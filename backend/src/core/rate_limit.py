"""Limiteur de debit a fenetre glissante (Redis sorted set).

Chaque tentative est horodatee dans un sorted set ; les entrees hors fenetre sont
purgees, puis on compte. Precis (vraie fenetre glissante), atomique (pipeline).
"""

from __future__ import annotations

import time
import uuid

from redis.asyncio import Redis


async def sliding_window_allow(redis: Redis, *, key: str, limit: int, window_seconds: int) -> bool:
    """Retourne True si la requete est autorisee, False si la limite est atteinte."""
    now = time.time()
    cutoff = now - window_seconds
    member = f"{now:.6f}:{uuid.uuid4()}"
    async with redis.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, 0, cutoff)
        pipe.zadd(key, {member: now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        results = await pipe.execute()
    count = int(results[2])
    return count <= limit
