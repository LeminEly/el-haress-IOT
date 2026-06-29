"""Point d'entree du service collector (process distinct du serveur web).

    python -m src.collector

Boucle a intervalle configurable (jamais code en dur). Une exception dans un
cycle est journalisee sans arreter le service (resilience).
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog

from ..config import get_settings
from ..core.live import publish_reading
from ..core.logging import configure_logging
from ..core.redis import pubsub_redis
from ..db.session import AsyncSessionLocal
from ..sensors.ste2_client import Ste2Client
from .collector_service import CollectorService

logger = structlog.get_logger(__name__)


async def _run_loop() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=settings.is_production)

    redis = pubsub_redis()

    async def _publisher(account_id: uuid.UUID, payload: dict[str, Any]) -> None:
        await publish_reading(redis, account_id=account_id, payload=payload)

    service = CollectorService(AsyncSessionLocal, Ste2Client(), publisher=_publisher)
    interval = settings.collector_poll_interval_seconds
    logger.info("collector_starting", interval_seconds=interval)

    while True:
        try:
            await service.run_cycle()
        except Exception as exc:  # le service ne doit jamais s'arreter
            logger.error("collector_cycle_failed", error=str(exc))
        await asyncio.sleep(interval)


def main() -> None:
    asyncio.run(_run_loop())


if __name__ == "__main__":
    main()
