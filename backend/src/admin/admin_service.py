"""Vue d'ensemble plateforme — agregats globaux, reserves au SUPER_ADMIN.

C'est l'unique endroit ou l'on agrege au-dela d'une seule entreprise. L'acces est
strictement controle par `require_role(SUPER_ADMIN)` cote route ; aucune entreprise
n'atteint ce service. Le perimetre reste interne (l'exploitant supervise son parc).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..alerting.alerting_models import Alert, AlertStatus
from ..auth.auth_models import Account, AccountRole, AccountStatus
from ..config import get_settings
from ..sensors.sensors_models import Sensor
from .admin_schemas import CompanyHealth, PlatformOverview


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def overview(self) -> PlatformOverview:
        cutoff = datetime.now(UTC) - timedelta(seconds=get_settings().sensor_offline_after_seconds)

        companies = list(
            await self._session.scalars(
                select(Account)
                .where(Account.role == AccountRole.COMPANY)
                .order_by(Account.company_name)
            )
        )

        # Parc par entreprise : total, en ligne (mesure recente), derniere activite.
        online = and_(
            Sensor.is_active.is_(True),
            Sensor.last_seen_at.is_not(None),
            Sensor.last_seen_at >= cutoff,
        )
        sensor_rows = await self._session.execute(
            select(
                Sensor.account_id,
                func.count(),
                func.count().filter(online),
                func.max(Sensor.last_seen_at),
            ).group_by(Sensor.account_id)
        )
        sensors_by_account = {row[0]: (row[1], row[2], row[3]) for row in sensor_rows}

        alert_rows = await self._session.execute(
            select(Alert.account_id, func.count())
            .where(Alert.status == AlertStatus.ACTIVE)
            .group_by(Alert.account_id)
        )
        alerts_by_account = {row[0]: row[1] for row in alert_rows}

        health: list[CompanyHealth] = []
        for account in companies:
            total, online_count, last_activity = sensors_by_account.get(account.id, (0, 0, None))
            health.append(
                CompanyHealth(
                    account_id=account.id,
                    company_name=account.company_name,
                    phone_number=account.phone_number,
                    status=account.status,
                    language=account.language,
                    sensors_total=total,
                    sensors_online=online_count,
                    active_alerts=alerts_by_account.get(account.id, 0),
                    last_activity_at=last_activity,
                )
            )

        return PlatformOverview(
            companies_total=len(companies),
            companies_active=sum(1 for c in companies if c.status == AccountStatus.ACTIVE),
            companies_suspended=sum(1 for c in companies if c.status == AccountStatus.SUSPENDED),
            sensors_total=sum(h.sensors_total for h in health),
            sensors_online=sum(h.sensors_online for h in health),
            active_alerts=sum(h.active_alerts for h in health),
            companies=health,
        )
