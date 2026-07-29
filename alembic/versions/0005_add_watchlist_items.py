"""add watchlist items

Revision ID: 0005_add_watchlist_items
Revises: 0004_review_settlement
Create Date: 2026-07-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0005_add_watchlist_items"
down_revision: str | None = "0004_review_settlement"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=64), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('active', 'archived')",
            name="ck_watchlist_status",
        ),
        sa.CheckConstraint(
            "(status = 'active' and archived_at is null) or "
            "(status = 'archived' and archived_at is not null)",
            name="ck_watchlist_archived_at",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_watchlist_updated_at",
        ),
    )
    op.create_index(
        "ix_watchlist_items_status",
        "watchlist_items",
        ["status"],
    )
    op.create_index(
        "ix_watchlist_items_market_symbol",
        "watchlist_items",
        ["market", "symbol"],
    )
    op.create_index(
        "uq_watchlist_active_symbol_market",
        "watchlist_items",
        ["market", "symbol"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_watchlist_active_symbol_market",
        table_name="watchlist_items",
    )
    op.drop_index("ix_watchlist_items_market_symbol", table_name="watchlist_items")
    op.drop_index("ix_watchlist_items_status", table_name="watchlist_items")
    op.drop_table("watchlist_items")
