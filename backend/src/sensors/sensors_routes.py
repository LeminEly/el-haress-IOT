"""Routes REST : passerelles, capteurs, mesures, tableau de bord.

Toutes protegees par jeton ; le perimetre vient du contexte de tenance
(`account_id` du jeton), jamais d'un parametre client.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_session
from ..tenancy.tenancy import TenantContext, get_tenant_context
from .sensors_schemas import (
    GatewayCreate,
    GatewayRead,
    ReadingBucket,
    SensorUpdate,
)
from .sensors_service import SensorsService

router = APIRouter(tags=["sensors"])


@router.get("/gateways")
async def list_gateways(
    context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_session),
) -> dict:
    gateways = await SensorsService(session, context).list_gateways()
    return {"data": [GatewayRead.model_validate(g) for g in gateways]}


@router.post("/gateways", status_code=status.HTTP_201_CREATED)
async def create_gateway(
    payload: GatewayCreate,
    context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_session),
) -> dict:
    gateway = await SensorsService(session, context).create_gateway(payload)
    return {"data": GatewayRead.model_validate(gateway)}


@router.get("/sensors")
async def list_sensors(
    context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {"data": await SensorsService(session, context).list_sensors_read()}


@router.patch("/sensors/{sensor_id}")
async def update_sensor(
    sensor_id: uuid.UUID,
    payload: SensorUpdate,
    context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_session),
) -> dict:
    service = SensorsService(session, context)
    sensor = await service.update_sensor(sensor_id, payload)
    return {"data": service.to_read(sensor)}


@router.get("/readings")
async def get_readings(
    context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_session),
    sensor_id: uuid.UUID | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    bucket: ReadingBucket = Query(default=ReadingBucket.RAW),
    limit: int = Query(default=500, ge=1, le=5000),
    offset: int = Query(default=0, ge=0, le=50000),
) -> dict:
    points = await SensorsService(session, context).get_readings(
        sensor_id=sensor_id, start=start, end=end, bucket=bucket, limit=limit, offset=offset
    )
    return {"data": points}


@router.get("/readings/latest")
async def latest_readings(
    context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {"data": await SensorsService(session, context).latest_readings()}


@router.get("/dashboard/summary")
async def dashboard_summary(
    context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {"data": await SensorsService(session, context).dashboard_summary()}
