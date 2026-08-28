"""Logique d'authentification : verification des identifiants et lockout.

Messages volontairement generiques (pas d'enumeration de comptes). Apres N echecs
consecutifs, le compte est verrouille pour une duree configurable (protection
brute-force durable, persistee en base).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..core.exceptions import ProblemException
from .auth_models import Account, AccountStatus
from .phone import normalize_phone
from .security import verify_password


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    async def authenticate(self, *, phone_number: str, password: str) -> Account:
        normalized = normalize_phone(
            phone_number, default_region=self._settings.default_phone_region
        )
        account: Account | None = None
        if normalized is not None:
            account = await self._session.scalar(
                select(Account).where(Account.phone_number == normalized)
            )

        if account is None:
            raise ProblemException(401, "Identifiants invalides")

        now = datetime.now(UTC)
        if account.locked_until is not None and account.locked_until > now:
            raise ProblemException(401, "Compte temporairement verrouille")

        if account.status != AccountStatus.ACTIVE:
            raise ProblemException(401, "Identifiants invalides")

        if not verify_password(password, account.password_hash):
            account.failed_login_attempts += 1
            if account.failed_login_attempts >= self._settings.max_login_attempts:
                account.locked_until = now + timedelta(minutes=self._settings.account_lock_minutes)
                account.failed_login_attempts = 0
            await self._session.commit()
            raise ProblemException(401, "Identifiants invalides")

        account.failed_login_attempts = 0
        account.locked_until = None
        account.last_login_at = now
        await self._session.commit()
        await self._session.refresh(account)
        return account
