"""Add BRAIN-004 decision persistence.

Revision ID: 0014_brain004_decision
Revises: 0013_brain003_discussion
Create Date: 2026-07-26 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_brain004_decision"
down_revision: str | Sequence[str] | None = "0013_brain003_discussion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_executions",
        sa.Column("decision_execution_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("discussion_result_id", sa.String(length=64), nullable=False),
        sa.Column("skill_result_ids", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False),
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
            name="ck_decision_executions_finished_at",
        ),
        sa.CheckConstraint(
            "latency_ms is null or latency_ms >= 0",
            name="ck_decision_executions_latency_ms",
        ),
        sa.CheckConstraint(
            "retry_count >= 0",
            name="ck_decision_executions_retry_count",
        ),
        sa.PrimaryKeyConstraint("decision_execution_id"),
    )
    for column in (
        "task_id",
        "discussion_result_id",
        "status",
        "started_at",
        "created_at",
    ):
        op.create_index(
            f"ix_decision_executions_{column}",
            "decision_executions",
            [column],
        )

    op.create_table(
        "decision_results",
        sa.Column("decision_result_id", sa.String(length=64), nullable=False),
        sa.Column("decision_execution_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("discussion_result_id", sa.String(length=64), nullable=False),
        sa.Column("skill_result_ids", postgresql.JSONB(), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("reasoning", postgresql.JSONB(), nullable=False),
        sa.Column("supporting_skills", postgresql.JSONB(), nullable=False),
        sa.Column("opposing_skills", postgresql.JSONB(), nullable=False),
        sa.Column("discussion_refs", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=False),
        sa.Column("risks", postgresql.JSONB(), nullable=False),
        sa.Column("rejected_directions", postgresql.JSONB(), nullable=False),
        sa.Column("decision_summary", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 and confidence <= 1",
            name="ck_decision_results_confidence",
        ),
        sa.PrimaryKeyConstraint("decision_result_id"),
    )
    for column in (
        "decision_execution_id",
        "task_id",
        "discussion_result_id",
        "direction",
        "action",
        "created_at",
    ):
        op.create_index(
            f"ix_decision_results_{column}",
            "decision_results",
            [column],
        )


def downgrade() -> None:
    for column in (
        "created_at",
        "action",
        "direction",
        "discussion_result_id",
        "task_id",
        "decision_execution_id",
    ):
        op.drop_index(
            f"ix_decision_results_{column}",
            table_name="decision_results",
        )
    op.drop_table("decision_results")

    for column in (
        "created_at",
        "started_at",
        "status",
        "discussion_result_id",
        "task_id",
    ):
        op.drop_index(
            f"ix_decision_executions_{column}",
            table_name="decision_executions",
        )
    op.drop_table("decision_executions")
