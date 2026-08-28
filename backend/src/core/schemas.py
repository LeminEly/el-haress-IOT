"""Base de schemas partagee."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Entrees API : rejette tout champ inconnu (anti mass-assignment)."""

    model_config = ConfigDict(extra="forbid")
