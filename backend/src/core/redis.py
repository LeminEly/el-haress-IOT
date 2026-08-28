"""Clients Redis par base logique.

Bases separees (cf. config) : cache, rate limiting, deduplication d'alertes,
blacklist JWT. Les dependances sont surchargeables en test (fakeredis).
"""

from __future__ import annotations

from functools import cache

from redis.asyncio import Redis

from ..config import get_settings


def _make_client(db: int) -> Redis:
    settings = get_settings()
    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=db,
        password=settings.redis_password or None,
        decode_responses=True,
    )


@cache
def ratelimit_redis() -> Redis:
    return _make_client(get_settings().redis_db_ratelimit)


@cache
def blacklist_redis() -> Redis:
    return _make_client(get_settings().redis_db_jwt_blacklist)


@cache
def pubsub_redis() -> Redis:
    # Diffusion temps reel (pub/sub) : base cache.
    return _make_client(get_settings().redis_db_cache)


@cache
def alert_dedup_redis() -> Redis:
    return _make_client(get_settings().redis_db_alert_dedup)


async def get_ratelimit_redis() -> Redis:
    return ratelimit_redis()


async def get_blacklist_redis() -> Redis:
    return blacklist_redis()


async def get_pubsub_redis() -> Redis:
    return pubsub_redis()
