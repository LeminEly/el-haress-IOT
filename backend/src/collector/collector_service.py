"""Service de collecte : un cycle interroge chaque passerelle active.

Pour chaque passerelle : lecture des echantillons, auto-provisionnement des
capteurs (decouverte dynamique, aucun capteur en dur), insertion des mesures
valides avec l'`account_id` **de la passerelle** (jamais code en dur). Resilient :
une panne reseau ou base sur une passerelle n'interrompt pas le cycle.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..sensors.sensors_models import Gateway, Reading, Sensor
from ..sensors.ste2_client import SampleSource
from ..sensors.ste2_parser import is_binary_kind

logger = structlog.get_logger(__name__)

# Publie une mesure pour diffusion temps reel (account_id, payload).
Publisher = Callable[[uuid.UUID, dict[str, Any]], Awaitable[None]]
# Evalue une mesure contre le moteur d'alertes (account_id, sensor_id, value, recorded_at).
Evaluator = Callable[[uuid.UUID, uuid.UUID, float, datetime], Awaitable[None]]


@dataclass
class GatewayResult:
    gateway_id: str
    sensors_seen: int
    readings_inserted: int
    mute: int
    error: str | None = None


class CollectorService:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        client: SampleSource,
        publisher: Publisher | None = None,
        evaluator: Evaluator | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._client = client
        self._publisher = publisher
        self._evaluator = evaluator

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
        published: list[dict[str, Any]] = []
        events: list[tuple[uuid.UUID, float]] = []
        try:
            async with self._session_factory() as session:
                existing = {
                    sensor.gateway_ref: sensor
                    for sensor in await session.scalars(
                        select(Sensor).where(Sensor.gateway_id == gateway.id)
                    )
                }
                # Index sequentiel par entreprise (pour le nom el-haress-NN-...).
                next_index = (
                    await session.scalar(
                        select(func.coalesce(func.max(Sensor.device_index), 0)).where(
                            Sensor.account_id == gateway.account_id
                        )
                    )
                ) + 1
                for sample in samples:
                    sensor = existing.get(sample.gateway_ref)
                    if sensor is None:
                        sensor = Sensor(
                            account_id=gateway.account_id,
                            gateway_id=gateway.id,
                            gateway_ref=sample.gateway_ref,
                            hardware_id=sample.hardware_id,
                            label=sample.name or sample.gateway_ref,
                            kind=sample.kind,
                            unit=sample.unit,
                            device_index=next_index,
                            is_active=True,
                        )
                        next_index += 1
                        session.add(sensor)
                        await session.flush()
                        existing[sample.gateway_ref] = sensor
                    else:
                        if sample.hardware_id and not sensor.hardware_id:
                            sensor.hardware_id = sample.hardware_id
                        # Rafraichit unite/type des qu'ils sont connus : un capteur
                        # decouvert hors-ligne se completera une fois branche.
                        if sample.unit and sensor.unit != sample.unit:
                            sensor.unit = sample.unit
                        if sample.kind != "unknown" and sensor.kind != sample.kind:
                            sensor.kind = sample.kind

                    # Capteur binaire (flood/contact...) : son etat declenche sort
                    # la valeur de la plage (sentinelle), on s'appuie sur status_state
                    # (1=normal, 2=alarme). Un detecteur de securite ne doit jamais
                    # etre masque : tant que l'appareil le voit, on enregistre 0/1.
                    if is_binary_kind(sensor.kind):
                        present = sample.status_state in ("1", "2")
                        detected = (
                            sample.status_state == "2"
                            or sample.alarm == "1"
                            or (sample.value or 0.0) > 0.0
                        )
                        reading_value: float | None = 1.0 if detected else 0.0
                    else:
                        present = sample.valid
                        reading_value = sample.value

                    if present and sensor.is_active and reading_value is not None:
                        session.add(
                            Reading(
                                account_id=gateway.account_id,
                                sensor_id=sensor.id,
                                recorded_at=now,
                                value=reading_value,
                            )
                        )
                        sensor.last_seen_at = now
                        inserted += 1
                        published.append(
                            {
                                "sensor_id": str(sensor.id),
                                "value": reading_value,
                                "recorded_at": now.isoformat(),
                            }
                        )
                        events.append((sensor.id, reading_value))
                    elif not present:
                        mute += 1

                refreshed = await session.get(Gateway, gateway.id)
                if refreshed is not None:
                    refreshed.last_polled_at = now
                await session.commit()
        except SQLAlchemyError as exc:  # backpressure : base indisponible
            logger.error("gateway_persist_failed", gateway_id=gateway_id, error=str(exc))
            return GatewayResult(gateway_id, len(samples), 0, 0, error=str(exc))

        # Diffusion temps reel apres commit (donnees visibles par les consommateurs).
        if self._publisher is not None:
            for payload in published:
                await self._publisher(gateway.account_id, payload)

        # Evaluation des alertes apres commit (mesures persistees).
        if self._evaluator is not None:
            for sensor_id, value in events:
                await self._evaluator(gateway.account_id, sensor_id, value, now)

        logger.info(
            "gateway_polled",
            gateway_id=gateway_id,
            sensors=len(samples),
            readings=inserted,
            mute=mute,
        )
        return GatewayResult(gateway_id, len(samples), inserted, mute)
