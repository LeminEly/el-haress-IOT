"""Service de collecte : un cycle interroge chaque passerelle active.

Pour chaque passerelle : lecture des echantillons, auto-provisionnement des
capteurs (decouverte dynamique, aucun capteur en dur), insertion des mesures
valides avec l'`account_id` **de la passerelle** (jamais code en dur). Resilient :
une panne reseau ou base sur une passerelle n'interrompt pas le cycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..sensors.sensors_models import Gateway, Reading, Sensor
from ..sensors.ste2_client import SampleSource
from ..sensors.ste2_parser import infer_kind

logger = structlog.get_logger(__name__)


@dataclass
class GatewayResult:
    gateway_id: str
    sensors_seen: int
    readings_inserted: int
    mute: int
    error: str | None = None


class CollectorService:
    def __init__(self, session_factory: async_sessionmaker, client: SampleSource) -> None:
        self._session_factory = session_factory
        self._client = client

    async def run_cycle(self) -> list[GatewayResult]:
        async with self._session_factory() as session:
            gateways = list(
                await session.scalars(select(Gateway).where(Gateway.is_active.is_(True)))
            )
        return [await self._poll_gateway(gateway) for gateway in gateways]

    async def _poll_gateway(self, gateway: Gateway) -> GatewayResult:
        gateway_id = str(gateway.id)
        try:
            samples = await self._client.fetch_samples(gateway.base_url)
        except Exception as exc:  # resilience : ne jamais interrompre le cycle
            logger.warning("gateway_poll_failed", gateway_id=gateway_id, error=str(exc))
            return GatewayResult(gateway_id, 0, 0, 0, error=str(exc))

        now = datetime.now(UTC)
        inserted = 0
        mute = 0
        try:
            async with self._session_factory() as session:
                existing = {
                    sensor.gateway_ref: sensor
                    for sensor in await session.scalars(
                        select(Sensor).where(Sensor.gateway_id == gateway.id)
                    )
                }
                for sample in samples:
                    sensor = existing.get(sample.gateway_ref)
                    if sensor is None:
                        sensor = Sensor(
                            account_id=gateway.account_id,
                            gateway_id=gateway.id,
                            gateway_ref=sample.gateway_ref,
                            hardware_id=sample.hardware_id,
                            label=sample.name or sample.gateway_ref,
                            kind=infer_kind(sample.unit),
                            unit=sample.unit,
                            is_active=True,
                        )
                        session.add(sensor)
                        await session.flush()
                        existing[sample.gateway_ref] = sensor
                    elif sample.hardware_id and not sensor.hardware_id:
                        sensor.hardware_id = sample.hardware_id

                    if sample.valid and sensor.is_active:
                        session.add(
                            Reading(
                                account_id=gateway.account_id,
                                sensor_id=sensor.id,
                                recorded_at=now,
                                value=sample.value,
                            )
                        )
                        sensor.last_seen_at = now
                        inserted += 1
                    elif not sample.valid:
                        mute += 1

                refreshed = await session.get(Gateway, gateway.id)
                if refreshed is not None:
                    refreshed.last_polled_at = now
                await session.commit()
        except SQLAlchemyError as exc:  # backpressure : base indisponible
            logger.error("gateway_persist_failed", gateway_id=gateway_id, error=str(exc))
            return GatewayResult(gateway_id, len(samples), 0, 0, error=str(exc))

        logger.info(
            "gateway_polled",
            gateway_id=gateway_id,
            sensors=len(samples),
            readings=inserted,
            mute=mute,
        )
        return GatewayResult(gateway_id, len(samples), inserted, mute)
