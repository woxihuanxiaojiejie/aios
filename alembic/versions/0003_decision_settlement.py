"""create decision settlement tables

Revision ID: 0003_decision_settlement
Revises: 0002_llm_generation_records
Create Date: 2026-07-19 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_decision_settlement"
down_revision: str | None = "0002_llm_generation_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_outcomes",
        sa.Column("outcome_id", sa.String(length=64), primary_key=True),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("experiment_id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("horizon", sa.String(length=64), nullable=False),
        sa.Column("horizon_semantics", sa.String(length=64), nullable=False),
        sa.Column("observation_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observation_ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entry_price", sa.Numeric(24, 12), nullable=True),
        sa.Column("exit_price", sa.Numeric(24, 12), nullable=True),
        sa.Column("realized_return", sa.Numeric(24, 12), nullable=True),
        sa.Column("maximum_adverse_excursion", sa.Numeric(24, 12), nullable=True),
        sa.Column("maximum_favorable_excursion", sa.Numeric(24, 12), nullable=True),
        sa.Column("market_data_source", sa.String(length=255), nullable=False),
        sa.Column(
            "market_data_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
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
        sa.UniqueConstraint("decision_id", name="uq_decision_outcomes_decision_id"),
    )
    op.create_index(
        "ix_decision_outcomes_experiment_id",
        "decision_outcomes",
        ["experiment_id"],
    )
    op.create_index(
        "ix_decision_outcomes_status",
        "decision_outcomes",
        ["status"],
    )

    op.create_table(
        "decision_evaluations",
        sa.Column("evaluation_id", sa.String(length=64), primary_key=True),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("outcome_id", sa.String(length=64), nullable=False),
        sa.Column("experiment_id", sa.String(length=64), nullable=False),
        sa.Column("directional_result", sa.String(length=64), nullable=False),
        sa.Column("return_result", sa.String(length=64), nullable=False),
        sa.Column("risk_result", sa.String(length=64), nullable=False),
        sa.Column("final_result", sa.String(length=64), nullable=False),
        sa.Column("evaluation_rules_version", sa.String(length=128), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("explanation", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["decisions.decision_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["outcome_id"],
            ["decision_outcomes.outcome_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["experiments.experiment_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "decision_id",
            "evaluation_rules_version",
            name="uq_decision_evaluations_decision_rules",
        ),
    )
    op.create_index(
        "ix_decision_evaluations_outcome_id",
        "decision_evaluations",
        ["outcome_id"],
    )
    op.create_index(
        "ix_decision_evaluations_final_result",
        "decision_evaluations",
        ["final_result"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_decision_evaluations_final_result",
        table_name="decision_evaluations",
    )
    op.drop_index(
        "ix_decision_evaluations_outcome_id",
        table_name="decision_evaluations",
    )
    op.drop_table("decision_evaluations")
    op.drop_index("ix_decision_outcomes_status", table_name="decision_outcomes")
    op.drop_index(
        "ix_decision_outcomes_experiment_id",
        table_name="decision_outcomes",
    )
    op.drop_table("decision_outcomes")
