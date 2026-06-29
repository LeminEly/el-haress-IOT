"""Revocation de jetons JWT (blacklist par `jti` dans Redis).

Un jeton revoque (logout, rotation du refresh) est stocke jusqu'a son expiration
naturelle : le TTL Redis correspond a la duree de vie restante du jeton.
"""

from __future__ import annotations

from redis.asyncio import Redis

_PREFIX = "jwt:blacklist:"


async def revoke(redis: Redis, *, jti: str, ttl_seconds: int) -> None:
    if ttl_seconds > 0:
        await redis.set(f"{_PREFIX}{jti}", "1", ex=ttl_seconds)


async def is_revoked(redis: Redis, *, jti: str) -> bool:
    return bool(await redis.exists(f"{_PREFIX}{jti}"))
