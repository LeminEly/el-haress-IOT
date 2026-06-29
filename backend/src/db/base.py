"""Socle ORM : base declarative, convention de nommage et mixins partages.

- Convention de nommage explicite des contraintes/index : noms de migrations
  stables et previsibles.
- `UUIDPrimaryKeyMixin` : identifiant UUID sur chaque table (jamais d'entier
  sequentiel expose).
- `TimestampMixin` : `created_at` / `updated_at` sur les tables metier.
- `TenantMixin` : colonne `account_id` NOT NULL (isolation multi-entreprises).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TenantMixin:
    """Rattachement a une entreprise. L'`account_id` vient du contexte JWT en
    couche service, jamais d'un parametre client (voir module tenancy)."""

    @declared_attr.directive
    @classmethod
    def account_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
