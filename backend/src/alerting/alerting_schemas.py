"""Schemas Pydantic des regles d'alerte."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..core.schemas import StrictModel
from .alerting_models import AlertCondition, AlertSeverity, AlertStatus


class AlertChannel(enum.StrEnum):
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"


class AlertRuleCreate(StrictModel):
    name: str = Field(min_length=1, max_length=255)
    sensor_id: uuid.UUID | None = None
    condition: AlertCondition
    threshold: float
    duration_seconds: int = Field(default=0, ge=0, le=86400)
    cooldown_minutes: int = Field(default=0, ge=0, le=1440)
    severity: AlertSeverity
    channels: list[AlertChannel] = Field(min_length=1)
    is_active: bool = True


class AlertRuleUpdate(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    condition: AlertCondition | None = None
    threshold: float | None = None
    duration_seconds: int | None = Field(default=None, ge=0, le=86400)
    cooldown_minutes: int | None = Field(default=None, ge=0, le=1440)
    severity: AlertSeverity | None = None
    channels: list[AlertChannel] | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class AlertRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    sensor_id: uuid.UUID | None = None
    condition: AlertCondition
    threshold: float
    duration_seconds: int
    cooldown_minutes: int
    severity: AlertSeverity
    channels: list[str]
    is_active: bool
    created_at: datetime


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_rule_id: uuid.UUID | None = None
    sensor_id: uuid.UUID | None = None
    severity: AlertSeverity
    value: float
    status: AlertStatus
    triggered_at: datetime
    acknowledged_at: datetime | None = None
