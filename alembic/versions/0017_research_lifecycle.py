"""Add ResearchSession lifecycle framework fields.

Revision ID: 0017_research_lifecycle
Revises: 0016_core_evidence_fields
Create Date: 2026-07-26 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017_research_lifecycle"
down_revision: str | Sequence[str] | None = "0016_core_evidence_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_STATUS_CHECK = "status in ('created', 'evidence_ready', 'cancelled')"
_NEW_STATUS_CHECK = (
    "status in ("
    "'created', 'collecting_evidence', 'evidence_ready', "
    "'hypothesis_ready', 'skills_running', 'discussion_ready', "
    "'risk_review', 'decision_ready', 'trade_plan_ready', "
    "'waiting_execution', 'waiting_settlement', 'settled', "
    "'reviewed', 'learning_proposed', 'completed', 'failed', 'cancelled'"
    ")"
)


def upgrade() -> None:
    op.drop_constraint(
        "ck_research_sessions_status",
        "research_sessions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_research_sessions_status",
        "research_sessions",
        _NEW_STATUS_CHECK,
    )
    op.add_column(
        "research_sessions",
        sa.Column("failure_stage", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "research_sessions",
        sa.Column("failure_error", sa.String(), nullable=True),
    )
    op.add_column(
        "research_sessions",
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "research_sessions",
        sa.Column(
            "transition_log",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.alter_column("research_sessions", "retry_count", server_default=None)
    op.alter_column("research_sessions", "transition_log", server_default=None)


def downgrade() -> None:
    op.execute(
        "update research_sessions set status = 'created' "
        "where status not in ('created', 'evidence_ready', 'cancelled')"
    )
    op.drop_column("research_sessions", "transition_log")
    op.drop_column("research_sessions", "retry_count")
    op.drop_column("research_sessions", "failure_error")
    op.drop_column("research_sessions", "failure_stage")
    op.drop_constraint(
        "ck_research_sessions_status",
        "research_sessions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_research_sessions_status",
        "research_sessions",
        _OLD_STATUS_CHECK,
    )
