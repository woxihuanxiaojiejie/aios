"""create postgresql storage tables

Revision ID: 0001_postgresql_storage_adapter
Revises:
Create Date: 2026-07-19 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_postgresql_storage_adapter"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence",
        sa.Column("evidence_id", sa.String(length=64), primary_key=True),
        sa.Column("evidence_type", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("symbols", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("reliability", sa.Float(), nullable=False),
        sa.Column("content_hash", sa.String(length=255), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "reliability >= 0 and reliability <= 1",
            name="ck_evidence_reliability",
        ),
        sa.CheckConstraint(
            "available_at >= published_at",
            name="ck_evidence_available_at",
        ),
    )
    op.create_index("ix_evidence_content_hash", "evidence", ["content_hash"])
    op.create_index("ix_evidence_published_at", "evidence", ["published_at"])

    op.create_table(
        "experiments",
        sa.Column("experiment_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=255), nullable=False),
        sa.Column("agent_config_version", sa.String(length=255), nullable=False),
        sa.Column("dataset_snapshot", sa.String(length=255), nullable=False),
        sa.Column(
            "evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "finished_at is null or finished_at >= started_at",
            name="ck_experiments_finished_at",
        ),
    )
    op.create_index("ix_experiments_model", "experiments", ["model"])
    op.create_index("ix_experiments_prompt_version", "experiments", ["prompt_version"])
    op.create_index(
        "ix_experiments_agent_config_version",
        "experiments",
        ["agent_config_version"],
    )

    op.create_table(
        "decisions",
        sa.Column("decision_id", sa.String(length=64), primary_key=True),
        sa.Column("experiment_id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("horizon", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("expected_return", sa.Float(), nullable=False),
        sa.Column("max_expected_loss", sa.Float(), nullable=False),
        sa.Column(
            "evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("reasoning_summary", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 and confidence <= 1",
            name="ck_decisions_confidence",
        ),
        sa.CheckConstraint("valid_until > created_at", name="ck_decisions_valid_until"),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["experiments.experiment_id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_decisions_experiment_id", "decisions", ["experiment_id"])
    op.create_index("ix_decisions_symbol", "decisions", ["symbol"])
    op.create_index("ix_decisions_action", "decisions", ["action"])

    op.create_table(
        "reviews",
        sa.Column("review_id", sa.String(length=64), primary_key=True),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("actual_return", sa.Float(), nullable=False),
        sa.Column("direction_correct", sa.Boolean(), nullable=False),
        sa.Column("risk_limit_breached", sa.Boolean(), nullable=False),
        sa.Column("outcome", sa.String(length=64), nullable=False),
        sa.Column(
            "cause_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("review_summary", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["decisions.decision_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("decision_id", name="uq_reviews_decision_id"),
    )
    op.create_index("ix_reviews_outcome", "reviews", ["outcome"])

    op.create_table(
        "learnings",
        sa.Column("learning_id", sa.String(length=64), primary_key=True),
        sa.Column("review_id", sa.String(length=64), nullable=False),
        sa.Column("learning_type", sa.String(length=64), nullable=False),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("approval_status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["reviews.review_id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_learnings_learning_type", "learnings", ["learning_type"])
    op.create_index("ix_learnings_approval_status", "learnings", ["approval_status"])


def downgrade() -> None:
    op.drop_index("ix_learnings_approval_status", table_name="learnings")
    op.drop_index("ix_learnings_learning_type", table_name="learnings")
    op.drop_table("learnings")
    op.drop_index("ix_reviews_outcome", table_name="reviews")
    op.drop_table("reviews")
    op.drop_index("ix_decisions_action", table_name="decisions")
    op.drop_index("ix_decisions_symbol", table_name="decisions")
    op.drop_index("ix_decisions_experiment_id", table_name="decisions")
    op.drop_table("decisions")
    op.drop_index("ix_experiments_agent_config_version", table_name="experiments")
    op.drop_index("ix_experiments_prompt_version", table_name="experiments")
    op.drop_index("ix_experiments_model", table_name="experiments")
    op.drop_table("experiments")
    op.drop_index("ix_evidence_published_at", table_name="evidence")
    op.drop_index("ix_evidence_content_hash", table_name="evidence")
    op.drop_table("evidence")
