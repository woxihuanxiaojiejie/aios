"""Add core business Evidence compatibility fields.

Revision ID: 0016_core_evidence_fields
Revises: 0015_nullable_legacy_links
Create Date: 2026-07-26 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_core_evidence_fields"
down_revision: str | Sequence[str] | None = "0015_nullable_legacy_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("title", sa.String(), nullable=True))
    op.add_column("evidence", sa.Column("raw_content", sa.String(), nullable=True))
    op.add_column(
        "evidence",
        sa.Column("raw_response", postgresql.JSONB(), nullable=True),
    )
    op.add_column("evidence", sa.Column("source_type", sa.String(length=64)))
    op.add_column("evidence", sa.Column("source_identifier", sa.String(length=1024)))
    op.add_column("evidence", sa.Column("source_url", sa.String(length=2048)))
    op.add_column(
        "evidence",
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "evidence",
        sa.Column(
            "entities",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column("evidence", sa.Column("fingerprint", sa.String(length=64)))
    op.add_column("evidence", sa.Column("credibility", sa.Float()))
    op.add_column("evidence", sa.Column("freshness", sa.String(length=64)))
    op.add_column(
        "evidence",
        sa.Column(
            "processing_status",
            sa.String(length=64),
            nullable=False,
            server_default="parsed",
        ),
    )
    op.add_column("evidence", sa.Column("parse_error", sa.String()))
    op.add_column(
        "evidence",
        sa.Column("legacy_brain_evidence_id", sa.String(length=36), nullable=True),
    )
    op.alter_column("evidence", "entities", server_default=None)
    op.alter_column("evidence", "processing_status", server_default=None)

    op.create_index("ix_evidence_source_type", "evidence", ["source_type"])
    op.create_index(
        "ix_evidence_source_identifier",
        "evidence",
        ["source_identifier"],
    )
    op.create_index("ix_evidence_collected_at", "evidence", ["collected_at"])
    op.create_index("ix_evidence_fingerprint", "evidence", ["fingerprint"])
    op.create_index(
        "ix_evidence_processing_status",
        "evidence",
        ["processing_status"],
    )
    op.create_index(
        "uq_evidence_legacy_brain_evidence_id",
        "evidence",
        ["legacy_brain_evidence_id"],
        unique=True,
        postgresql_where=sa.text("legacy_brain_evidence_id is not null"),
    )


def downgrade() -> None:
    op.drop_index("uq_evidence_legacy_brain_evidence_id", table_name="evidence")
    op.drop_index("ix_evidence_processing_status", table_name="evidence")
    op.drop_index("ix_evidence_fingerprint", table_name="evidence")
    op.drop_index("ix_evidence_collected_at", table_name="evidence")
    op.drop_index("ix_evidence_source_identifier", table_name="evidence")
    op.drop_index("ix_evidence_source_type", table_name="evidence")

    op.drop_column("evidence", "legacy_brain_evidence_id")
    op.drop_column("evidence", "parse_error")
    op.drop_column("evidence", "processing_status")
    op.drop_column("evidence", "freshness")
    op.drop_column("evidence", "credibility")
    op.drop_column("evidence", "fingerprint")
    op.drop_column("evidence", "entities")
    op.drop_column("evidence", "collected_at")
    op.drop_column("evidence", "source_url")
    op.drop_column("evidence", "source_identifier")
    op.drop_column("evidence", "source_type")
    op.drop_column("evidence", "raw_response")
    op.drop_column("evidence", "raw_content")
    op.drop_column("evidence", "title")
