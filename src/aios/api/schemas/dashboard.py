from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from aios.api.schemas.common import ApiSchema
from aios.application.dashboard import (
    AttentionRequiredItem,
    DashboardCounts,
    DashboardPerformance,
    DashboardSummary,
    RecentResearchItem,
    RecentSettlementItem,
)


class DashboardCountsResponse(ApiSchema):
    research_runs: int
    completed_research_runs: int
    failed_or_resumable_research_runs: int
    decisions: int
    trade_plans: int
    simulated_executions: int
    settlements: int
    pending_learning_proposals: int
    positive_settlements: int
    negative_settlements: int


class DashboardPerformanceResponse(ApiSchema):
    average_return: Decimal | None


class AttentionRequiredItemResponse(ApiSchema):
    type: str
    symbol: str | None
    market: str | None
    current_stage: str
    missing_stage: str
    created_at: datetime
    detail_path: str
    detail_id: str


class RecentResearchItemResponse(ApiSchema):
    run_id: str
    created_at: datetime
    symbol: str | None
    market: str | None
    research_status: str
    decision_action: str | None
    confidence: float | None
    trade_plan_status: str | None
    current_loop_stage: str


class RecentSettlementItemResponse(ApiSchema):
    settlement_id: str
    settled_at: datetime
    symbol: str
    market: str | None
    decision_action: str | None
    entry_price: Decimal | None
    exit_price: Decimal | None
    return_rate: Decimal | None
    pnl: Decimal | None
    evaluation_summary: str | None
    review_status: str | None


class DashboardSummaryResponse(ApiSchema):
    generated_at: datetime
    counts: DashboardCountsResponse
    performance: DashboardPerformanceResponse
    attention_required: list[AttentionRequiredItemResponse]
    recent_research: list[RecentResearchItemResponse]
    recent_settlements: list[RecentSettlementItemResponse]


def dashboard_summary_response(summary: DashboardSummary) -> DashboardSummaryResponse:
    return DashboardSummaryResponse(
        generated_at=summary.generated_at,
        counts=_counts(summary.counts),
        performance=_performance(summary.performance),
        attention_required=[_attention(item) for item in summary.attention_required],
        recent_research=[_recent_research(item) for item in summary.recent_research],
        recent_settlements=[
            _recent_settlement(item) for item in summary.recent_settlements
        ],
    )


def _counts(counts: DashboardCounts) -> DashboardCountsResponse:
    return DashboardCountsResponse(
        research_runs=counts.research_runs,
        completed_research_runs=counts.completed_research_runs,
        failed_or_resumable_research_runs=counts.failed_or_resumable_research_runs,
        decisions=counts.decisions,
        trade_plans=counts.trade_plans,
        simulated_executions=counts.simulated_executions,
        settlements=counts.settlements,
        pending_learning_proposals=counts.pending_learning_proposals,
        positive_settlements=counts.positive_settlements,
        negative_settlements=counts.negative_settlements,
    )


def _performance(performance: DashboardPerformance) -> DashboardPerformanceResponse:
    return DashboardPerformanceResponse(average_return=performance.average_return)


def _attention(item: AttentionRequiredItem) -> AttentionRequiredItemResponse:
    return AttentionRequiredItemResponse(
        type=item.type,
        symbol=item.symbol,
        market=item.market,
        current_stage=item.current_stage,
        missing_stage=item.missing_stage,
        created_at=item.created_at,
        detail_path=item.detail_path,
        detail_id=item.detail_id,
    )


def _recent_research(item: RecentResearchItem) -> RecentResearchItemResponse:
    return RecentResearchItemResponse(
        run_id=item.run_id,
        created_at=item.created_at,
        symbol=item.symbol,
        market=item.market,
        research_status=item.research_status,
        decision_action=item.decision_action,
        confidence=item.confidence,
        trade_plan_status=item.trade_plan_status,
        current_loop_stage=item.current_loop_stage,
    )


def _recent_settlement(item: RecentSettlementItem) -> RecentSettlementItemResponse:
    return RecentSettlementItemResponse(
        settlement_id=item.settlement_id,
        settled_at=item.settled_at,
        symbol=item.symbol,
        market=item.market,
        decision_action=item.decision_action,
        entry_price=item.entry_price,
        exit_price=item.exit_price,
        return_rate=item.return_rate,
        pnl=item.pnl,
        evaluation_summary=item.evaluation_summary,
        review_status=item.review_status,
    )
