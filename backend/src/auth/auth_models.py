"""Modeles d'authentification : comptes entreprises.

Un compte = une entreprise (relation un-a-un). Le compte est l'unite de tenance ;
il ne porte donc pas lui-meme d'`account_id` (il en est la racine).
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AccountRole(enum.StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    COMPANY = "COMPANY"


class AccountStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class AccountLanguage(enum.StrEnum):
    FR = "fr"
    AR = "ar"
    EN = "en"


class Account(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "accounts"

    # Identifiant de connexion : numero de telephone normalise (format international).
    phone_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Destinataire des notifications email (optionnel ; le telephone sert SMS/WhatsApp).
    contact_email: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[AccountRole] = mapped_column(
        Enum(AccountRole, native_enum=False, length=20), nullable=False
    )
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, native_enum=False, length=20),
        default=AccountStatus.ACTIVE,
        nullable=False,
    )
    # Langue des notifications (WhatsApp/SMS/Email) envoyees a ce compte.
    # values_callable : on persiste la valeur ("fr"/"ar"/"en"), pas le nom de membre,
    # pour rester coherent avec les codes de langue (i18n) et la migration.
    language: Mapped[AccountLanguage] = mapped_column(
        Enum(
            AccountLanguage,
            native_enum=False,
            length=2,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        default=AccountLanguage.FR,
        server_default=AccountLanguage.FR.value,
        nullable=False,
    )

    # Protection contre la force brute (lockout durable, cote base).
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
