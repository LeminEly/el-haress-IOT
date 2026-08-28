"""Endpoint de sante — verification de disponibilite du service.

Volontairement sans dependance externe (base, Redis) : il doit repondre meme si
les dependances sont indisponibles, pour distinguer "service vivant" de
"dependance en panne". Les verifications de dependances viendront en phase
observabilite (readiness).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ..config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness du service")
async def health() -> dict[str, Any]:
    settings = get_settings()
    return {
        "data": {
            "status": "ok",
            "service": "el-haress-backend",
            "environment": settings.environment,
        }
    }
