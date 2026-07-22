"""Add research run orchestration records.

Revision ID: 0010_research_runs
Revises: 0009_research_settlement_records
Create Date: 2026-07-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_research_runs"
down_revision: str | Sequence[str] | None = "0009_research_settlement_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_runs",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("research_session_id", sa.String(length=64), nullable=True),
        sa.Column("watchlist_item_id", sa.String(length=64), nullable=False),
        sa.Column("current_stage", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("vibe_run_id", sa.String(length=255), nullable=True),
        sa.Column("workflow", sa.String(length=128), nullable=False),
        sa.Column(
            "input_params",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("raw_output_reference", sa.String(length=500), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('running', 'completed', 'failed')",
            name="ck_research_runs_status",
        ),
        sa.ForeignKeyConstraint(
            ["watchlist_item_id"],
            ["watchlist_items.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("run_id"),
        sa.UniqueConstraint(
            "watchlist_item_id",
            "workflow",
            "input_params",
            name="uq_research_runs_idempotency",
        ),
    )
    op.create_index(
        "ix_research_runs_research_session_id",
        "research_runs",
        ["research_session_id"],
    )
    op.create_index(
        "ix_research_runs_watchlist_item_id",
        "research_runs",
        ["watchlist_item_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_research_runs_watchlist_item_id", table_name="research_runs")
    op.drop_index("ix_research_runs_research_session_id", table_name="research_runs")
    op.drop_table("research_runs")
