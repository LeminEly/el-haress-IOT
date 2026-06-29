"""Schemas Pydantic de gestion des comptes (SUPER_ADMIN)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .auth_models import AccountRole, AccountStatus
from .auth_schemas import StrictModel


class AccountCreate(StrictModel):
    phone_number: str = Field(min_length=6, max_length=32)
    password: str = Field(min_length=10, max_length=128)
    company_name: str = Field(min_length=1, max_length=255)
    contact_email: str | None = Field(default=None, max_length=255)
    role: AccountRole = AccountRole.COMPANY


class AccountUpdate(StrictModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=255)
    contact_email: str | None = Field(default=None, max_length=255)
    status: AccountStatus | None = None


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone_number: str
    company_name: str
    contact_email: str | None = None
    role: AccountRole
    status: AccountStatus
    created_at: datetime
    last_login_at: datetime | None = None
