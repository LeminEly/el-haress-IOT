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
    critical_threshold: float | None = None
    color: str | None = Field(default=None, max_length=16)


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
    device_index: int | None = None
    # Nom d'affichage genere : el-haress-NN-<label> (prefixe + index entreprise).
    display_name: str = ""
    # Capteur a etat binaire (Detecte / Normal) plutot qu'a valeur continue.
    is_binary: bool = False
    # Connectivite reelle : mesure recente (< fenetre de fraicheur) et capteur actif.
    # Distinct de `is_active` (drapeau de configuration).
    online: bool = False
    critical_threshold: float | None = None
    color: str | None = None


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
    # Capteurs reellement connectes (mesure recente), pas le drapeau is_active.
    sensors_active: int
    # Fenetre de fraicheur (secondes) : le front l'utilise pour reevaluer la
    # connectivite en temps reel et masquer les capteurs muets.
    offline_after_seconds: float
    latest: list[LatestReading]
