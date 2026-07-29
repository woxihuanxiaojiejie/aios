"""Add scheduler runtime status records.

Revision ID: 0023_scheduler_runtime_status
Revises: 0022_watchlist_scheduler_runtime
Create Date: 2026-07-28 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

revision: str = "0023_scheduler_runtime_status"
down_revision: str | Sequence[str] | None = "0022_watchlist_scheduler_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from alembic import op as alembic_op

    alembic_op.create_table(
        "scheduler_runtimes",
        sa.Column("scheduler_instance_id", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("scheduler_instance_id"),
    )
    alembic_op.create_index(
        "ix_scheduler_runtimes_last_heartbeat",
        "scheduler_runtimes",
        ["last_heartbeat_at"],
    )
    alembic_op.create_table(
        "scheduler_job_runs",
        sa.Column("job_run_id", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=True),
        sa.Column("success_count", sa.Integer(), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=True),
        sa.Column("result_message", sa.String(length=500), nullable=True),
        sa.Column("error_type", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("job_run_id"),
    )
    alembic_op.create_index(
        "ix_scheduler_job_runs_job_completed",
        "scheduler_job_runs",
        ["job_id", "completed_at"],
    )


def downgrade() -> None:
    from alembic import op as alembic_op

    alembic_op.drop_index(
        "ix_scheduler_job_runs_job_completed",
        table_name="scheduler_job_runs",
    )
    alembic_op.drop_table("scheduler_job_runs")
    alembic_op.drop_index(
        "ix_scheduler_runtimes_last_heartbeat",
        table_name="scheduler_runtimes",
    )
    alembic_op.drop_table("scheduler_runtimes")
