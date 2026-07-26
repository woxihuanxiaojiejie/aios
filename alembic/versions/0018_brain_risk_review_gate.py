"""Add BRAIN-native RiskReview gate fields.

Revision ID: 0018_brain_risk_review_gate
Revises: 0017_research_lifecycle
Create Date: 2026-07-26 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_brain_risk_review_gate"
down_revision: str | Sequence[str] | None = "0017_research_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_VERDICT_CHECK = "verdict in ('approve', 'downgrade', 'veto')"
_NEW_VERDICT_CHECK = (
    "verdict in ('approve', 'reduce_confidence', 'reduce_position', "
    "'modify_conditions', 'downgrade', 'veto')"
)


def upgrade() -> None:
    op.drop_constraint("ck_risk_reviews_verdict", "risk_reviews", type_="check")
    op.create_check_constraint(
        "ck_risk_reviews_verdict",
        "risk_reviews",
        _NEW_VERDICT_CHECK,
    )
    op.alter_column(
        "risk_reviews",
        "proposal_id",
        existing_type=sa.String(length=64),
        nullable=True,
    )
    op.add_column("risk_reviews", sa.Column("confidence_delta", sa.Float()))
    op.add_column("risk_reviews", sa.Column("adjusted_position", sa.Float()))
    op.add_column(
        "risk_reviews",
        sa.Column(
            "condition_changes",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "risk_reviews",
        sa.Column(
            "converted_to_no_trade",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "risk_reviews",
        sa.Column("research_session_id", sa.String(length=64)),
    )
    op.add_column(
        "risk_reviews",
        sa.Column("decision_result_id", sa.String(length=64)),
    )
    op.add_column(
        "risk_reviews",
        sa.Column("discussion_result_id", sa.String(length=64)),
    )
    op.add_column(
        "risk_reviews",
        sa.Column(
            "skill_result_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "risk_reviews",
        sa.Column(
            "evidence_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "risk_reviews",
        sa.Column(
            "supporting_arguments",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "risk_reviews",
        sa.Column(
            "opposing_arguments",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_unique_constraint(
        "uq_risk_reviews_decision_result_id",
        "risk_reviews",
        ["decision_result_id"],
    )
    for column_name in (
        "condition_changes",
        "converted_to_no_trade",
        "skill_result_ids",
        "evidence_ids",
        "supporting_arguments",
        "opposing_arguments",
    ):
        op.alter_column("risk_reviews", column_name, server_default=None)


def downgrade() -> None:
    op.execute("delete from risk_reviews where proposal_id is null")
    op.drop_constraint(
        "uq_risk_reviews_decision_result_id",
        "risk_reviews",
        type_="unique",
    )
    for column_name in (
        "opposing_arguments",
        "supporting_arguments",
        "evidence_ids",
        "skill_result_ids",
        "discussion_result_id",
        "decision_result_id",
        "research_session_id",
        "converted_to_no_trade",
        "condition_changes",
        "adjusted_position",
        "confidence_delta",
    ):
        op.drop_column("risk_reviews", column_name)
    op.alter_column(
        "risk_reviews",
        "proposal_id",
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.drop_constraint("ck_risk_reviews_verdict", "risk_reviews", type_="check")
    op.create_check_constraint(
        "ck_risk_reviews_verdict",
        "risk_reviews",
        _OLD_VERDICT_CHECK,
    )
