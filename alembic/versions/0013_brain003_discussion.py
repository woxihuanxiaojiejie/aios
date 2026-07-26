"""Add BRAIN-003 discussion persistence.

Revision ID: 0013_brain003_discussion
Revises: 0012_brain002_skill_persistence
Create Date: 2026-07-26 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_brain003_discussion"
down_revision: str | Sequence[str] | None = "0012_brain002_skill_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discussion_executions",
        sa.Column("discussion_execution_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("skill_result_ids", postgresql.JSONB(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("prompt_version", sa.String(length=128), nullable=True),
        sa.Column("token_usage", postgresql.JSONB(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("raw_response", sa.String(), nullable=True),
        sa.Column("parsed_response", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "finished_at is null or finished_at >= started_at",
            name="ck_discussion_executions_finished_at",
        ),
        sa.CheckConstraint(
            "latency_ms is null or latency_ms >= 0",
            name="ck_discussion_executions_latency_ms",
        ),
        sa.CheckConstraint(
            "retry_count >= 0",
            name="ck_discussion_executions_retry_count",
        ),
        sa.PrimaryKeyConstraint("discussion_execution_id"),
    )
    for column in ("task_id", "status", "started_at", "created_at"):
        op.create_index(
            f"ix_discussion_executions_{column}",
            "discussion_executions",
            [column],
        )

    op.create_table(
        "discussion_results",
        sa.Column("discussion_result_id", sa.String(length=64), nullable=False),
        sa.Column("discussion_execution_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("skill_result_ids", postgresql.JSONB(), nullable=False),
        sa.Column("conflicts", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_reviews", postgresql.JSONB(), nullable=False),
        sa.Column("counter_arguments", postgresql.JSONB(), nullable=False),
        sa.Column("revision_suggestions", postgresql.JSONB(), nullable=False),
        sa.Column("discussion_summary", sa.String(), nullable=False),
        sa.Column("discussion_confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "discussion_confidence >= 0 and discussion_confidence <= 1",
            name="ck_discussion_results_confidence",
        ),
        sa.PrimaryKeyConstraint("discussion_result_id"),
    )
    op.create_index(
        "ix_discussion_results_execution_id",
        "discussion_results",
        ["discussion_execution_id"],
    )
    for column in ("task_id", "created_at"):
        op.create_index(
            f"ix_discussion_results_{column}",
            "discussion_results",
            [column],
        )


def downgrade() -> None:
    for column in ("created_at", "task_id"):
        op.drop_index(
            f"ix_discussion_results_{column}",
            table_name="discussion_results",
        )
    op.drop_index(
        "ix_discussion_results_execution_id",
        table_name="discussion_results",
    )
    op.drop_table("discussion_results")

    for column in ("created_at", "started_at", "status", "task_id"):
        op.drop_index(
            f"ix_discussion_executions_{column}",
            table_name="discussion_executions",
        )
    op.drop_table("discussion_executions")
