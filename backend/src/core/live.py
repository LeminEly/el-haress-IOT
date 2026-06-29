"""Diffusion temps reel des mesures (Redis pub/sub).

Le collector (process distinct) publie chaque nouvelle mesure sur le canal de
l'entreprise ; le serveur web (WebSocket) y est abonne et relaie aux clients
connectes. Un canal par `account_id` garantit l'isolation : un client ne recoit
que les mesures de sa propre entreprise.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from redis.asyncio import Redis


def channel_for(account_id: uuid.UUID | str) -> str:
    return f"live:{account_id}"


async def publish_reading(redis: Redis, *, account_id: uuid.UUID, payload: dict[str, Any]) -> None:
    await redis.publish(channel_for(account_id), json.dumps(payload, default=str))
