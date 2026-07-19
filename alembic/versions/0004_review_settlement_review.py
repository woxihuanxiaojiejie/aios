"""align reviews with settlement evaluation mapping

Revision ID: 0004_review_settlement
Revises: 0003_decision_settlement
Create Date: 2026-07-19 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0004_review_settlement"
down_revision: str | None = "0003_decision_settlement"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "reviews",
        "actual_return",
        existing_type=sa.Float(),
        type_=sa.Numeric(24, 12),
        existing_nullable=False,
        nullable=True,
        postgresql_using="actual_return::numeric(24, 12)",
    )
    op.alter_column(
        "reviews",
        "direction_correct",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        "reviews",
        "risk_limit_breached",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "reviews",
        "risk_limit_breached",
        existing_type=sa.Boolean(),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "reviews",
        "direction_correct",
        existing_type=sa.Boolean(),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "reviews",
        "actual_return",
        existing_type=sa.Numeric(24, 12),
        type_=sa.Float(),
        existing_nullable=True,
        nullable=False,
        postgresql_using="actual_return::double precision",
    )
