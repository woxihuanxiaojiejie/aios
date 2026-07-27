"""Add simulated execution and MVP settlement fields.

Revision ID: 0021_sim_execution
Revises: 0020_trade_plans
Create Date: 2026-07-27 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_sim_execution"
down_revision: str | Sequence[str] | None = "0020_trade_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "simulated_executions",
        sa.Column("execution_id", sa.String(length=64), nullable=False),
        sa.Column("trade_plan_id", sa.String(length=64), nullable=False),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("research_session_id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.Column("execution_status", sa.String(length=32), nullable=False),
        sa.Column("execution_date", sa.DateTime(timezone=True)),
        sa.Column("market_bar_id", sa.String(length=255)),
        sa.Column("market_data_source", sa.String(length=255)),
        sa.Column("planned_entry", sa.String(length=255), nullable=False),
        sa.Column("executed_entry", sa.Numeric(24, 12)),
        sa.Column("executed_exit", sa.Numeric(24, 12)),
        sa.Column("position_size", sa.Numeric(24, 12), nullable=False),
        sa.Column("fee", sa.Numeric(24, 12), nullable=False),
        sa.Column("slippage", sa.Numeric(24, 12), nullable=False),
        sa.Column("realized_return", sa.Numeric(24, 12)),
        sa.Column("exit_reason", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "execution_status in ('waiting_settlement', 'not_filled')",
            name="ck_simulated_executions_status",
        ),
        sa.CheckConstraint(
            "exit_reason in ('target', 'stop', 'expiry', 'not_filled')",
            name="ck_simulated_executions_exit_reason",
        ),
        sa.CheckConstraint("position_size >= 0 and position_size <= 1"),
        sa.CheckConstraint("fee >= 0"),
        sa.CheckConstraint("slippage >= 0"),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_simulated_executions_updated_at",
        ),
        sa.ForeignKeyConstraint(
            ["trade_plan_id"],
            ["trade_plans.trade_plan_id"],
            name="fk_simulated_executions_trade_plan_id_trade_plans",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("execution_id"),
        sa.UniqueConstraint(
            "trade_plan_id",
            name="uq_simulated_executions_trade_plan_id",
        ),
    )
    op.create_index(
        "ix_simulated_executions_trade_plan_id",
        "simulated_executions",
        ["trade_plan_id"],
    )
    op.create_index(
        "ix_simulated_executions_decision_id",
        "simulated_executions",
        ["decision_id"],
    )
    op.create_index(
        "ix_simulated_executions_research_session_id",
        "simulated_executions",
        ["research_session_id"],
    )
    op.create_index(
        "ix_simulated_executions_symbol",
        "simulated_executions",
        ["symbol"],
    )
    op.create_index(
        "ix_simulated_executions_status",
        "simulated_executions",
        ["execution_status"],
    )

    op.add_column("decision_outcomes", sa.Column("execution_id", sa.String(64)))
    op.add_column("decision_outcomes", sa.Column("trade_plan_id", sa.String(64)))
    op.add_column("decision_outcomes", sa.Column("research_session_id", sa.String(64)))
    op.add_column("decision_outcomes", sa.Column("pnl", sa.Numeric(24, 12)))
    op.add_column("decision_outcomes", sa.Column("return_rate", sa.Numeric(24, 12)))
    op.add_column("decision_outcomes", sa.Column("holding_days", sa.Integer()))
    op.add_column("decision_outcomes", sa.Column("exit_reason", sa.String(32)))
    op.add_column("decision_outcomes", sa.Column("max_drawdown", sa.Numeric(24, 12)))

    op.add_column(
        "decision_evaluations",
        sa.Column("prediction_accuracy", sa.String(32)),
    )
    op.add_column("decision_evaluations", sa.Column("timing_accuracy", sa.String(32)))
    op.add_column("decision_evaluations", sa.Column("risk_control", sa.String(32)))
    op.add_column("decision_evaluations", sa.Column("execution_quality", sa.String(32)))

    op.add_column(
        "reviews",
        sa.Column(
            "success_reasons",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "reviews",
        sa.Column(
            "failure_reasons",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "reviews",
        sa.Column(
            "effective_evidence_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "reviews",
        sa.Column(
            "effective_skill_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "reviews",
        sa.Column(
            "mistaken_judgement_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "reviews",
        sa.Column(
            "reference_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
    )
    for column in (
        "success_reasons",
        "failure_reasons",
        "effective_evidence_ids",
        "effective_skill_ids",
        "mistaken_judgement_ids",
        "reference_ids",
    ):
        op.alter_column("reviews", column, server_default=None)


def downgrade() -> None:
    for column in (
        "reference_ids",
        "mistaken_judgement_ids",
        "effective_skill_ids",
        "effective_evidence_ids",
        "failure_reasons",
        "success_reasons",
    ):
        op.drop_column("reviews", column)
    for column in (
        "execution_quality",
        "risk_control",
        "timing_accuracy",
        "prediction_accuracy",
    ):
        op.drop_column("decision_evaluations", column)
    for column in (
        "max_drawdown",
        "exit_reason",
        "holding_days",
        "return_rate",
        "pnl",
        "research_session_id",
        "trade_plan_id",
        "execution_id",
    ):
        op.drop_column("decision_outcomes", column)
    op.drop_index("ix_simulated_executions_status", table_name="simulated_executions")
    op.drop_index("ix_simulated_executions_symbol", table_name="simulated_executions")
    op.drop_index(
        "ix_simulated_executions_research_session_id",
        table_name="simulated_executions",
    )
    op.drop_index(
        "ix_simulated_executions_decision_id",
        table_name="simulated_executions",
    )
    op.drop_index(
        "ix_simulated_executions_trade_plan_id",
        table_name="simulated_executions",
    )
    op.drop_table("simulated_executions")
