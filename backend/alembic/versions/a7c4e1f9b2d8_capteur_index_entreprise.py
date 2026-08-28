"""capteur index par entreprise (nom el-haress-NN)

Revision ID: a7c4e1f9b2d8
Revises: d517f8347796
Create Date: 2026-06-29 21:05:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c4e1f9b2d8"
down_revision: str | None = "d517f8347796"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sensors", sa.Column("device_index", sa.Integer(), nullable=True))
    # Backfill : numerotation sequentielle par entreprise, ordre de creation.
    op.execute(
        """
        UPDATE sensors AS s
        SET device_index = sub.rn
        FROM (
            SELECT id,
                   row_number() OVER (PARTITION BY account_id ORDER BY created_at, id) AS rn
            FROM sensors
        ) AS sub
        WHERE s.id = sub.id
        """
    )


def downgrade() -> None:
    op.drop_column("sensors", "device_index")
