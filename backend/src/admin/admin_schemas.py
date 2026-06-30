"""Schemas de la vue d'ensemble plateforme (SUPER_ADMIN)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from ..auth.auth_models import AccountLanguage, AccountStatus


class CompanyHealth(BaseModel):
    """Sante d'une entreprise vue par l'exploitant : etat, parc, alertes."""

    account_id: uuid.UUID
    company_name: str
    phone_number: str
    status: AccountStatus
    language: AccountLanguage
    sensors_total: int
    sensors_online: int
    active_alerts: int
    last_activity_at: datetime | None = None


class PlatformOverview(BaseModel):
    companies_total: int
    companies_active: int
    companies_suspended: int
    sensors_total: int
    sensors_online: int
    active_alerts: int
    companies: list[CompanyHealth]
