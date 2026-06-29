"""Logique metier des regles d'alerte, filtree par `account_id`.

Une regle peut cibler un capteur : ce capteur doit appartenir a l'entreprise
courante (verifie via le contexte de tenance, jamais via un parametre client).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import ProblemException
from ..sensors.sensors_models import Sensor
from ..tenancy.tenancy import TenantContext
from .alerting_models import AlertRule
from .alerting_schemas import AlertRuleCreate, AlertRuleUpdate


class AlertingService:
    def __init__(self, session: AsyncSession, context: TenantContext) -> None:
        self._session = session
        self._account_id = context.account_id

    async def _assert_sensor_owned(self, sensor_id: uuid.UUID | None) -> None:
        if sensor_id is None:
            return
        owned = await self._session.scalar(
            select(Sensor.id).where(Sensor.id == sensor_id, Sensor.account_id == self._account_id)
        )
        if owned is None:
            raise ProblemException(422, "Capteur invalide")

    async def list_rules(self) -> list[AlertRule]:
        return list(
            await self._session.scalars(
                select(AlertRule)
                .where(AlertRule.account_id == self._account_id)
                .order_by(AlertRule.created_at.desc())
            )
        )

    async def _get_owned_rule(self, rule_id: uuid.UUID) -> AlertRule:
        rule = await self._session.scalar(
            select(AlertRule).where(
                AlertRule.id == rule_id, AlertRule.account_id == self._account_id
            )
        )
        if rule is None:
            raise ProblemException(404, "Regle introuvable")
        return rule

    async def create_rule(self, data: AlertRuleCreate) -> AlertRule:
        await self._assert_sensor_owned(data.sensor_id)
        rule = AlertRule(
            account_id=self._account_id,
            sensor_id=data.sensor_id,
            name=data.name,
            condition=data.condition,
            threshold=data.threshold,
            duration_seconds=data.duration_seconds,
            cooldown_minutes=data.cooldown_minutes,
            severity=data.severity,
            channels=[c.value for c in data.channels],
            is_active=data.is_active,
        )
        self._session.add(rule)
        await self._session.commit()
        await self._session.refresh(rule)
        return rule

    async def update_rule(self, rule_id: uuid.UUID, data: AlertRuleUpdate) -> AlertRule:
        rule = await self._get_owned_rule(rule_id)
        fields = data.model_dump(exclude_unset=True)
        if "channels" in fields and fields["channels"] is not None:
            fields["channels"] = [c.value for c in data.channels]
        for key, value in fields.items():
            setattr(rule, key, value)
        await self._session.commit()
        await self._session.refresh(rule)
        return rule

    async def delete_rule(self, rule_id: uuid.UUID) -> None:
        rule = await self._get_owned_rule(rule_id)
        await self._session.delete(rule)
        await self._session.commit()
