"""Primitives de securite : hachage de mot de passe et jetons JWT RS256.

- Mots de passe : bcrypt (cout configurable). Un pre-hachage SHA-256 (encode en
  base64) est applique pour lever la limite de 72 octets de bcrypt sans tronquer
  silencieusement les mots de passe longs.
- Jetons : JWT signes en RS256 (cle privee cote backend uniquement), avec `jti`
  pour la revocation (blacklist) et un `type` distinguant access et refresh.
"""

from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import bcrypt
import jwt

from ..config import Settings

ACCESS_TOKEN = "access"
REFRESH_TOKEN = "refresh"


class TokenError(Exception):
    """Jeton invalide, expire ou de type inattendu."""


def _prehash(plain: str) -> bytes:
    return base64.b64encode(hashlib.sha256(plain.encode("utf-8")).digest())


def hash_password(plain: str, *, rounds: int) -> str:
    return bcrypt.hashpw(_prehash(plain), bcrypt.gensalt(rounds=rounds)).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(plain), hashed.encode("ascii"))
    except ValueError:
        return False


@lru_cache(maxsize=1)
def _private_key(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _public_key(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _create_token(
    *,
    account_id: uuid.UUID,
    role: str,
    token_type: str,
    expires_delta: timedelta,
    settings: Settings,
) -> tuple[str, str, int]:
    """Retourne (jeton, jti, ttl_secondes)."""
    now = datetime.now(UTC)
    expire = now + expires_delta
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(account_id),
        "role": role,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": expire,
        "iss": settings.jwt_issuer,
    }
    token = jwt.encode(payload, _private_key(settings.jwt_private_key_path), algorithm="RS256")
    return token, jti, int(expires_delta.total_seconds())


def create_access_token(
    *, account_id: uuid.UUID, role: str, settings: Settings
) -> tuple[str, str, int]:
    return _create_token(
        account_id=account_id,
        role=role,
        token_type=ACCESS_TOKEN,
        expires_delta=timedelta(minutes=settings.jwt_access_expires_minutes),
        settings=settings,
    )


def create_refresh_token(
    *, account_id: uuid.UUID, role: str, settings: Settings
) -> tuple[str, str, int]:
    return _create_token(
        account_id=account_id,
        role=role,
        token_type=REFRESH_TOKEN,
        expires_delta=timedelta(days=settings.jwt_refresh_expires_days),
        settings=settings,
    )


def decode_token(token: str, *, expected_type: str, settings: Settings) -> dict:
    try:
        payload = jwt.decode(
            token,
            _public_key(settings.jwt_public_key_path),
            algorithms=["RS256"],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "jti"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
    if payload.get("type") != expected_type:
        raise TokenError("type de jeton inattendu")
    return payload
