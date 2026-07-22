"""add agent reports and hypotheses

Revision ID: 0007_agent_reports_hypotheses
Revises: 0006_add_research_sessions
Create Date: 2026-07-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0007_agent_reports_hypotheses"
down_revision: str | None = "0006_add_research_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_reports",
        sa.Column("report_id", sa.String(length=64), primary_key=True),
        sa.Column("research_session_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("stance", sa.String(length=255), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("raw_reference", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_session_id"],
            ["research_sessions.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "role in ('technical', 'fundamental', 'news', 'sentiment', 'capital_flow')",
            name="ck_agent_reports_role",
        ),
        sa.CheckConstraint(
            "status in ('active', 'archived')",
            name="ck_agent_reports_status",
        ),
        sa.CheckConstraint(
            "confidence >= 0 and confidence <= 1",
            name="ck_agent_reports_confidence",
        ),
        sa.CheckConstraint(
            "(status = 'active' and archived_at is null) or "
            "(status = 'archived' and archived_at is not null)",
            name="ck_agent_reports_archived_at",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_agent_reports_updated_at",
        ),
    )
    op.create_index(
        "ix_agent_reports_research_session_id",
        "agent_reports",
        ["research_session_id"],
    )
    op.create_index("ix_agent_reports_role", "agent_reports", ["role"])
    op.create_index("ix_agent_reports_status", "agent_reports", ["status"])
    op.create_index(
        "uq_agent_reports_active_session_role",
        "agent_reports",
        ["research_session_id", "role"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_table(
        "agent_report_evidence",
        sa.Column("report_id", sa.String(length=64), primary_key=True),
        sa.Column("evidence_id", sa.String(length=64), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["agent_reports.report_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.evidence_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "report_id",
            "position",
            name="uq_agent_report_evidence_position",
        ),
    )
    op.create_table(
        "hypotheses",
        sa.Column("hypothesis_id", sa.String(length=64), primary_key=True),
        sa.Column("research_session_id", sa.String(length=64), nullable=False),
        sa.Column("statement", sa.String(), nullable=False),
        sa.Column("rationale", sa.String(), nullable=False),
        sa.Column("direction", sa.String(length=64), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_session_id"],
            ["research_sessions.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status in ('proposed', 'validated', 'rejected', 'invalidated')",
            name="ck_hypotheses_status",
        ),
        sa.CheckConstraint(
            "confidence >= 0 and confidence <= 1",
            name="ck_hypotheses_confidence",
        ),
        sa.CheckConstraint(
            "horizon_days in (1, 3, 7)",
            name="ck_hypotheses_horizon",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_hypotheses_updated_at",
        ),
    )
    op.create_index(
        "ix_hypotheses_research_session_id",
        "hypotheses",
        ["research_session_id"],
    )
    op.create_index("ix_hypotheses_status", "hypotheses", ["status"])
    op.create_table(
        "hypothesis_reports",
        sa.Column("hypothesis_id", sa.String(length=64), primary_key=True),
        sa.Column("report_id", sa.String(length=64), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["hypothesis_id"],
            ["hypotheses.hypothesis_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["agent_reports.report_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "hypothesis_id",
            "position",
            name="uq_hypothesis_reports_position",
        ),
    )
    op.create_table(
        "hypothesis_evidence",
        sa.Column("hypothesis_id", sa.String(length=64), primary_key=True),
        sa.Column("evidence_id", sa.String(length=64), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["hypothesis_id"],
            ["hypotheses.hypothesis_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.evidence_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "hypothesis_id",
            "position",
            name="uq_hypothesis_evidence_position",
        ),
    )


def downgrade() -> None:
    op.drop_table("hypothesis_evidence")
    op.drop_table("hypothesis_reports")
    op.drop_index("ix_hypotheses_status", table_name="hypotheses")
    op.drop_index("ix_hypotheses_research_session_id", table_name="hypotheses")
    op.drop_table("hypotheses")
    op.drop_table("agent_report_evidence")
    op.drop_index("uq_agent_reports_active_session_role", table_name="agent_reports")
    op.drop_index("ix_agent_reports_status", table_name="agent_reports")
    op.drop_index("ix_agent_reports_role", table_name="agent_reports")
    op.drop_index(
        "ix_agent_reports_research_session_id",
        table_name="agent_reports",
    )
    op.drop_table("agent_reports")
