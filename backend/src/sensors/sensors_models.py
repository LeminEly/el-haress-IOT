"""Modeles capteurs et mesures.

`Sensor` : capteur declare, rattache a une entreprise, identifie de facon stable
par son adresse materielle (`hardware_id`, ex. SenId 1-Wire du STE2). Le type
(`kind`) et l'unite sont generiques : aucun capteur n'est code en dur.

`Reading` : hypertable TimescaleDB, partitionnee par `recorded_at` (horodatage
serveur, UTC). Pas d'identifiant surrogate : une mesure est identifiee par
(`sensor_id`, `recorded_at`), conformement aux bonnes pratiques time-series ; la
cle primaire inclut la colonne de partitionnement, requis par TimescaleDB.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Double, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Sensor(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "sensors"

    hardware_id: Mapped[str] = mapped_column(String(64), nullable=False)
    gateway_ref: Mapped[str | None] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("account_id", "hardware_id", name="uq_sensors_account_id_hardware_id"),
        Index("ix_sensors_account_id", "account_id"),
    )


class Reading(Base):
    __tablename__ = "readings"

    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    sensor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, primary_key=True
    )
    value: Mapped[float] = mapped_column(Double, nullable=False)

    __table_args__ = (
        # Index composites prefixes par account_id (isolation + performance).
        Index("ix_readings_account_id_recorded_at", "account_id", "recorded_at"),
        Index(
            "ix_readings_account_id_sensor_id_recorded_at",
            "account_id",
            "sensor_id",
            "recorded_at",
        ),
    )
