"""Dependances de securite : extraction du principal et controle RBAC.

`get_current_account` decode le jeton d'acces (RS256), verifie qu'il n'est pas
revoque, charge le compte et controle son statut. `require_role` restreint une
route a certains roles. L'`account_id` du principal est la seule source du
perimetre de donnees (voir module tenancy).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..core.exceptions import ProblemException
from ..core.redis import get_blacklist_redis
from ..db.session import get_session
from .auth_models import Account, AccountRole, AccountStatus
from .revocation import is_revoked
from .security import ACCESS_TOKEN, TokenError, decode_token

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    account_id: uuid.UUID
    role: AccountRole
    jti: str
    access_exp: int


async def get_current_account(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
    blacklist: Redis = Depends(get_blacklist_redis),
    settings: Settings = Depends(get_settings),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ProblemException(401, "Authentification requise")

    try:
        payload = decode_token(
            credentials.credentials, expected_type=ACCESS_TOKEN, settings=settings
        )
    except TokenError:
        raise ProblemException(401, "Jeton invalide ou expire") from None

    if await is_revoked(blacklist, jti=payload["jti"]):
        raise ProblemException(401, "Jeton revoque") from None

    account = await session.get(Account, uuid.UUID(payload["sub"]))
    if account is None or account.status != AccountStatus.ACTIVE:
        raise ProblemException(401, "Compte indisponible") from None

    return Principal(
        account_id=account.id,
        role=account.role,
        jti=payload["jti"],
        access_exp=int(payload["exp"]),
    )


def require_role(*roles: AccountRole) -> Callable[[Principal], Awaitable[Principal]]:
    async def _guard(principal: Principal = Depends(get_current_account)) -> Principal:
        if principal.role not in roles:
            raise ProblemException(403, "Acces refuse")
        return principal

    return _guard
