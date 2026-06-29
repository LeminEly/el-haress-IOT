"""Modeles capteurs : passerelles, capteurs et mesures.

`Gateway` : passerelle physique (STE2 LITE) rattachee a une entreprise. C'est elle
qui resout l'`account_id` des mesures collectees : aucun `account_id` n'est code en
dur dans le collector. Prepare aussi le multi-site (plusieurs passerelles).

`Sensor` : capteur rattache a une passerelle. Identifie par son `gateway_ref`
(identifiant du point de mesure sur la passerelle) ; son `hardware_id` (SenId
1-Wire) est renseigne quand il est connu, comme identite materielle stable.

`Reading` : hypertable TimescaleDB, partitionnee par `recorded_at` (horodatage
serveur, UTC). Voir docs/sensor-system-ste2.md.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Gateway(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "gateways"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_gateways_account_id", "account_id"),)


class Sensor(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "sensors"

    gateway_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gateways.id", ondelete="CASCADE"), nullable=False
    )
    # Identifiant du point de mesure sur la passerelle (cle d'appariement au poll).
    gateway_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    # Adresse materielle stable (SenId 1-Wire), renseignee quand connue.
    hardware_id: Mapped[str | None] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Configuration par capteur : seuil critique (affichage/statut) et couleur de courbe.
    critical_threshold: Mapped[float | None] = mapped_column(Double)
    color: Mapped[str | None] = mapped_column(String(16))

    __table_args__ = (
        UniqueConstraint("gateway_id", "gateway_ref", name="uq_sensors_gateway_id_gateway_ref"),
        Index("ix_sensors_account_id", "account_id"),
        Index("ix_sensors_gateway_id", "gateway_id"),
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
        Index("ix_readings_account_id_recorded_at", "account_id", "recorded_at"),
        Index(
            "ix_readings_account_id_sensor_id_recorded_at",
            "account_id",
            "sensor_id",
            "recorded_at",
        ),
    )
