"""Add BRAIN-002 skill persistence.

Revision ID: 0012_brain002_skill_persistence
Revises: 0011_brain_evidence
Create Date: 2026-07-24 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_brain002_skill_persistence"
down_revision: str | Sequence[str] | None = "0011_brain_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "skill_definitions",
        sa.Column("definition_id", sa.String(length=64), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("supported_markets", postgresql.JSONB(), nullable=False),
        sa.Column("supported_asset_types", postgresql.JSONB(), nullable=False),
        sa.Column("supported_horizons", postgresql.JSONB(), nullable=False),
        sa.Column("required_evidence_types", postgresql.JSONB(), nullable=False),
        sa.Column("input_schema", postgresql.JSONB(), nullable=False),
        sa.Column("output_schema", postgresql.JSONB(), nullable=False),
        sa.Column("trigger_conditions", postgresql.JSONB(), nullable=False),
        sa.Column("dependencies", postgresql.JSONB(), nullable=False),
        sa.Column("conflicts", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("definition_id"),
        sa.UniqueConstraint(
            "skill_id",
            "version",
            name="uq_skill_definitions_version",
        ),
    )
    op.create_index("ix_skill_definitions_skill_id", "skill_definitions", ["skill_id"])
    op.create_index("ix_skill_definitions_status", "skill_definitions", ["status"])
    op.create_index(
        "ix_skill_definitions_created_at", "skill_definitions", ["created_at"]
    )

    op.create_table(
        "analysis_tasks",
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=64), nullable=False),
        sa.Column("asset_type", sa.String(length=64), nullable=False),
        sa.Column("horizon", sa.String(length=64), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False),
        sa.Column("user_constraints", postgresql.JSONB(), nullable=False),
        sa.Column("requested_skill_ids", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("task_id"),
    )
    for column in ("symbol", "market", "as_of", "created_at"):
        op.create_index(f"ix_analysis_tasks_{column}", "analysis_tasks", [column])

    op.create_table(
        "skill_executions",
        sa.Column("execution_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=False),
        sa.Column("skill_version", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("prompt_version", sa.String(length=128), nullable=True),
        sa.Column("token_usage", postgresql.JSONB(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(), nullable=True),
        sa.CheckConstraint(
            "finished_at is null or finished_at >= started_at",
            name="ck_skill_executions_finished_at",
        ),
        sa.CheckConstraint(
            "latency_ms is null or latency_ms >= 0",
            name="ck_skill_executions_latency_ms",
        ),
        sa.CheckConstraint("retry_count >= 0", name="ck_skill_executions_retry_count"),
        sa.PrimaryKeyConstraint("execution_id"),
    )
    for column in ("task_id", "skill_id", "status", "started_at"):
        op.create_index(f"ix_skill_executions_{column}", "skill_executions", [column])

    op.create_table(
        "skill_results",
        sa.Column("result_id", sa.String(length=64), nullable=False),
        sa.Column("execution_id", sa.String(length=64), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=False),
        sa.Column("skill_version", sa.String(length=64), nullable=False),
        sa.Column("conclusion", sa.String(), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("supporting_evidence_ids", postgresql.JSONB(), nullable=False),
        sa.Column("contradicting_evidence_ids", postgresql.JSONB(), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(), nullable=False),
        sa.Column("risk_factors", postgresql.JSONB(), nullable=False),
        sa.Column("invalid_conditions", postgresql.JSONB(), nullable=False),
        sa.Column("missing_information", postgresql.JSONB(), nullable=False),
        sa.Column("reasoning_summary", sa.String(), nullable=False),
        sa.Column("raw_output", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 and confidence <= 1",
            name="ck_skill_results_confidence",
        ),
        sa.PrimaryKeyConstraint("result_id"),
    )
    for column in ("execution_id", "skill_id", "direction", "created_at"):
        op.create_index(f"ix_skill_results_{column}", "skill_results", [column])


def downgrade() -> None:
    for column in ("created_at", "direction", "skill_id", "execution_id"):
        op.drop_index(f"ix_skill_results_{column}", table_name="skill_results")
    op.drop_table("skill_results")

    for column in ("started_at", "status", "skill_id", "task_id"):
        op.drop_index(f"ix_skill_executions_{column}", table_name="skill_executions")
    op.drop_table("skill_executions")

    for column in ("created_at", "as_of", "market", "symbol"):
        op.drop_index(f"ix_analysis_tasks_{column}", table_name="analysis_tasks")
    op.drop_table("analysis_tasks")

    for column in ("created_at", "status", "skill_id"):
        op.drop_index(f"ix_skill_definitions_{column}", table_name="skill_definitions")
    op.drop_table("skill_definitions")
