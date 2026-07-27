"""Add Watchlist scheduler runtime fields.

Revision ID: 0022_watchlist_scheduler_runtime
Revises: 0021_sim_execution
Create Date: 2026-07-27 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

revision: str = "0022_watchlist_scheduler_runtime"
down_revision: str | Sequence[str] | None = "0021_sim_execution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from alembic import op as alembic_op

    alembic_op.add_column(
        "watchlist_items",
        sa.Column(
            "auto_research_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    alembic_op.add_column(
        "watchlist_items",
        sa.Column(
            "research_horizon_days",
            sa.Integer(),
            nullable=False,
            server_default="3",
        ),
    )
    alembic_op.add_column(
        "watchlist_items",
        sa.Column(
            "schedule_time",
            sa.Time(),
            nullable=False,
            server_default="15:00:00",
        ),
    )
    alembic_op.add_column(
        "watchlist_items",
        sa.Column(
            "schedule_timezone",
            sa.String(length=64),
            nullable=False,
            server_default="Asia/Shanghai",
        ),
    )
    alembic_op.add_column(
        "watchlist_items",
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
    )
    alembic_op.add_column(
        "watchlist_items",
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
    )
    alembic_op.create_check_constraint(
        "ck_watchlist_research_horizon_days",
        "watchlist_items",
        "research_horizon_days in (1, 3, 7)",
    )
    alembic_op.create_index(
        "ix_watchlist_items_next_run",
        "watchlist_items",
        ["auto_research_enabled", "next_run_at"],
    )

    alembic_op.add_column(
        "research_runs",
        sa.Column("symbol", sa.String(length=64), nullable=True),
    )
    alembic_op.add_column(
        "research_runs",
        sa.Column("research_window_key", sa.String(length=255), nullable=True),
    )
    alembic_op.add_column(
        "research_runs",
        sa.Column("failed_stage", sa.String(length=64), nullable=True),
    )
    alembic_op.add_column(
        "research_runs",
        sa.Column("error_type", sa.String(length=128), nullable=True),
    )
    alembic_op.add_column(
        "research_runs",
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    alembic_op.create_index(
        "ix_research_runs_window_key",
        "research_runs",
        ["research_window_key"],
    )


def downgrade() -> None:
    from alembic import op as alembic_op

    alembic_op.drop_index("ix_research_runs_window_key", table_name="research_runs")
    alembic_op.drop_column("research_runs", "finished_at")
    alembic_op.drop_column("research_runs", "error_type")
    alembic_op.drop_column("research_runs", "failed_stage")
    alembic_op.drop_column("research_runs", "research_window_key")
    alembic_op.drop_column("research_runs", "symbol")

    alembic_op.drop_index("ix_watchlist_items_next_run", table_name="watchlist_items")
    alembic_op.drop_constraint(
        "ck_watchlist_research_horizon_days",
        "watchlist_items",
        type_="check",
    )
    alembic_op.drop_column("watchlist_items", "last_run_at")
    alembic_op.drop_column("watchlist_items", "next_run_at")
    alembic_op.drop_column("watchlist_items", "schedule_timezone")
    alembic_op.drop_column("watchlist_items", "schedule_time")
    alembic_op.drop_column("watchlist_items", "research_horizon_days")
    alembic_op.drop_column("watchlist_items", "auto_research_enabled")
