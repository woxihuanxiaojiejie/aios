"""add research settlement records

Revision ID: 0009_research_settlement_records
Revises: 0008_debate_decision_assembly
Create Date: 2026-07-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009_research_settlement_records"
down_revision: str | None = "0008_debate_decision_assembly"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_settlement_records",
        sa.Column("research_settlement_id", sa.String(length=64), primary_key=True),
        sa.Column("assembly_id", sa.String(length=64), nullable=False),
        sa.Column("research_session_id", sa.String(length=64), nullable=False),
        sa.Column("debate_id", sa.String(length=64), nullable=False),
        sa.Column("proposal_id", sa.String(length=64), nullable=False),
        sa.Column("risk_review_id", sa.String(length=64), nullable=False),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("outcome_id", sa.String(length=64), nullable=False),
        sa.Column("evaluation_id", sa.String(length=64), nullable=False),
        sa.Column("review_id", sa.String(length=64), nullable=False),
        sa.Column("learning_ids", JSONB(), nullable=False),
        sa.Column("evidence_ids", JSONB(), nullable=False),
        sa.Column("report_ids", JSONB(), nullable=False),
        sa.Column("hypothesis_ids", JSONB(), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assembly_id"],
            ["decision_assembly_records.assembly_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["research_session_id"],
            ["research_sessions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["debate_id"], ["debate_records.debate_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["decision_proposals.proposal_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["risk_review_id"],
            ["risk_reviews.risk_review_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["decision_id"], ["decisions.decision_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["outcome_id"],
            ["decision_outcomes.outcome_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_id"],
            ["decision_evaluations.evaluation_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["review_id"], ["reviews.review_id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "assembly_id",
            name="uq_research_settlements_assembly_id",
        ),
    )
    op.create_index(
        "ix_research_settlements_research_session_id",
        "research_settlement_records",
        ["research_session_id"],
    )
    op.create_index(
        "ix_research_settlements_decision_id",
        "research_settlement_records",
        ["decision_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_research_settlements_decision_id",
        table_name="research_settlement_records",
    )
    op.drop_index(
        "ix_research_settlements_research_session_id",
        table_name="research_settlement_records",
    )
    op.drop_table("research_settlement_records")
