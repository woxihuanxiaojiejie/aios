from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from aios.api.schemas.brain002 import (
    AnalysisTaskResponse,
    SkillExecutionResponse,
    SkillResultResponse,
    analysis_task_response,
    skill_execution_response,
    skill_result_response,
)
from aios.api.schemas.brain003 import (
    DiscussionResultResponse,
    discussion_result_response,
)
from aios.api.schemas.brain004 import DecisionResultResponse, decision_result_response
from aios.api.schemas.common import ApiSchema
from aios.api.schemas.decision import DecisionResponse, decision_response
from aios.api.schemas.learning import LearningResponse, learning_response
from aios.api.schemas.research import (
    DecisionEvaluationResponse,
    DecisionOutcomeResponse,
    SimulatedExecutionResponse,
    decision_evaluation_response,
    decision_outcome_response,
    simulated_execution_response,
)
from aios.api.schemas.research_run import ResearchRunResponse, research_run_response
from aios.api.schemas.research_session import (
    ResearchSessionResponse,
    research_session_response,
)
from aios.api.schemas.review import ReviewResponse, review_response
from aios.application.business_views import (
    BusinessPage,
    DecisionSummary,
    LearningDetail,
    ReviewSummary,
)


class BusinessListResponse[ItemT](ApiSchema):
    items: list[ItemT]
    total: int
    page: int
    page_size: int
    count: int


class BrainResearchRecordsResponse(ApiSchema):
    analysis_task: AnalysisTaskResponse | None = None
    skill_executions: list[SkillExecutionResponse] = Field(default_factory=list)
    skill_results: list[SkillResultResponse] = Field(default_factory=list)
    discussion_result: DiscussionResultResponse | None = None
    decision_result: DecisionResultResponse | None = None


class DecisionSummaryResponse(ApiSchema):
    decision_id: str
    research_run_id: str | None
    stock_name: str | None
    symbol: str
    market: str | None
    decided_at: datetime
    research_horizon: str | None
    action: str
    confidence: float
    decision_summary: str
    core_reason: str
    risks: list[str]
    invalidation_conditions: list[str]
    trade_plan_status: str | None
    simulated_execution_status: str | None


class ReviewSummaryResponse(ApiSchema):
    settlement_id: str
    research_run_id: str | None
    stock_name: str | None
    symbol: str
    market: str | None
    original_decision: str | None
    research_horizon: str | None
    execution_time: date | None
    entry_price: Decimal | None
    exit_price: Decimal | None
    return_rate: Decimal | None
    pnl: Decimal | None
    directional_result: str | None
    return_result: str | None
    risk_result: str | None
    main_error: str | None
    learning_proposal_status: str | None


class LearningDetailResponse(ApiSchema):
    learning: LearningResponse
    review: ReviewResponse | None
    evaluation: DecisionEvaluationResponse | None
    settlement: DecisionOutcomeResponse | None
    simulated_execution: SimulatedExecutionResponse | None
    decision: DecisionResponse | None
    research_run: ResearchRunResponse | None
    research_session: ResearchSessionResponse | None
    current_value_summary: str
    proposed_value_summary: str
    change_summary: str
    technical_details: dict[str, Any]


def brain_records_payload(records: object) -> dict[str, object]:
    return {
        "analysis_task": (
            analysis_task_response(records.analysis_task)  # type: ignore[attr-defined]
            if records.analysis_task  # type: ignore[attr-defined]
            else None
        ),
        "skill_executions": [
            skill_execution_response(item)
            for item in records.skill_executions  # type: ignore[attr-defined]
        ],
        "skill_results": [
            skill_result_response(item)
            for item in records.skill_results  # type: ignore[attr-defined]
        ],
        "discussion_result": (
            discussion_result_response(records.discussion_result)  # type: ignore[attr-defined]
            if records.discussion_result  # type: ignore[attr-defined]
            else None
        ),
        "decision_result": (
            decision_result_response(records.decision_result)  # type: ignore[attr-defined]
            if records.decision_result  # type: ignore[attr-defined]
            else None
        ),
    }


def decision_summary_list_response(
    page: BusinessPage[DecisionSummary],
) -> BusinessListResponse[DecisionSummaryResponse]:
    return BusinessListResponse(
        items=[decision_summary_response(item) for item in page.items],
        total=page.total,
        page=page.page,
        page_size=page.page_size,
        count=len(page.items),
    )


def review_summary_list_response(
    page: BusinessPage[ReviewSummary],
) -> BusinessListResponse[ReviewSummaryResponse]:
    return BusinessListResponse(
        items=[review_summary_response(item) for item in page.items],
        total=page.total,
        page=page.page,
        page_size=page.page_size,
        count=len(page.items),
    )


def decision_summary_response(row: DecisionSummary) -> DecisionSummaryResponse:
    decision = row.decision
    market = row.research_session.scope.market if row.research_session else None
    horizon = (
        f"{row.research_session.scope.horizon_days}d"
        if row.research_session
        else decision.horizon
    )
    return DecisionSummaryResponse(
        decision_id=decision.decision_id,
        research_run_id=row.research_run.run_id if row.research_run else None,
        stock_name=None,
        symbol=decision.symbol,
        market=market,
        decided_at=decision.created_at,
        research_horizon=horizon,
        action=decision.action.value,
        confidence=decision.confidence,
        decision_summary=decision.reasoning_summary,
        core_reason=decision.reasoning_summary,
        risks=list(decision.risk_factors),
        invalidation_conditions=list(decision.invalidation_conditions),
        trade_plan_status=row.trade_plan.status.value if row.trade_plan else None,
        simulated_execution_status=(
            row.simulated_execution.execution_status.value
            if row.simulated_execution
            else None
        ),
    )


def review_summary_response(row: ReviewSummary) -> ReviewSummaryResponse:
    settlement = row.settlement
    return ReviewSummaryResponse(
        settlement_id=settlement.outcome_id,
        research_run_id=row.research_run.run_id if row.research_run else None,
        stock_name=None,
        symbol=settlement.symbol,
        market=row.research_session.scope.market if row.research_session else None,
        original_decision=row.decision.action.value if row.decision else None,
        research_horizon=(
            row.trade_plan.horizon if row.trade_plan else settlement.horizon
        ),
        execution_time=(
            row.simulated_execution.execution_date if row.simulated_execution else None
        ),
        entry_price=settlement.entry_price,
        exit_price=settlement.exit_price,
        return_rate=settlement.return_rate,
        pnl=settlement.pnl,
        directional_result=(
            row.evaluation.directional_result.value if row.evaluation else None
        ),
        return_result=row.evaluation.return_result.value if row.evaluation else None,
        risk_result=row.evaluation.risk_result.value if row.evaluation else None,
        main_error=(
            row.review.failure_reasons[0]
            if row.review and row.review.failure_reasons
            else None
        ),
        learning_proposal_status=(
            row.learning_proposals[0].approval_status.value
            if row.learning_proposals
            else None
        ),
    )


def learning_detail_response(detail: LearningDetail) -> LearningDetailResponse:
    return LearningDetailResponse(
        learning=learning_response(detail.learning),
        review=review_response(detail.review) if detail.review else None,
        evaluation=(
            decision_evaluation_response(detail.evaluation)
            if detail.evaluation
            else None
        ),
        settlement=(
            decision_outcome_response(detail.settlement) if detail.settlement else None
        ),
        simulated_execution=(
            simulated_execution_response(detail.simulated_execution)
            if detail.simulated_execution
            else None
        ),
        decision=decision_response(detail.decision) if detail.decision else None,
        research_run=(
            research_run_response(detail.research_run) if detail.research_run else None
        ),
        research_session=(
            research_session_response(detail.research_session)
            if detail.research_session
            else None
        ),
        current_value_summary=detail.current_value_summary,
        proposed_value_summary=detail.proposed_value_summary,
        change_summary=detail.change_summary,
        technical_details=detail.technical_details,
    )
