"""Add BRAIN-001 unified evidence storage.

Revision ID: 0011_brain_evidence
Revises: 0010_research_runs
Create Date: 2026-07-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_brain_evidence"
down_revision: str | Sequence[str] | None = "0010_research_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "brain_evidence",
        sa.Column("evidence_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_identifier", sa.String(length=1024), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("raw_artifact_path", sa.String(length=2048), nullable=False),
        sa.Column(
            "provider_record",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.CheckConstraint(
            "available_at >= collected_at",
            name="ck_brain_evidence_available_at",
        ),
        sa.PrimaryKeyConstraint("evidence_id"),
    )
    for column in (
        "fingerprint",
        "source",
        "source_type",
        "published_at",
        "collected_at",
        "available_at",
    ):
        op.create_index(f"ix_brain_evidence_{column}", "brain_evidence", [column])


def downgrade() -> None:
    for column in (
        "available_at",
        "collected_at",
        "published_at",
        "source_type",
        "source",
        "fingerprint",
    ):
        op.drop_index(f"ix_brain_evidence_{column}", table_name="brain_evidence")
    op.drop_table("brain_evidence")
