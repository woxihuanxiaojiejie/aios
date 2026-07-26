"""Allow Brain-native research assemblies without legacy Debate rows.

Revision ID: 0015_nullable_legacy_links
Revises: 0014_brain004_decision
Create Date: 2026-07-26 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_nullable_legacy_links"
down_revision: str | Sequence[str] | None = "0014_brain004_decision"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table_name in ("decision_assembly_records", "research_settlement_records"):
        for column_name in ("debate_id", "proposal_id", "risk_review_id"):
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.String(length=64),
                nullable=True,
            )


def downgrade() -> None:
    op.execute(
        "delete from research_settlement_records "
        "where debate_id is null or proposal_id is null or risk_review_id is null"
    )
    op.execute(
        "delete from decision_assembly_records "
        "where debate_id is null or proposal_id is null or risk_review_id is null"
    )
    for table_name in ("research_settlement_records", "decision_assembly_records"):
        for column_name in ("debate_id", "proposal_id", "risk_review_id"):
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.String(length=64),
                nullable=False,
            )
