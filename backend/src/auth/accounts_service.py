"""Gestion des comptes entreprises (operations reservees au SUPER_ADMIN).

Aucune auto-inscription : les comptes sont crees exclusivement ici. Chaque action
sensible est tracee dans le journal d'audit append-only.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..core.exceptions import ProblemException
from ..db.audit_models import AuditLog
from .accounts_schemas import AccountCreate
from .auth_models import Account, AccountStatus
from .phone import normalize_phone
from .security import hash_password


class AccountsService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    async def create(self, data: AccountCreate, *, actor_id: uuid.UUID) -> Account:
        normalized = normalize_phone(
            data.phone_number, default_region=self._settings.default_phone_region
        )
        if normalized is None:
            raise ProblemException(422, "Numero de telephone invalide")

        existing = await self._session.scalar(
            select(Account).where(Account.phone_number == normalized)
        )
        if existing is not None:
            raise ProblemException(409, "Numero de telephone deja utilise")

        account = Account(
            phone_number=normalized,
            password_hash=hash_password(data.password, rounds=self._settings.bcrypt_rounds),
            company_name=data.company_name,
            role=data.role,
            status=AccountStatus.ACTIVE,
        )
        self._session.add(account)
        await self._session.flush()
        self._session.add(
            AuditLog(
                actor_account_id=actor_id,
                account_id=account.id,
                action="account.create",
                entity_type="account",
                entity_id=account.id,
            )
        )
        await self._session.commit()
        await self._session.refresh(account)
        return account

    async def list_all(self) -> list[Account]:
        result = await self._session.scalars(select(Account).order_by(Account.created_at.desc()))
        return list(result)

    async def set_status(
        self, account_id: uuid.UUID, status: AccountStatus, *, actor_id: uuid.UUID
    ) -> Account:
        account = await self._session.get(Account, account_id)
        if account is None:
            raise ProblemException(404, "Compte introuvable")

        account.status = status
        self._session.add(
            AuditLog(
                actor_account_id=actor_id,
                account_id=account.id,
                action="account.status_change",
                entity_type="account",
                entity_id=account.id,
                data={"status": status.value},
            )
        )
        await self._session.commit()
        await self._session.refresh(account)
        return account
