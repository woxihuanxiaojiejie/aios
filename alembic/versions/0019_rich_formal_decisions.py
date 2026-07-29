"""Add rich BRAIN formal Decision fields.

Revision ID: 0019_rich_formal_decisions
Revises: 0018_brain_risk_review_gate
Create Date: 2026-07-27 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_rich_formal_decisions"
down_revision: str | Sequence[str] | None = "0018_brain_risk_review_gate"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "decisions",
        "expected_return",
        existing_type=sa.Float(),
        nullable=True,
    )
    op.alter_column(
        "decisions",
        "max_expected_loss",
        existing_type=sa.Float(),
        nullable=True,
    )
    op.add_column("decisions", sa.Column("research_session_id", sa.String(length=64)))
    op.add_column("decisions", sa.Column("decision_result_id", sa.String(length=64)))
    op.add_column("decisions", sa.Column("risk_review_id", sa.String(length=64)))
    op.add_column("decisions", sa.Column("direction", sa.String(length=32)))
    op.add_column("decisions", sa.Column("original_direction", sa.String(length=32)))
    op.add_column("decisions", sa.Column("target_range", postgresql.JSONB()))
    op.add_column(
        "decisions",
        sa.Column(
            "entry_conditions",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "decisions",
        sa.Column(
            "invalidation_conditions",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("decisions", sa.Column("stop_loss", sa.Float()))
    op.add_column("decisions", sa.Column("position_suggestion", sa.Float()))
    op.add_column(
        "decisions",
        sa.Column(
            "risk_factors",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "decisions",
        sa.Column(
            "supporting_skill_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "decisions",
        sa.Column(
            "dissenting_opinions",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("decisions", sa.Column("market_regime", sa.String(length=128)))
    op.add_column("decisions", sa.Column("generated_at", sa.DateTime(timezone=True)))
    op.add_column(
        "decisions",
        sa.Column("planned_settlement_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "decisions",
        sa.Column(
            "unavailable_fields",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "decisions",
        sa.Column(
            "downgrade_reasons",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_unique_constraint(
        "uq_decisions_decision_result_id",
        "decisions",
        ["decision_result_id"],
    )
    for column_name in (
        "entry_conditions",
        "invalidation_conditions",
        "risk_factors",
        "supporting_skill_ids",
        "dissenting_opinions",
        "unavailable_fields",
        "downgrade_reasons",
    ):
        op.alter_column("decisions", column_name, server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "uq_decisions_decision_result_id",
        "decisions",
        type_="unique",
    )
    for column_name in (
        "downgrade_reasons",
        "unavailable_fields",
        "planned_settlement_at",
        "generated_at",
        "market_regime",
        "dissenting_opinions",
        "supporting_skill_ids",
        "risk_factors",
        "position_suggestion",
        "stop_loss",
        "invalidation_conditions",
        "entry_conditions",
        "target_range",
        "original_direction",
        "direction",
        "risk_review_id",
        "decision_result_id",
        "research_session_id",
    ):
        op.drop_column("decisions", column_name)
    op.execute(
        "delete from research_settlement_records where decision_id in "
        "(select decision_id from decisions where expected_return is null "
        "or max_expected_loss is null)"
    )
    op.execute(
        "delete from decision_assembly_records where decision_id in "
        "(select decision_id from decisions where expected_return is null "
        "or max_expected_loss is null)"
    )
    op.execute(
        "delete from decisions where expected_return is null "
        "or max_expected_loss is null"
    )
    op.alter_column(
        "decisions",
        "max_expected_loss",
        existing_type=sa.Float(),
        nullable=False,
    )
    op.alter_column(
        "decisions",
        "expected_return",
        existing_type=sa.Float(),
        nullable=False,
    )
