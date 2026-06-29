"""Logique metier capteurs. Toutes les requetes sont filtrees par
`context.account_id` (issu du jeton) : c'est le point d'application de
l'isolation multi-entreprises. Un identifiant appartenant a une autre entreprise
ne renvoie jamais de donnees (et donne 404 en ecriture).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
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
    SensorRead,
    SensorUpdate,
)
from .ste2_parser import is_binary_kind

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

    def _offline_cutoff(self, now: datetime | None = None) -> datetime:
        """Horodatage en-deca duquel une mesure est consideree perimee."""
        window = timedelta(seconds=get_settings().sensor_offline_after_seconds)
        return (now or datetime.now(UTC)) - window

    @staticmethod
    def _is_online(sensor: Sensor, cutoff: datetime) -> bool:
        """Connectivite reelle : capteur actif et mesure plus recente que la
        fenetre de fraicheur. Distinct du drapeau de configuration `is_active`."""
        return bool(
            sensor.is_active and sensor.last_seen_at is not None and sensor.last_seen_at >= cutoff
        )

    @staticmethod
    def _display_name(sensor: Sensor) -> str:
        """Nom d'affichage : el-haress-NN-<label> (prefixe + index entreprise)."""
        if sensor.device_index is None:
            return sensor.label
        return f"el-haress-{sensor.device_index:02d}-{sensor.label}"

    def to_read(self, sensor: Sensor, cutoff: datetime | None = None) -> SensorRead:
        cutoff = cutoff or self._offline_cutoff()
        return SensorRead.model_validate(sensor).model_copy(
            update={
                "online": self._is_online(sensor, cutoff),
                "display_name": self._display_name(sensor),
                "is_binary": is_binary_kind(sensor.kind),
            }
        )

    async def list_sensors(self) -> list[Sensor]:
        return list(
            await self._session.scalars(
                select(Sensor).where(Sensor.account_id == self._account_id).order_by(Sensor.label)
            )
        )

    async def list_sensors_read(self) -> list[SensorRead]:
        cutoff = self._offline_cutoff()
        return [self.to_read(sensor, cutoff) for sensor in await self.list_sensors()]

    async def _get_owned_sensor(self, sensor_id: uuid.UUID) -> Sensor:
        sensor = await self._session.scalar(
            select(Sensor).where(Sensor.id == sensor_id, Sensor.account_id == self._account_id)
        )
        if sensor is None:
            raise ProblemException(404, "Capteur introuvable")
        return sensor

    async def update_sensor(self, sensor_id: uuid.UUID, data: SensorUpdate) -> Sensor:
        sensor = await self._get_owned_sensor(sensor_id)
        # exclude_unset : seuls les champs reellement fournis sont modifies
        # (permet de remettre un seuil a None explicitement).
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(sensor, key, value)
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
        offset: int = 0,
    ) -> list[ReadingPoint] | list[AggregatePoint]:
        limit = min(limit, _MAX_LIMIT)
        if bucket is ReadingBucket.RAW:
            return await self._raw_readings(sensor_id, start, end, limit, offset)
        return await self._aggregated_readings(
            _BUCKET_VIEW[bucket], sensor_id, start, end, limit, offset
        )

    async def _raw_readings(
        self,
        sensor_id: uuid.UUID | None,
        start: datetime | None,
        end: datetime | None,
        limit: int,
        offset: int = 0,
    ) -> list[ReadingPoint]:
        query = select(Reading).where(Reading.account_id == self._account_id)
        if sensor_id is not None:
            query = query.where(Reading.sensor_id == sensor_id)
        if start is not None:
            query = query.where(Reading.recorded_at >= start)
        if end is not None:
            query = query.where(Reading.recorded_at < end)
        query = query.order_by(Reading.recorded_at.desc()).offset(offset).limit(limit)
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
        offset: int = 0,
    ) -> list[AggregatePoint]:
        # `view` provient d'une enum (jamais d'entree client) ; parametres lies.
        conditions = ["account_id = :account_id"]
        params: dict[str, object] = {
            "account_id": self._account_id,
            "limit": limit,
            "offset": offset,
        }
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
            f"ORDER BY bucket DESC LIMIT :limit OFFSET :offset"
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
        settings = get_settings()
        cutoff = self._offline_cutoff()
        total = await self._session.scalar(
            select(func.count()).select_from(Sensor).where(Sensor.account_id == self._account_id)
        )
        # "Actifs" = reellement connectes : actifs ET mesure recente (last_seen_at).
        # Un capteur debranche cesse d'etre compte des qu'il depasse la fenetre.
        online = await self._session.scalar(
            select(func.count())
            .select_from(Sensor)
            .where(
                Sensor.account_id == self._account_id,
                Sensor.is_active.is_(True),
                Sensor.last_seen_at.is_not(None),
                Sensor.last_seen_at >= cutoff,
            )
        )
        return DashboardSummary(
            sensors_total=total or 0,
            sensors_active=online or 0,
            offline_after_seconds=settings.sensor_offline_after_seconds,
            latest=await self.latest_readings(),
        )
