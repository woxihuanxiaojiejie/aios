"""Add trade plans.

Revision ID: 0020_trade_plans
Revises: 0019_rich_formal_decisions
Create Date: 2026-07-27 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_trade_plans"
down_revision: str | Sequence[str] | None = "0019_rich_formal_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trade_plans",
        sa.Column("trade_plan_id", sa.String(length=64), nullable=False),
        sa.Column("decision_id", sa.String(length=64), nullable=False),
        sa.Column("research_session_id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("planned_entry", postgresql.JSONB(), nullable=False),
        sa.Column("entry_conditions", postgresql.JSONB(), nullable=False),
        sa.Column("target", postgresql.JSONB()),
        sa.Column("stop_loss", sa.Float()),
        sa.Column("invalidation_conditions", postgresql.JSONB(), nullable=False),
        sa.Column("planned_position", sa.Float()),
        sa.Column("horizon", sa.String(length=64), nullable=False),
        sa.Column("expiry", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fee_model", postgresql.JSONB(), nullable=False),
        sa.Column("slippage_model", postgresql.JSONB(), nullable=False),
        sa.Column("unavailable_fields", postgresql.JSONB(), nullable=False),
        sa.Column("no_trade_reasons", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('ready', 'no_trade', 'invalid', 'expired', 'cancelled')",
            name="ck_trade_plans_status",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_trade_plans_updated_at",
        ),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["decisions.decision_id"],
            name="fk_trade_plans_decision_id_decisions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("trade_plan_id"),
        sa.UniqueConstraint("decision_id", name="uq_trade_plans_decision_id"),
    )
    op.create_index("ix_trade_plans_decision_id", "trade_plans", ["decision_id"])
    op.create_index(
        "ix_trade_plans_research_session_id",
        "trade_plans",
        ["research_session_id"],
    )
    op.create_index("ix_trade_plans_symbol", "trade_plans", ["symbol"])
    op.create_index("ix_trade_plans_status", "trade_plans", ["status"])


def downgrade() -> None:
    op.drop_index("ix_trade_plans_status", table_name="trade_plans")
    op.drop_index("ix_trade_plans_symbol", table_name="trade_plans")
    op.drop_index("ix_trade_plans_research_session_id", table_name="trade_plans")
    op.drop_index("ix_trade_plans_decision_id", table_name="trade_plans")
    op.drop_table("trade_plans")
