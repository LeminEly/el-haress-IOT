"""Moteur d'alertes : evalue chaque nouvelle mesure contre les regles.

Mecanismes anti-spam :
- **gate de duree** : le seuil doit etre franchi pendant `duration_seconds`
  (suivi du premier franchissement via Redis) avant de declencher ;
- **cooldown** : pas de nouveau declenchement avant `cooldown_minutes` (cle Redis
  a TTL) ; sert aussi de deduplication.

Chaque declenchement est enregistre dans `alerts` (avec `account_id`) et dispatche
sur les canaux de la regle. El-Haress est l'unique autorite d'alerte.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import structlog
from redis.asyncio import Redis
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..auth.auth_models import Account
from .alerting_models import Alert, AlertCondition, AlertRule, AlertStatus

logger = structlog.get_logger(__name__)

_OPERATORS = {
    AlertCondition.GT: lambda value, threshold: value > threshold,
    AlertCondition.GTE: lambda value, threshold: value >= threshold,
    AlertCondition.LT: lambda value, threshold: value < threshold,
    AlertCondition.LTE: lambda value, threshold: value <= threshold,
}


@dataclass(frozen=True)
class ReadingEvent:
    account_id: uuid.UUID
    sensor_id: uuid.UUID
    value: float
    recorded_at: datetime


class Notifier(Protocol):
    async def dispatch(
        self,
        *,
        channels: Iterable[str],
        phone: str | None,
        email: str | None,
        subject: str,
        body: str,
    ) -> None: ...


class AlertEngine:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        redis: Redis,
        notifier: Notifier | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._redis = redis
        self._notifier = notifier

    async def evaluate(self, event: ReadingEvent) -> list[Alert]:
        triggered: list[Alert] = []
        async with self._session_factory() as session:
            rules = list(
                await session.scalars(
                    select(AlertRule).where(
                        AlertRule.account_id == event.account_id,
                        AlertRule.is_active.is_(True),
                        or_(
                            AlertRule.sensor_id == event.sensor_id,
                            AlertRule.sensor_id.is_(None),
                        ),
                    )
                )
            )
            account = await session.get(Account, event.account_id)
            for rule in rules:
                alert = await self._evaluate_rule(session, rule, event, account)
                if alert is not None:
                    triggered.append(alert)
        return triggered

    async def _evaluate_rule(
        self, session, rule: AlertRule, event: ReadingEvent, account: Account | None
    ) -> Alert | None:
        breach = _OPERATORS[rule.condition](event.value, rule.threshold)
        breach_key = f"alert:breach:{rule.id}:{event.sensor_id}"
        cooldown_key = f"alert:cooldown:{rule.id}:{event.sensor_id}"

        if not breach:
            await self._redis.delete(breach_key)
            return None

        if await self._redis.exists(cooldown_key):
            return None

        if rule.duration_seconds > 0 and not await self._duration_gate_passed(
            breach_key, rule.duration_seconds
        ):
            return None

        alert = Alert(
            account_id=event.account_id,
            alert_rule_id=rule.id,
            sensor_id=event.sensor_id,
            severity=rule.severity,
            value=event.value,
            status=AlertStatus.ACTIVE,
            triggered_at=event.recorded_at,
        )
        session.add(alert)
        await session.commit()
        await session.refresh(alert)

        await self._redis.set(cooldown_key, "1", ex=max(rule.cooldown_minutes * 60, 1))
        await self._redis.delete(breach_key)
        logger.info(
            "alert_triggered",
            rule_id=str(rule.id),
            sensor_id=str(event.sensor_id),
            severity=str(rule.severity),
            value=event.value,
        )

        if self._notifier is not None and account is not None:
            await self._notifier.dispatch(
                channels=list(rule.channels),
                phone=account.phone_number,
                email=account.contact_email,
                subject=f"[{rule.severity}] {rule.name}",
                body=(
                    f"Valeur {event.value} ({rule.condition} {rule.threshold}) "
                    f"a {event.recorded_at.isoformat()}"
                ),
            )
        return alert

    async def _duration_gate_passed(self, breach_key: str, duration_seconds: int) -> bool:
        now_ts = time.time()
        first_breach = await self._redis.get(breach_key)
        if first_breach is None:
            await self._redis.set(breach_key, now_ts, ex=max(duration_seconds * 3, 300))
            return False
        return now_ts - float(first_breach) >= duration_seconds
