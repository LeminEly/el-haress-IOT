"""Routes d'authentification.

`/login` et `/refresh` sont publiques ; `/logout` et `/me` exigent un jeton.
- access token : Bearer, courte duree.
- refresh token : cookie httpOnly SameSite=Strict, rotation a chaque rafraichissement.
- logout : revocation (blacklist Redis) de l'access et du refresh courants.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..core.exceptions import ProblemException
from ..core.rate_limit import sliding_window_allow
from ..core.redis import get_blacklist_redis, get_ratelimit_redis
from ..db.session import get_session
from .auth_models import Account, AccountStatus
from .auth_schemas import AccountProfile, LoginRequest, TokenResponse
from .auth_service import AuthService
from .dependencies import Principal, get_current_account
from .revocation import is_revoked, revoke
from .security import (
    REFRESH_TOKEN,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _remaining_ttl(exp: int) -> int:
    return max(0, exp - int(datetime.now(UTC).timestamp()))


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=settings.jwt_refresh_expires_days * 86400,
        httponly=True,
        secure=settings.cookie_secure or settings.is_production,
        samesite="strict",
        path="/api/v1/auth",
    )


async def _issue_tokens(account: Account, response: Response, settings: Settings) -> TokenResponse:
    access, _, ttl = create_access_token(
        account_id=account.id, role=account.role, settings=settings
    )
    refresh, _, _ = create_refresh_token(
        account_id=account.id, role=account.role, settings=settings
    )
    _set_refresh_cookie(response, refresh, settings)
    return TokenResponse(access_token=access, expires_in=ttl)


@router.post("/login")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    ratelimit: Redis = Depends(get_ratelimit_redis),
    settings: Settings = Depends(get_settings),
) -> dict:
    client_ip = request.client.host if request.client else "unknown"
    allowed = await sliding_window_allow(
        ratelimit,
        key=f"login:{client_ip}",
        limit=settings.login_rate_limit_per_minute,
        window_seconds=60,
    )
    if not allowed:
        raise ProblemException(429, "Trop de tentatives, reessayez plus tard")

    account = await AuthService(session, settings).authenticate(
        phone_number=payload.phone_number, password=payload.password
    )
    return {"data": await _issue_tokens(account, response, settings)}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    blacklist: Redis = Depends(get_blacklist_redis),
    settings: Settings = Depends(get_settings),
) -> dict:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise ProblemException(401, "Jeton de rafraichissement absent")

    try:
        payload = decode_token(token, expected_type=REFRESH_TOKEN, settings=settings)
    except TokenError:
        raise ProblemException(401, "Jeton invalide ou expire") from None

    if await is_revoked(blacklist, jti=payload["jti"]):
        raise ProblemException(401, "Jeton revoque") from None

    account = await session.get(Account, uuid.UUID(payload["sub"]))
    if account is None or account.status != AccountStatus.ACTIVE:
        raise ProblemException(401, "Compte indisponible") from None

    # Rotation : on revoque l'ancien refresh pour sa duree de vie restante.
    await revoke(blacklist, jti=payload["jti"], ttl_seconds=_remaining_ttl(int(payload["exp"])))
    return {"data": await _issue_tokens(account, response, settings)}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    principal: Principal = Depends(get_current_account),
    blacklist: Redis = Depends(get_blacklist_redis),
    settings: Settings = Depends(get_settings),
) -> dict:
    await revoke(blacklist, jti=principal.jti, ttl_seconds=_remaining_ttl(principal.access_exp))

    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if refresh_token:
        try:
            payload = decode_token(refresh_token, expected_type=REFRESH_TOKEN, settings=settings)
            await revoke(
                blacklist, jti=payload["jti"], ttl_seconds=_remaining_ttl(int(payload["exp"]))
            )
        except TokenError:
            pass

    response.delete_cookie(settings.refresh_cookie_name, path="/api/v1/auth")
    return {"data": {"status": "deconnecte"}}


@router.get("/me")
async def me(
    principal: Principal = Depends(get_current_account),
    session: AsyncSession = Depends(get_session),
) -> dict:
    account = await session.get(Account, principal.account_id)
    if account is None:
        raise ProblemException(401, "Compte indisponible")
    return {"data": AccountProfile.model_validate(account)}
