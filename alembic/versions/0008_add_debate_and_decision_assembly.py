"""add debate and decision assembly

Revision ID: 0008_debate_decision_assembly
Revises: 0007_agent_reports_hypotheses
Create Date: 2026-07-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008_debate_decision_assembly"
down_revision: str | None = "0007_agent_reports_hypotheses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "debate_records",
        sa.Column("debate_id", sa.String(length=64), primary_key=True),
        sa.Column("research_session_id", sa.String(length=64), nullable=False),
        sa.Column("report_ids", JSONB(), nullable=False),
        sa.Column("hypothesis_ids", JSONB(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("final_decision_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_session_id"], ["research_sessions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["final_decision_id"], ["decisions.decision_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "status in ('open', 'assembled', 'cancelled')",
            name="ck_debate_records_status",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_debate_records_updated_at",
        ),
    )
    op.create_index(
        "ix_debate_records_research_session_id",
        "debate_records",
        ["research_session_id"],
    )
    op.create_table(
        "debate_record_reports",
        sa.Column("debate_id", sa.String(length=64), primary_key=True),
        sa.Column("report_id", sa.String(length=64), primary_key=True),
        sa.ForeignKeyConstraint(
            ["debate_id"], ["debate_records.debate_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["report_id"], ["agent_reports.report_id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "debate_record_hypotheses",
        sa.Column("debate_id", sa.String(length=64), primary_key=True),
        sa.Column("hypothesis_id", sa.String(length=64), primary_key=True),
        sa.ForeignKeyConstraint(
            ["debate_id"], ["debate_records.debate_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["hypothesis_id"], ["hypotheses.hypothesis_id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "debate_statements",
        sa.Column("statement_id", sa.String(length=64), primary_key=True),
        sa.Column("debate_id", sa.String(length=64), nullable=False),
        sa.Column("agent_report_id", sa.String(length=64), nullable=False),
        sa.Column("hypothesis_id", sa.String(length=64), nullable=False),
        sa.Column("stance", sa.String(length=32), nullable=False),
        sa.Column("reasoning", sa.String(), nullable=False),
        sa.Column("evidence_ids", JSONB(), nullable=False),
        sa.Column("confidence_before", sa.Float(), nullable=False),
        sa.Column("confidence_after", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["debate_id"], ["debate_records.debate_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["agent_report_id"], ["agent_reports.report_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["hypothesis_id"], ["hypotheses.hypothesis_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "stance in ('support', 'oppose', 'neutral')",
            name="ck_debate_statements_stance",
        ),
        sa.CheckConstraint(
            "confidence_before >= 0 and confidence_before <= 1",
            name="ck_debate_statements_confidence_before",
        ),
        sa.CheckConstraint(
            "confidence_after >= 0 and confidence_after <= 1",
            name="ck_debate_statements_confidence_after",
        ),
        sa.UniqueConstraint(
            "debate_id",
            "agent_report_id",
            "hypothesis_id",
            name="uq_debate_statement_pair",
        ),
    )
    op.create_index(
        "ix_debate_statements_debate_id", "debate_statements", ["debate_id"]
    )
    op.create_table(
        "debate_statement_evidence",
        sa.Column("statement_id", sa.String(length=64), primary_key=True),
        sa.Column("evidence_id", sa.String(length=64), primary_key=True),
        sa.ForeignKeyConstraint(
            ["statement_id"], ["debate_statements.statement_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["evidence.evidence_id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "decision_proposals",
        sa.Column("proposal_id", sa.String(length=64), primary_key=True),
        sa.Column("debate_id", sa.String(length=64), nullable=False),
        sa.Column("conclusion", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("thesis", sa.String(), nullable=False),
        sa.Column("supporting_hypothesis_ids", JSONB(), nullable=False),
        sa.Column("rejected_hypothesis_ids", JSONB(), nullable=False),
        sa.Column("evidence_ids", JSONB(), nullable=False),
        sa.Column("risk_notes", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["debate_id"], ["debate_records.debate_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "conclusion in ('buy', 'sell', 'hold', 'watch', 'no_trade', 'invalid')",
            name="ck_decision_proposals_conclusion",
        ),
        sa.CheckConstraint(
            "confidence >= 0 and confidence <= 1",
            name="ck_decision_proposals_confidence",
        ),
        sa.UniqueConstraint("debate_id", name="uq_decision_proposals_debate_id"),
    )
    op.create_index(
        "ix_decision_proposals_debate_id", "decision_proposals", ["debate_id"]
    )
    op.create_table(
        "decision_proposal_hypotheses",
        sa.Column("proposal_id", sa.String(length=64), primary_key=True),
        sa.Column("hypothesis_id", sa.String(length=64), primary_key=True),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["decision_proposals.proposal_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["hypothesis_id"], ["hypotheses.hypothesis_id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "decision_proposal_evidence",
        sa.Column("proposal_id", sa.String(length=64), primary_key=True),
        sa.Column("evidence_id", sa.String(length=64), primary_key=True),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["decision_proposals.proposal_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["evidence.evidence_id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "risk_reviews",
        sa.Column("risk_review_id", sa.String(length=64), primary_key=True),
        sa.Column("proposal_id", sa.String(length=64), nullable=False),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column("final_conclusion", sa.String(length=32), nullable=False),
        sa.Column("final_confidence", sa.Float(), nullable=False),
        sa.Column("reasons", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["decision_proposals.proposal_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "verdict in ('approve', 'downgrade', 'veto')",
            name="ck_risk_reviews_verdict",
        ),
        sa.CheckConstraint(
            "final_conclusion in "
            "('buy', 'sell', 'hold', 'watch', 'no_trade', 'invalid')",
            name="ck_risk_reviews_final_conclusion",
        ),
        sa.CheckConstraint(
            "final_confidence >= 0 and final_confidence <= 1",
            name="ck_risk_reviews_final_confidence",
        ),
        sa.UniqueConstraint("proposal_id", name="uq_risk_reviews_proposal_id"),
    )
    op.create_table(
        "decision_assembly_records",
        sa.Column("assembly_id", sa.String(length=64), primary_key=True),
        sa.Column("research_session_id", sa.String(length=64), nullable=False),
        sa.Column("debate_id", sa.String(length=64), nullable=False),
        sa.Column("proposal_id", sa.String(length=64), nullable=False),
        sa.Column("risk_review_id", sa.String(length=64), nullable=False),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("conclusion", sa.String(length=32), nullable=False),
        sa.Column("report_ids", JSONB(), nullable=False),
        sa.Column("hypothesis_ids", JSONB(), nullable=False),
        sa.Column("evidence_ids", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["debate_id"], ["debate_records.debate_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["decision_proposals.proposal_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["risk_review_id"], ["risk_reviews.risk_review_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["decision_id"], ["decisions.decision_id"], ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "conclusion in ('buy', 'sell', 'hold', 'watch', 'no_trade', 'invalid')",
            name="ck_decision_assembly_conclusion",
        ),
        sa.UniqueConstraint("proposal_id", name="uq_decision_assembly_proposal_id"),
        sa.UniqueConstraint("debate_id", name="uq_decision_assembly_debate_id"),
        sa.UniqueConstraint("decision_id", name="uq_decision_assembly_decision_id"),
    )


def downgrade() -> None:
    op.drop_table("decision_assembly_records")
    op.drop_table("risk_reviews")
    op.drop_table("decision_proposal_evidence")
    op.drop_table("decision_proposal_hypotheses")
    op.drop_index("ix_decision_proposals_debate_id", table_name="decision_proposals")
    op.drop_table("decision_proposals")
    op.drop_table("debate_statement_evidence")
    op.drop_index("ix_debate_statements_debate_id", table_name="debate_statements")
    op.drop_table("debate_statements")
    op.drop_table("debate_record_hypotheses")
    op.drop_table("debate_record_reports")
    op.drop_index("ix_debate_records_research_session_id", table_name="debate_records")
    op.drop_table("debate_records")
