"""Routes REST de gestion des regles d'alerte (par entreprise)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_session
from ..tenancy.tenancy import TenantContext, get_tenant_context
from .alerting_models import AlertStatus
from .alerting_schemas import AlertRead, AlertRuleCreate, AlertRuleRead, AlertRuleUpdate
from .alerting_service import AlertingService

router = APIRouter(prefix="/alert-rules", tags=["alert-rules"])
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])


@alerts_router.get("")
async def list_alerts(
    context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_session),
    status_filter: AlertStatus | None = Query(default=None, alias="status"),
) -> dict:
    alerts = await AlertingService(session, context).list_alerts(status=status_filter)
    return {"data": [AlertRead.model_validate(a) for a in alerts]}


@alerts_router.post("/{alert_id}/ack")
async def acknowledge_alert(
    alert_id: uuid.UUID,
    context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_session),
) -> dict:
    alert = await AlertingService(session, context).acknowledge_alert(alert_id)
    return {"data": AlertRead.model_validate(alert)}


@router.get("")
async def list_rules(
    context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rules = await AlertingService(session, context).list_rules()
    return {"data": [AlertRuleRead.model_validate(r) for r in rules]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: AlertRuleCreate,
    context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rule = await AlertingService(session, context).create_rule(payload)
    return {"data": AlertRuleRead.model_validate(rule)}


@router.patch("/{rule_id}")
async def update_rule(
    rule_id: uuid.UUID,
    payload: AlertRuleUpdate,
    context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rule = await AlertingService(session, context).update_rule(rule_id, payload)
    return {"data": AlertRuleRead.model_validate(rule)}


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: uuid.UUID,
    context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await AlertingService(session, context).delete_rule(rule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
