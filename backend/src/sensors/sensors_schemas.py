"""Schemas Pydantic : passerelles, capteurs, mesures, tableau de bord."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..core.schemas import StrictModel


class GatewayCreate(StrictModel):
    name: str = Field(min_length=1, max_length=255)
    base_url: str = Field(min_length=1, max_length=255)
    poll_interval_seconds: int = Field(default=10, ge=1, le=3600)


class GatewayRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    base_url: str
    poll_interval_seconds: int
    is_active: bool
    last_polled_at: datetime | None = None


class SensorUpdate(StrictModel):
    label: str | None = Field(default=None, min_length=1, max_length=255)
    kind: str | None = Field(default=None, min_length=1, max_length=64)
    is_active: bool | None = None


class SensorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    gateway_id: uuid.UUID
    gateway_ref: str
    hardware_id: str | None = None
    label: str
    kind: str
    unit: str | None = None
    is_active: bool
    last_seen_at: datetime | None = None


class ReadingBucket(enum.StrEnum):
    RAW = "raw"
    MIN = "1min"
    HOUR = "1hour"


class ReadingPoint(BaseModel):
    sensor_id: uuid.UUID
    recorded_at: datetime
    value: float


class AggregatePoint(BaseModel):
    sensor_id: uuid.UUID
    bucket: datetime
    avg_value: float
    min_value: float
    max_value: float


class LatestReading(BaseModel):
    sensor_id: uuid.UUID
    label: str
    unit: str | None = None
    value: float
    recorded_at: datetime


class DashboardSummary(BaseModel):
    sensors_total: int
    sensors_active: int
    latest: list[LatestReading]
