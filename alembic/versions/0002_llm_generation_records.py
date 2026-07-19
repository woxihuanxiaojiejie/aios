"""create llm generation records table

Revision ID: 0002_llm_generation_records
Revises: 0001_postgresql_storage_adapter
Create Date: 2026-07-19 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0002_llm_generation_records"
down_revision: str | None = "0001_postgresql_storage_adapter"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_generation_records",
        sa.Column("decision_id", sa.String(length=64), primary_key=True),
        sa.Column("experiment_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("evidence_snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["decisions.decision_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["experiments.experiment_id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_llm_generation_records_experiment_id",
        "llm_generation_records",
        ["experiment_id"],
    )
    op.create_index(
        "ix_llm_generation_records_created_at",
        "llm_generation_records",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_llm_generation_records_created_at",
        table_name="llm_generation_records",
    )
    op.drop_index(
        "ix_llm_generation_records_experiment_id",
        table_name="llm_generation_records",
    )
    op.drop_table("llm_generation_records")
