from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from aios.api.schemas.common import ApiSchema
from aios.api.schemas.decision import DecisionResponse, decision_response
from aios.api.schemas.learning import LearningResponse, learning_response
from aios.api.schemas.research import (
    DecisionEvaluationResponse,
    DecisionOutcomeResponse,
    SimulatedExecutionResponse,
    TradePlanResponse,
    decision_evaluation_response,
    decision_outcome_response,
    simulated_execution_response,
    trade_plan_response,
)
from aios.api.schemas.research_run import ResearchRunResponse, research_run_response
from aios.api.schemas.research_session import (
    ResearchSessionResponse,
    research_session_response,
)
from aios.api.schemas.review import ReviewResponse, review_response
from aios.application.explorer import (
    ExecutionListItem,
    ExplorerDetail,
    ExplorerPage,
    SettlementListItem,
)


class ExplorerListResponse[ItemT](ApiSchema):
    items: list[ItemT]
    total: int
    page: int
    page_size: int
    count: int


class ExecutionListItemResponse(ApiSchema):
    execution_id: str
    symbol: str
    market: str | None
    side: str
    action: str
    quantity: Decimal
    simulated_price: Decimal | None
    status: str
    created_at: datetime
    research_run_id: str | None
    research_session_id: str
    decision_id: str
    trade_plan_id: str
    settlement_id: str | None


class SettlementListItemResponse(ApiSchema):
    settlement_id: str
    execution_id: str | None
    trade_plan_id: str | None
    decision_id: str
    research_session_id: str | None
    research_run_id: str | None
    symbol: str
    market: str | None
    status: str
    entry_price: Decimal | None
    exit_price: Decimal | None
    return_rate: Decimal | None
    pnl: Decimal | None
    settled_at: datetime
    created_at: datetime


class ExplorerDetailResponse(ApiSchema):
    research_run: ResearchRunResponse | None
    research_session: ResearchSessionResponse | None
    decision: DecisionResponse | None
    trade_plan: TradePlanResponse | None
    simulated_execution: SimulatedExecutionResponse | None
    settlement: DecisionOutcomeResponse | None
    evaluation: DecisionEvaluationResponse | None
    review: ReviewResponse | None
    learning_proposals: list[LearningResponse]


def execution_list_response(
    page: ExplorerPage[ExecutionListItem],
) -> ExplorerListResponse[ExecutionListItemResponse]:
    return ExplorerListResponse(
        items=[execution_list_item_response(item) for item in page.items],
        total=page.total,
        page=page.page,
        page_size=page.page_size,
        count=len(page.items),
    )


def settlement_list_response(
    page: ExplorerPage[SettlementListItem],
) -> ExplorerListResponse[SettlementListItemResponse]:
    return ExplorerListResponse(
        items=[settlement_list_item_response(item) for item in page.items],
        total=page.total,
        page=page.page,
        page_size=page.page_size,
        count=len(page.items),
    )


def execution_list_item_response(
    item: ExecutionListItem,
) -> ExecutionListItemResponse:
    execution = item.execution
    return ExecutionListItemResponse(
        execution_id=execution.execution_id,
        symbol=execution.symbol,
        market=item.market,
        side=execution.direction.value,
        action=execution.direction.value,
        quantity=execution.position_size,
        simulated_price=execution.executed_entry,
        status=execution.execution_status.value,
        created_at=execution.created_at,
        research_run_id=item.research_run_id,
        research_session_id=execution.research_session_id,
        decision_id=execution.decision_id,
        trade_plan_id=execution.trade_plan_id,
        settlement_id=item.settlement_id,
    )


def settlement_list_item_response(
    item: SettlementListItem,
) -> SettlementListItemResponse:
    settlement = item.settlement
    return SettlementListItemResponse(
        settlement_id=settlement.outcome_id,
        execution_id=settlement.execution_id,
        trade_plan_id=settlement.trade_plan_id,
        decision_id=settlement.decision_id,
        research_session_id=settlement.research_session_id,
        research_run_id=item.research_run_id,
        symbol=settlement.symbol,
        market=item.market,
        status=settlement.status.value,
        entry_price=settlement.entry_price,
        exit_price=settlement.exit_price,
        return_rate=settlement.return_rate,
        pnl=settlement.pnl,
        settled_at=settlement.settled_at,
        created_at=settlement.created_at,
    )


def explorer_detail_response(detail: ExplorerDetail) -> ExplorerDetailResponse:
    return ExplorerDetailResponse(
        research_run=(
            research_run_response(detail.research_run) if detail.research_run else None
        ),
        research_session=(
            research_session_response(detail.research_session)
            if detail.research_session
            else None
        ),
        decision=decision_response(detail.decision) if detail.decision else None,
        trade_plan=trade_plan_response(detail.trade_plan)
        if detail.trade_plan
        else None,
        simulated_execution=simulated_execution_response(detail.simulated_execution)
        if detail.simulated_execution
        else None,
        settlement=decision_outcome_response(detail.settlement)
        if detail.settlement
        else None,
        evaluation=decision_evaluation_response(detail.evaluation)
        if detail.evaluation
        else None,
        review=review_response(detail.review) if detail.review else None,
        learning_proposals=[
            learning_response(learning) for learning in detail.learning_proposals
        ],
    )
