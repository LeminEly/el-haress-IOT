"""Schemas Pydantic de l'authentification (validation stricte)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .auth_models import AccountLanguage, AccountRole, AccountStatus


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(StrictModel):
    phone_number: str = Field(min_length=6, max_length=32)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(StrictModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AccountProfile(BaseModel):
    """Profil du compte authentifie (sortie /auth/me)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone_number: str
    company_name: str
    contact_email: str | None = None
    language: AccountLanguage
    role: AccountRole
    status: AccountStatus
    last_login_at: datetime | None = None
