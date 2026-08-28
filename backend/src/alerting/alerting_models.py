"""Modeles du moteur d'alertes : regles configurables et alertes declenchees.

Les seuils ne sont jamais codes en dur : ils vivent dans `alert_rules`, propres a
chaque entreprise. `Alert` trace chaque declenchement avec son `account_id`.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Double, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AlertSeverity(enum.StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class AlertCondition(enum.StrEnum):
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"


class AlertStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class AlertRule(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "alert_rules"

    sensor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sensors.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    condition: Mapped[AlertCondition] = mapped_column(
        Enum(AlertCondition, native_enum=False, length=8), nullable=False
    )
    threshold: Mapped[float] = mapped_column(Double, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, native_enum=False, length=12), nullable=False
    )
    channels: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (Index("ix_alert_rules_account_id_sensor_id", "account_id", "sensor_id"),)


class Alert(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "alerts"

    alert_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("alert_rules.id", ondelete="SET NULL")
    )
    sensor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sensors.id", ondelete="SET NULL")
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, native_enum=False, length=12), nullable=False
    )
    value: Mapped[float] = mapped_column(Double, nullable=False)
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, native_enum=False, length=12),
        default=AlertStatus.ACTIVE,
        nullable=False,
    )
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_alerts_account_id_triggered_at", "account_id", "triggered_at"),)
