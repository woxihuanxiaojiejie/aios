from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator

from aios.api.schemas.common import ApiSchema, require_timezone
from aios.api.schemas.debate import (
    DebateResponse,
    DebateStatementResponse,
    DecisionAssemblyResponse,
    DecisionProposalResponse,
    RiskReviewResponse,
)
from aios.api.schemas.decision import DecisionResponse
from aios.api.schemas.decision_generation import GenerationMetadataResponse
from aios.api.schemas.evidence import EvidenceResponse
from aios.api.schemas.experiment import ExperimentResponse
from aios.api.schemas.learning import LearningResponse, learning_response
from aios.api.schemas.market_data import MarketBarResponse
from aios.api.schemas.research_records import AgentReportResponse, HypothesisResponse
from aios.api.schemas.research_run import ResearchRunResponse
from aios.api.schemas.research_session import ResearchSessionResponse
from aios.api.schemas.review import ReviewResponse
from aios.api.schemas.watchlist import WatchlistItemResponse
from aios.kernel.enums import (
    DecisionDirection,
    DirectionalResult,
    EvaluationFinalResult,
    EvaluationScore,
    ExecutionExitReason,
    ExecutionStatus,
    OutcomeStatus,
    ReturnResult,
    RiskResult,
    TradePlanStatus,
)
from aios.kernel.execution import SimulatedExecution
from aios.kernel.learning import Learning
from aios.kernel.settlement import (
    DecisionEvaluation,
    DecisionOutcome,
    ResearchSettlementRecord,
)
from aios.kernel.trade_plan import TradePlan


class ResearchMarketResponse(ApiSchema):
    symbol: str
    market: str
    source: str
    data_source: str
    latest: MarketBarResponse
    bars: list[MarketBarResponse]
    change: Decimal | None
    change_percent: Decimal | None
    observed_at: datetime
    available_at: datetime


class ResearchEvidenceRequest(ApiSchema):
    symbol: str = Field(min_length=1)
    days: int = Field(default=90, ge=1, le=180)


class ResearchEvidenceResponse(ApiSchema):
    symbol: str
    requested: int
    created: int
    existing: int
    evidence_ids: list[str]
    latest_evidence: EvidenceResponse | None


class ResearchExperimentRequest(ApiSchema):
    symbol: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    model: str | None = Field(default=None, min_length=1)


class ResearchDecisionRequest(ApiSchema):
    experiment_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    horizon: str = Field(default="1d", min_length=1)


class ResearchDecisionResponse(ApiSchema):
    decision: DecisionResponse
    generation: GenerationMetadataResponse


class ResearchSettlementRequest(ApiSchema):
    as_of: datetime | None = None

    @field_validator("as_of")
    @classmethod
    def validate_as_of(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return require_timezone(value)


class TradePlanResponse(ApiSchema):
    trade_plan_id: str
    decision_id: str
    research_session_id: str
    symbol: str
    direction: DecisionDirection
    status: TradePlanStatus
    planned_entry: tuple[str, ...]
    entry_conditions: tuple[str, ...]
    target: tuple[float, float] | None
    stop_loss: float | None
    invalidation_conditions: tuple[str, ...]
    planned_position: float | None
    horizon: str
    expiry: datetime
    fee_model: dict[str, object]
    slippage_model: dict[str, object]
    unavailable_fields: tuple[str, ...]
    no_trade_reasons: tuple[str, ...]
    created_at: datetime
    updated_at: datetime


class SimulatedExecutionResponse(ApiSchema):
    execution_id: str
    trade_plan_id: str
    decision_id: str
    research_session_id: str
    symbol: str
    direction: DecisionDirection
    execution_status: ExecutionStatus
    execution_date: datetime | None
    market_bar_id: str | None
    market_data_source: str | None
    planned_entry: str
    executed_entry: Decimal | None
    executed_exit: Decimal | None
    position_size: Decimal
    fee: Decimal
    slippage: Decimal
    realized_return: Decimal | None
    exit_reason: ExecutionExitReason
    created_at: datetime
    updated_at: datetime


class DecisionOutcomeResponse(ApiSchema):
    outcome_id: str
    decision_id: str
    experiment_id: str
    symbol: str
    horizon: str
    horizon_semantics: str
    observation_started_at: datetime
    observation_ended_at: datetime
    entry_price: Decimal | None
    exit_price: Decimal | None
    realized_return: Decimal | None
    maximum_adverse_excursion: Decimal | None
    maximum_favorable_excursion: Decimal | None
    market_data_source: str
    settled_at: datetime
    status: OutcomeStatus
    execution_id: str | None = None
    trade_plan_id: str | None = None
    research_session_id: str | None = None
    pnl: Decimal | None = None
    return_rate: Decimal | None = None
    holding_days: int | None = None
    exit_reason: ExecutionExitReason | None = None
    max_drawdown: Decimal | None = None
    max_favorable_excursion: Decimal | None = None
    created_at: datetime


class DecisionEvaluationResponse(ApiSchema):
    evaluation_id: str
    decision_id: str
    outcome_id: str
    experiment_id: str
    directional_result: DirectionalResult
    return_result: ReturnResult
    risk_result: RiskResult
    final_result: EvaluationFinalResult
    evaluation_rules_version: str
    evaluated_at: datetime
    explanation: str
    prediction_accuracy: EvaluationScore | None = None
    timing_accuracy: EvaluationScore | None = None
    risk_control: EvaluationScore | None = None
    execution_quality: EvaluationScore | None = None
    created_at: datetime


class ResearchSettlementResponse(ApiSchema):
    outcome: DecisionOutcomeResponse
    evaluation: DecisionEvaluationResponse
    review: ReviewResponse
    learning_proposal: LearningResponse | None = None


class RuntimeResearchResponse(ApiSchema):
    run: ResearchRunResponse
    trade_plan: TradePlanResponse | None = None
    simulated_execution: SimulatedExecutionResponse | None = None


class ResearchRunListItemResponse(ResearchRunResponse):
    market: str | None = None
    trigger_method: str | None = None
    final_decision: str | None = None
    confidence: float | None = None


class ResearchRunListResponse(ApiSchema):
    items: list[ResearchRunListItemResponse]
    total: int
    limit: int
    offset: int
    count: int


class ResearchRunDiscussionResponse(ApiSchema):
    debates: list[DebateResponse]
    statements: list[DebateStatementResponse]
    proposal: DecisionProposalResponse | None = None
    risk_review: RiskReviewResponse | None = None
    assembly: DecisionAssemblyResponse | None = None


class ResearchRunDetailResponse(ApiSchema):
    run: ResearchRunResponse
    watchlist_item: WatchlistItemResponse | None = None
    session: ResearchSessionResponse | None = None
    evidence: list[EvidenceResponse]
    skill_reports: list[AgentReportResponse]
    hypotheses: list[HypothesisResponse]
    discussion: ResearchRunDiscussionResponse
    decision: DecisionResponse | None = None
    trade_plan: TradePlanResponse | None = None


class SchedulerErrorResponse(ApiSchema):
    id: str
    error_type: str
    error_message: str


class ResearchSchedulerRunOnceResponse(ApiSchema):
    runs: list[ResearchRunResponse]
    errors: list[SchedulerErrorResponse]


class SettlementSchedulerRunOnceResponse(ApiSchema):
    settled: int
    errors: list[SchedulerErrorResponse]


class ResearchSettlementRecordResponse(ApiSchema):
    research_settlement_id: str
    assembly_id: str
    research_session_id: str
    debate_id: str | None
    proposal_id: str | None
    risk_review_id: str | None
    decision_id: str
    outcome_id: str
    evaluation_id: str
    review_id: str
    learning_ids: list[str]
    evidence_ids: list[str]
    report_ids: list[str]
    hypothesis_ids: list[str]
    settled_at: datetime
    created_at: datetime


class ResearchAssemblySettlementResponse(ApiSchema):
    record: ResearchSettlementRecordResponse
    outcome: DecisionOutcomeResponse
    evaluation: DecisionEvaluationResponse
    review: ReviewResponse
    learnings: list[LearningResponse]


class ResearchHistoryRow(ApiSchema):
    time: datetime
    type: str
    decision_id: str | None = None
    direction: str | None = None
    confidence: float | None = None
    realized_return: Decimal | None = None
    review_outcome: str | None = None
    status: str


class ResearchHistoryResponse(ApiSchema):
    symbol: str
    latest_evidence: EvidenceResponse | None
    latest_experiment: ExperimentResponse | None
    latest_decision: DecisionResponse | None
    latest_outcome: DecisionOutcomeResponse | None
    latest_evaluation: DecisionEvaluationResponse | None
    latest_review: ReviewResponse | None
    rows: list[ResearchHistoryRow]


def decision_outcome_response(outcome: DecisionOutcome) -> DecisionOutcomeResponse:
    payload = outcome.model_dump(exclude={"market_data_snapshot"})
    payload["max_favorable_excursion"] = outcome.max_favorable_excursion
    return DecisionOutcomeResponse.model_validate(payload)


def trade_plan_response(plan: TradePlan) -> TradePlanResponse:
    return TradePlanResponse.model_validate(plan.model_dump())


def simulated_execution_response(
    execution: SimulatedExecution,
) -> SimulatedExecutionResponse:
    payload = execution.model_dump()
    if execution.execution_date is not None:
        payload["execution_date"] = datetime.combine(
            execution.execution_date,
            datetime.min.time(),
        ).replace(tzinfo=execution.created_at.tzinfo)
    return SimulatedExecutionResponse.model_validate(payload)


def decision_evaluation_response(
    evaluation: DecisionEvaluation,
) -> DecisionEvaluationResponse:
    return DecisionEvaluationResponse.model_validate(evaluation.model_dump())


def research_settlement_record_response(
    record: ResearchSettlementRecord,
) -> ResearchSettlementRecordResponse:
    return ResearchSettlementRecordResponse(
        research_settlement_id=record.research_settlement_id,
        assembly_id=record.assembly_id,
        research_session_id=record.research_session_id,
        debate_id=record.debate_id,
        proposal_id=record.proposal_id,
        risk_review_id=record.risk_review_id,
        decision_id=record.decision_id,
        outcome_id=record.outcome_id,
        evaluation_id=record.evaluation_id,
        review_id=record.review_id,
        learning_ids=list(record.learning_ids),
        evidence_ids=list(record.evidence_ids),
        report_ids=list(record.report_ids),
        hypothesis_ids=list(record.hypothesis_ids),
        settled_at=record.settled_at,
        created_at=record.created_at,
    )


def research_assembly_settlement_response(
    *,
    record: ResearchSettlementRecord,
    outcome: DecisionOutcome,
    evaluation: DecisionEvaluation,
    review: ReviewResponse,
    learnings: tuple[Learning, ...],
) -> ResearchAssemblySettlementResponse:
    return ResearchAssemblySettlementResponse(
        record=research_settlement_record_response(record),
        outcome=decision_outcome_response(outcome),
        evaluation=decision_evaluation_response(evaluation),
        review=review,
        learnings=[learning_response(learning) for learning in learnings],
    )
