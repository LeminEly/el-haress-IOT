"""WebSocket temps reel `/ws/live`.

Authentifie par le jeton d'acces (query `token`). Chaque connexion est abonnee au
canal Redis de SON entreprise (`live:{account_id}`) : un client ne recoit jamais
les mesures d'une autre entreprise. La diffusion vient du collector (pub/sub).
"""

from __future__ import annotations

import asyncio
import uuid

import structlog
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.auth_models import Account, AccountStatus
from ..auth.revocation import is_revoked
from ..auth.security import ACCESS_TOKEN, TokenError, decode_token
from ..config import Settings, get_settings
from ..core.live import channel_for
from ..core.redis import get_blacklist_redis, get_pubsub_redis
from ..db.session import get_session

logger = structlog.get_logger(__name__)
router = APIRouter()

_WS_UNAUTHORIZED = 4401


@router.websocket("/ws/live")
async def ws_live(
    websocket: WebSocket,
    token: str = Query(...),
    settings: Settings = Depends(get_settings),
    blacklist: Redis = Depends(get_blacklist_redis),
    pubsub_client: Redis = Depends(get_pubsub_redis),
    session: AsyncSession = Depends(get_session),
) -> None:
    try:
        payload = decode_token(token, expected_type=ACCESS_TOKEN, settings=settings)
    except TokenError:
        await websocket.close(code=_WS_UNAUTHORIZED)
        return
    if await is_revoked(blacklist, jti=payload["jti"]):
        await websocket.close(code=_WS_UNAUTHORIZED)
        return
    account = await session.get(Account, uuid.UUID(payload["sub"]))
    if account is None or account.status != AccountStatus.ACTIVE:
        await websocket.close(code=_WS_UNAUTHORIZED)
        return

    await websocket.accept()
    channel = channel_for(account.id)
    pubsub = pubsub_client.pubsub()
    await pubsub.subscribe(channel)

    async def _forward() -> None:
        async for message in pubsub.listen():
            if message.get("type") == "message":
                await websocket.send_text(message["data"])

    async def _detect_disconnect() -> None:
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            return

    forward_task = asyncio.create_task(_forward())
    disconnect_task = asyncio.create_task(_detect_disconnect())
    try:
        _, pending = await asyncio.wait(
            {forward_task, disconnect_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
