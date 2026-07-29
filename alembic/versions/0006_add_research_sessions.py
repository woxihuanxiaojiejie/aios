"""add research sessions

Revision ID: 0006_add_research_sessions
Revises: 0005_add_watchlist_items
Create Date: 2026-07-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0006_add_research_sessions"
down_revision: str | None = "0005_add_watchlist_items"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("watchlist_item_id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=64), nullable=False),
        sa.Column("watchlist_note_snapshot", sa.String(length=500), nullable=True),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("experiment_id", sa.String(length=64), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["watchlist_item_id"],
            ["watchlist_items.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["experiments.experiment_id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "horizon_days in (1, 3, 7)",
            name="ck_research_sessions_horizon",
        ),
        sa.CheckConstraint(
            "status in ('created', 'evidence_ready', 'cancelled')",
            name="ck_research_sessions_status",
        ),
        sa.CheckConstraint(
            "valid_until > as_of",
            name="ck_research_sessions_valid_until",
        ),
        sa.CheckConstraint(
            "(status = 'cancelled' and cancelled_at is not null) or "
            "(status <> 'cancelled' and cancelled_at is null)",
            name="ck_research_sessions_cancelled_at",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_research_sessions_updated_at",
        ),
    )
    op.create_index(
        "ix_research_sessions_watchlist_item_id",
        "research_sessions",
        ["watchlist_item_id"],
    )
    op.create_index(
        "ix_research_sessions_symbol",
        "research_sessions",
        ["symbol"],
    )
    op.create_index(
        "ix_research_sessions_market",
        "research_sessions",
        ["market"],
    )
    op.create_index(
        "ix_research_sessions_status",
        "research_sessions",
        ["status"],
    )
    op.create_index(
        "uq_research_sessions_active_scope",
        "research_sessions",
        ["watchlist_item_id", "as_of", "horizon_days"],
        unique=True,
        postgresql_where=sa.text("status <> 'cancelled'"),
    )
    op.create_table(
        "research_session_evidence",
        sa.Column("research_session_id", sa.String(length=64), primary_key=True),
        sa.Column("evidence_id", sa.String(length=64), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_session_id"],
            ["research_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.evidence_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "research_session_id",
            "position",
            name="uq_research_session_evidence_position",
        ),
    )


def downgrade() -> None:
    op.drop_table("research_session_evidence")
    op.drop_index("uq_research_sessions_active_scope", table_name="research_sessions")
    op.drop_index("ix_research_sessions_status", table_name="research_sessions")
    op.drop_index("ix_research_sessions_market", table_name="research_sessions")
    op.drop_index("ix_research_sessions_symbol", table_name="research_sessions")
    op.drop_index(
        "ix_research_sessions_watchlist_item_id",
        table_name="research_sessions",
    )
    op.drop_table("research_sessions")
