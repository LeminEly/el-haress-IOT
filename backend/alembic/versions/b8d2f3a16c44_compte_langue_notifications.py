"""compte langue des notifications

Revision ID: b8d2f3a16c44
Revises: a7c4e1f9b2d8
Create Date: 2026-06-29 21:55:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8d2f3a16c44"
down_revision: str | None = "a7c4e1f9b2d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column(
            "language",
            sa.Enum("fr", "ar", "en", native_enum=False, length=2),
            nullable=False,
            server_default="fr",
        ),
    )


def downgrade() -> None:
    op.drop_column("accounts", "language")
