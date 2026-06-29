"""Logique metier capteurs. Toutes les requetes sont filtrees par
`context.account_id` (issu du jeton) : c'est le point d'application de
l'isolation multi-entreprises. Un identifiant appartenant a une autre entreprise
ne renvoie jamais de donnees (et donne 404 en ecriture).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import ProblemException
from ..tenancy.tenancy import TenantContext
from .sensors_models import Gateway, Reading, Sensor
from .sensors_schemas import (
    AggregatePoint,
    DashboardSummary,
    GatewayCreate,
    LatestReading,
    ReadingBucket,
    ReadingPoint,
    SensorUpdate,
)

_BUCKET_VIEW = {ReadingBucket.MIN: "readings_1min", ReadingBucket.HOUR: "readings_1hour"}
_MAX_LIMIT = 5000


class SensorsService:
    def __init__(self, session: AsyncSession, context: TenantContext) -> None:
        self._session = session
        self._account_id = context.account_id

    # -- Passerelles --------------------------------------------------------

    async def list_gateways(self) -> list[Gateway]:
        return list(
            await self._session.scalars(
                select(Gateway)
                .where(Gateway.account_id == self._account_id)
                .order_by(Gateway.created_at.desc())
            )
        )

    async def create_gateway(self, data: GatewayCreate) -> Gateway:
        gateway = Gateway(
            account_id=self._account_id,
            name=data.name,
            base_url=data.base_url,
            poll_interval_seconds=data.poll_interval_seconds,
            is_active=True,
        )
        self._session.add(gateway)
        await self._session.commit()
        await self._session.refresh(gateway)
        return gateway

    # -- Capteurs -----------------------------------------------------------

    async def list_sensors(self) -> list[Sensor]:
        return list(
            await self._session.scalars(
                select(Sensor).where(Sensor.account_id == self._account_id).order_by(Sensor.label)
            )
        )

    async def _get_owned_sensor(self, sensor_id: uuid.UUID) -> Sensor:
        sensor = await self._session.scalar(
            select(Sensor).where(Sensor.id == sensor_id, Sensor.account_id == self._account_id)
        )
        if sensor is None:
            raise ProblemException(404, "Capteur introuvable")
        return sensor

    async def update_sensor(self, sensor_id: uuid.UUID, data: SensorUpdate) -> Sensor:
        sensor = await self._get_owned_sensor(sensor_id)
        if data.label is not None:
            sensor.label = data.label
        if data.kind is not None:
            sensor.kind = data.kind
        if data.is_active is not None:
            sensor.is_active = data.is_active
        await self._session.commit()
        await self._session.refresh(sensor)
        return sensor

    # -- Mesures ------------------------------------------------------------

    async def get_readings(
        self,
        *,
        sensor_id: uuid.UUID | None,
        start: datetime | None,
        end: datetime | None,
        bucket: ReadingBucket,
        limit: int,
    ) -> list[ReadingPoint] | list[AggregatePoint]:
        limit = min(limit, _MAX_LIMIT)
        if bucket is ReadingBucket.RAW:
            return await self._raw_readings(sensor_id, start, end, limit)
        return await self._aggregated_readings(_BUCKET_VIEW[bucket], sensor_id, start, end, limit)

    async def _raw_readings(
        self,
        sensor_id: uuid.UUID | None,
        start: datetime | None,
        end: datetime | None,
        limit: int,
    ) -> list[ReadingPoint]:
        query = select(Reading).where(Reading.account_id == self._account_id)
        if sensor_id is not None:
            query = query.where(Reading.sensor_id == sensor_id)
        if start is not None:
            query = query.where(Reading.recorded_at >= start)
        if end is not None:
            query = query.where(Reading.recorded_at < end)
        query = query.order_by(Reading.recorded_at.desc()).limit(limit)
        rows = await self._session.scalars(query)
        return [
            ReadingPoint(sensor_id=r.sensor_id, recorded_at=r.recorded_at, value=r.value)
            for r in rows
        ]

    async def _aggregated_readings(
        self,
        view: str,
        sensor_id: uuid.UUID | None,
        start: datetime | None,
        end: datetime | None,
        limit: int,
    ) -> list[AggregatePoint]:
        # `view` provient d'une enum (jamais d'entree client) ; parametres lies.
        conditions = ["account_id = :account_id"]
        params: dict[str, object] = {"account_id": self._account_id, "limit": limit}
        if sensor_id is not None:
            conditions.append("sensor_id = :sensor_id")
            params["sensor_id"] = sensor_id
        if start is not None:
            conditions.append("bucket >= :start")
            params["start"] = start
        if end is not None:
            conditions.append("bucket < :end")
            params["end"] = end
        sql = text(
            f"SELECT sensor_id, bucket, avg_value, min_value, max_value "
            f"FROM {view} WHERE {' AND '.join(conditions)} "
            f"ORDER BY bucket DESC LIMIT :limit"
        )
        result = await self._session.execute(sql, params)
        return [
            AggregatePoint(
                sensor_id=row.sensor_id,
                bucket=row.bucket,
                avg_value=row.avg_value,
                min_value=row.min_value,
                max_value=row.max_value,
            )
            for row in result
        ]

    async def latest_readings(self) -> list[LatestReading]:
        sql = text(
            "SELECT DISTINCT ON (r.sensor_id) "
            "  r.sensor_id, s.label, s.unit, r.value, r.recorded_at "
            "FROM readings r JOIN sensors s ON s.id = r.sensor_id "
            "WHERE r.account_id = :account_id "
            "ORDER BY r.sensor_id, r.recorded_at DESC"
        )
        result = await self._session.execute(sql, {"account_id": self._account_id})
        return [
            LatestReading(
                sensor_id=row.sensor_id,
                label=row.label,
                unit=row.unit,
                value=row.value,
                recorded_at=row.recorded_at,
            )
            for row in result
        ]

    async def dashboard_summary(self) -> DashboardSummary:
        total = await self._session.scalar(
            select(func.count()).select_from(Sensor).where(Sensor.account_id == self._account_id)
        )
        active = await self._session.scalar(
            select(func.count())
            .select_from(Sensor)
            .where(Sensor.account_id == self._account_id, Sensor.is_active.is_(True))
        )
        return DashboardSummary(
            sensors_total=total or 0,
            sensors_active=active or 0,
            latest=await self.latest_readings(),
        )
