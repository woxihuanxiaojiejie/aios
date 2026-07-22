from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Query, status

from aios.adapters.market_data import Adjustment
from aios.api.dependencies import (
    BaoStockMarketDataAdapterDep,
    GenerationRecorderDep,
    LifecycleDep,
    LLMAdapterDep,
    MarketDataAdapterDep,
    VibeTradingAdapterDep,
)
from aios.api.schemas.common import ListResponse, page
from aios.api.schemas.debate import (
    DebateResponse,
    DebateStatementCreateRequest,
    DebateStatementResponse,
    DecisionAssemblyResponse,
    DecisionProposalCreateRequest,
    DecisionProposalResponse,
    RiskReviewCreateRequest,
    RiskReviewResponse,
    debate_response,
    debate_statement_response,
    decision_assembly_response,
    decision_proposal_response,
    risk_review_response,
)
from aios.api.schemas.decision import decision_response
from aios.api.schemas.decision_generation import generation_metadata_response
from aios.api.schemas.evidence import evidence_response
from aios.api.schemas.experiment import ExperimentResponse, experiment_response
from aios.api.schemas.market_data import market_bar_response
from aios.api.schemas.research import (
    ResearchAssemblySettlementResponse,
    ResearchDecisionRequest,
    ResearchDecisionResponse,
    ResearchEvidenceRequest,
    ResearchEvidenceResponse,
    ResearchExperimentRequest,
    ResearchHistoryResponse,
    ResearchHistoryRow,
    ResearchMarketResponse,
    ResearchSettlementRequest,
    ResearchSettlementResponse,
    decision_evaluation_response,
    decision_outcome_response,
    research_assembly_settlement_response,
)
from aios.api.schemas.research_records import (
    AgentReportCreateRequest,
    AgentReportResponse,
    HypothesisCreateRequest,
    HypothesisResponse,
    HypothesisStatusUpdateRequest,
    agent_report_response,
    hypothesis_response,
)
from aios.api.schemas.research_run import (
    ResearchRunCreateRequest,
    ResearchRunResponse,
    research_run_response,
)
from aios.api.schemas.research_session import (
    ResearchSessionCreateRequest,
    ResearchSessionResponse,
    research_session_response,
)
from aios.api.schemas.review import review_response
from aios.api.schemas.watchlist import (
    WatchlistCreateRequest,
    WatchlistItemResponse,
    WatchlistUpdateRequest,
    watchlist_item_response,
)
from aios.application.debate import DebateService
from aios.application.decision_generation import DecisionGenerationService
from aios.application.decision_settlement import DecisionSettlementService
from aios.application.market_evidence import MarketEvidenceImportService
from aios.application.research_records import ResearchRecordService
from aios.application.research_runner import ResearchRunner
from aios.application.research_session import ResearchSessionService
from aios.application.research_settlement import ResearchSettlementService
from aios.application.watchlist import WatchlistService
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    AgentReportStatus,
    AgentRole,
    HypothesisStatus,
    ResearchSessionStatus,
    WatchlistStatus,
)
from aios.kernel.errors import EvaluationConfigurationError
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.research_run import ResearchRun
from aios.kernel.review import Review
from aios.kernel.settlement import DecisionOutcome

router = APIRouter(prefix="/research", tags=["research"])

WATCHLIST_STATUS_QUERY = Query(default=WatchlistStatus.ACTIVE, alias="status")
WATCHLIST_MARKET_QUERY = Query(default=None, min_length=1)
WATCHLIST_SYMBOL_QUERY = Query(default=None, min_length=1)
SESSION_STATUS_QUERY = Query(default=None, alias="status")
SESSION_MARKET_QUERY = Query(default=None, min_length=1)
SESSION_SYMBOL_QUERY = Query(default=None, min_length=1)
REPORT_STATUS_QUERY = Query(default=None, alias="status")
REPORT_ROLE_QUERY = Query(default=None)
HYPOTHESIS_STATUS_QUERY = Query(default=None, alias="status")


@router.post(
    "/runs",
    response_model=ResearchRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_research(
    request: ResearchRunCreateRequest,
    lifecycle: LifecycleDep,
    adapter: MarketDataAdapterDep,
    vibe_adapter: VibeTradingAdapterDep,
) -> ResearchRunResponse:
    run = ResearchRunner(
        lifecycle=lifecycle,
        market_data_adapter=adapter,
        vibe_trading_adapter=vibe_adapter,
    ).run_research(**request.model_dump())
    return research_run_response(run)


@router.get("/runs/{run_id}", response_model=ResearchRunResponse)
def get_research_run(
    run_id: str,
    lifecycle: LifecycleDep,
) -> ResearchRunResponse:
    run = lifecycle.storage.get(ResearchRun, run_id)
    return research_run_response(run)


@router.post("/runs/{run_id}/resume", response_model=ResearchRunResponse)
def resume_research_run(
    run_id: str,
    lifecycle: LifecycleDep,
    adapter: MarketDataAdapterDep,
    vibe_adapter: VibeTradingAdapterDep,
) -> ResearchRunResponse:
    run = ResearchRunner(
        lifecycle=lifecycle,
        market_data_adapter=adapter,
        vibe_trading_adapter=vibe_adapter,
    ).resume_research(run_id)
    return research_run_response(run)


@router.post(
    "/watchlist",
    response_model=WatchlistItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_watchlist_item(
    request: WatchlistCreateRequest,
    lifecycle: LifecycleDep,
) -> WatchlistItemResponse:
    item = WatchlistService(lifecycle.storage).add_item(**request.model_dump())
    return watchlist_item_response(item)


@router.get("/watchlist", response_model=ListResponse[WatchlistItemResponse])
def list_watchlist_items(
    lifecycle: LifecycleDep,
    status_filter: WatchlistStatus | None = WATCHLIST_STATUS_QUERY,
    market: str | None = WATCHLIST_MARKET_QUERY,
    symbol: str | None = WATCHLIST_SYMBOL_QUERY,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ListResponse[WatchlistItemResponse]:
    items = [
        watchlist_item_response(item)
        for item in WatchlistService(lifecycle.storage).list_items(
            status=status_filter,
            market=market,
            symbol=symbol,
        )
    ]
    return page(items, limit, offset)


@router.get("/watchlist/{item_id}", response_model=WatchlistItemResponse)
def get_watchlist_item(
    item_id: str,
    lifecycle: LifecycleDep,
) -> WatchlistItemResponse:
    item = WatchlistService(lifecycle.storage).get_item(item_id)
    return watchlist_item_response(item)


@router.patch("/watchlist/{item_id}", response_model=WatchlistItemResponse)
def update_watchlist_item(
    item_id: str,
    request: WatchlistUpdateRequest,
    lifecycle: LifecycleDep,
) -> WatchlistItemResponse:
    item = WatchlistService(lifecycle.storage).update_note(
        item_id,
        note=request.note,
    )
    return watchlist_item_response(item)


@router.post("/watchlist/{item_id}/archive", response_model=WatchlistItemResponse)
def archive_watchlist_item(
    item_id: str,
    lifecycle: LifecycleDep,
) -> WatchlistItemResponse:
    item = WatchlistService(lifecycle.storage).archive_item(item_id)
    return watchlist_item_response(item)


@router.post("/watchlist/{item_id}/restore", response_model=WatchlistItemResponse)
def restore_watchlist_item(
    item_id: str,
    lifecycle: LifecycleDep,
) -> WatchlistItemResponse:
    item = WatchlistService(lifecycle.storage).restore_item(item_id)
    return watchlist_item_response(item)


@router.post(
    "/sessions",
    response_model=ResearchSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_research_session(
    request: ResearchSessionCreateRequest,
    lifecycle: LifecycleDep,
) -> ResearchSessionResponse:
    session = ResearchSessionService(lifecycle.storage).create_session(
        **request.model_dump()
    )
    return research_session_response(session)


@router.get("/sessions", response_model=ListResponse[ResearchSessionResponse])
def list_research_sessions(
    lifecycle: LifecycleDep,
    watchlist_item_id: str | None = Query(default=None, min_length=1),
    status_filter: ResearchSessionStatus | None = SESSION_STATUS_QUERY,
    market: str | None = SESSION_MARKET_QUERY,
    symbol: str | None = SESSION_SYMBOL_QUERY,
    horizon_days: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ListResponse[ResearchSessionResponse]:
    sessions = [
        research_session_response(session)
        for session in ResearchSessionService(lifecycle.storage).list_sessions(
            watchlist_item_id=watchlist_item_id,
            symbol=symbol,
            market=market,
            status=status_filter,
            horizon_days=horizon_days,
        )
    ]
    return page(sessions, limit, offset)


@router.get("/sessions/{session_id}", response_model=ResearchSessionResponse)
def get_research_session(
    session_id: str,
    lifecycle: LifecycleDep,
) -> ResearchSessionResponse:
    session = ResearchSessionService(lifecycle.storage).get_session(session_id)
    return research_session_response(session)


@router.post("/sessions/{session_id}/cancel", response_model=ResearchSessionResponse)
def cancel_research_session(
    session_id: str,
    lifecycle: LifecycleDep,
) -> ResearchSessionResponse:
    session = ResearchSessionService(lifecycle.storage).cancel_session(session_id)
    return research_session_response(session)


@router.post(
    "/sessions/{session_id}/agent-reports",
    response_model=AgentReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent_report(
    session_id: str,
    request: AgentReportCreateRequest,
    lifecycle: LifecycleDep,
) -> AgentReportResponse:
    report = ResearchRecordService(lifecycle.storage).create_agent_report(
        research_session_id=session_id,
        **request.model_dump(),
    )
    return agent_report_response(report)


@router.get(
    "/sessions/{session_id}/agent-reports",
    response_model=ListResponse[AgentReportResponse],
)
def list_agent_reports(
    session_id: str,
    lifecycle: LifecycleDep,
    role: AgentRole | None = REPORT_ROLE_QUERY,
    status_filter: AgentReportStatus | None = REPORT_STATUS_QUERY,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ListResponse[AgentReportResponse]:
    reports = [
        agent_report_response(report)
        for report in ResearchRecordService(lifecycle.storage).list_agent_reports(
            research_session_id=session_id,
            role=role,
            status=status_filter,
        )
    ]
    return page(reports, limit, offset)


@router.get("/agent-reports/{report_id}", response_model=AgentReportResponse)
def get_agent_report(
    report_id: str,
    lifecycle: LifecycleDep,
) -> AgentReportResponse:
    report = ResearchRecordService(lifecycle.storage).get_agent_report(report_id)
    return agent_report_response(report)


@router.post("/agent-reports/{report_id}/archive", response_model=AgentReportResponse)
def archive_agent_report(
    report_id: str,
    lifecycle: LifecycleDep,
) -> AgentReportResponse:
    report = ResearchRecordService(lifecycle.storage).archive_agent_report(report_id)
    return agent_report_response(report)


@router.post(
    "/sessions/{session_id}/hypotheses",
    response_model=HypothesisResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_hypothesis(
    session_id: str,
    request: HypothesisCreateRequest,
    lifecycle: LifecycleDep,
) -> HypothesisResponse:
    hypothesis = ResearchRecordService(lifecycle.storage).create_hypothesis(
        research_session_id=session_id,
        **request.model_dump(),
    )
    return hypothesis_response(hypothesis)


@router.get(
    "/sessions/{session_id}/hypotheses",
    response_model=ListResponse[HypothesisResponse],
)
def list_hypotheses(
    session_id: str,
    lifecycle: LifecycleDep,
    status_filter: HypothesisStatus | None = HYPOTHESIS_STATUS_QUERY,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ListResponse[HypothesisResponse]:
    hypotheses = [
        hypothesis_response(hypothesis)
        for hypothesis in ResearchRecordService(lifecycle.storage).list_hypotheses(
            research_session_id=session_id,
            status=status_filter,
        )
    ]
    return page(hypotheses, limit, offset)


@router.get("/hypotheses/{hypothesis_id}", response_model=HypothesisResponse)
def get_hypothesis(
    hypothesis_id: str,
    lifecycle: LifecycleDep,
) -> HypothesisResponse:
    hypothesis = ResearchRecordService(lifecycle.storage).get_hypothesis(hypothesis_id)
    return hypothesis_response(hypothesis)


@router.post("/hypotheses/{hypothesis_id}/status", response_model=HypothesisResponse)
def update_hypothesis_status(
    hypothesis_id: str,
    request: HypothesisStatusUpdateRequest,
    lifecycle: LifecycleDep,
) -> HypothesisResponse:
    hypothesis = ResearchRecordService(lifecycle.storage).update_hypothesis_status(
        hypothesis_id,
        request.status,
    )
    return hypothesis_response(hypothesis)


@router.post(
    "/sessions/{session_id}/debates",
    response_model=DebateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_debate(
    session_id: str,
    lifecycle: LifecycleDep,
) -> DebateResponse:
    debate = DebateService(lifecycle.storage).create_debate(
        research_session_id=session_id
    )
    return debate_response(debate)


@router.get(
    "/sessions/{session_id}/debates",
    response_model=ListResponse[DebateResponse],
)
def list_debates(
    session_id: str,
    lifecycle: LifecycleDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ListResponse[DebateResponse]:
    debates = [
        debate_response(debate)
        for debate in DebateService(lifecycle.storage).list_debates(
            research_session_id=session_id
        )
    ]
    return page(debates, limit, offset)


@router.get("/debates/{debate_id}", response_model=DebateResponse)
def get_debate(
    debate_id: str,
    lifecycle: LifecycleDep,
) -> DebateResponse:
    debate = DebateService(lifecycle.storage).get_debate(debate_id)
    return debate_response(debate)


@router.post(
    "/debates/{debate_id}/statements",
    response_model=DebateStatementResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_debate_statement(
    debate_id: str,
    request: DebateStatementCreateRequest,
    lifecycle: LifecycleDep,
) -> DebateStatementResponse:
    statement = DebateService(lifecycle.storage).add_debate_statement(
        debate_id=debate_id,
        **request.model_dump(),
    )
    return debate_statement_response(statement)


@router.post(
    "/debates/{debate_id}/proposal",
    response_model=DecisionProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
def assemble_decision_proposal(
    debate_id: str,
    request: DecisionProposalCreateRequest,
    lifecycle: LifecycleDep,
) -> DecisionProposalResponse:
    proposal = DebateService(lifecycle.storage).assemble_decision_proposal(
        debate_id=debate_id,
        **request.model_dump(),
    )
    return decision_proposal_response(proposal)


@router.post(
    "/proposals/{proposal_id}/risk-review",
    response_model=RiskReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_risk_review(
    proposal_id: str,
    request: RiskReviewCreateRequest,
    lifecycle: LifecycleDep,
) -> RiskReviewResponse:
    review = DebateService(lifecycle.storage).submit_risk_review(
        proposal_id=proposal_id,
        **request.model_dump(),
    )
    return risk_review_response(review)


@router.post(
    "/proposals/{proposal_id}/finalize",
    response_model=DecisionAssemblyResponse,
)
def finalize_decision(
    proposal_id: str,
    lifecycle: LifecycleDep,
) -> DecisionAssemblyResponse:
    assembly = DebateService(lifecycle.storage).finalize_decision(proposal_id)
    return decision_assembly_response(assembly)


@router.post(
    "/assemblies/{assembly_id}/settlement",
    response_model=ResearchAssemblySettlementResponse,
)
def settle_research_assembly(
    assembly_id: str,
    request: ResearchSettlementRequest,
    lifecycle: LifecycleDep,
    adapter: MarketDataAdapterDep,
) -> ResearchAssemblySettlementResponse:
    result = ResearchSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=adapter,
    ).settle_assembly(assembly_id=assembly_id, as_of=request.as_of)
    return research_assembly_settlement_response(
        record=result.record,
        outcome=result.outcome,
        evaluation=result.evaluation,
        review=review_response(result.review),
        learnings=result.learnings,
    )


@router.get("/market", response_model=ResearchMarketResponse)
def preview_market(
    lifecycle: LifecycleDep,
    adapter: BaoStockMarketDataAdapterDep,
    symbol: str = Query(min_length=1),
    days: int = Query(default=90, ge=1, le=180),
) -> ResearchMarketResponse:
    bars = MarketEvidenceImportService(
        adapter=adapter,
        lifecycle=lifecycle,
    ).preview_daily_bars(
        symbol=symbol,
        start_date=_start_date(days),
        end_date=_today(),
        adjustment=Adjustment.NONE,
    )
    latest = bars[-1]
    previous = bars[-2] if len(bars) > 1 else None
    change = None
    change_percent = None
    if previous and previous.close:
        change = latest.close - previous.close
        change_percent = change / previous.close
    observed_at = datetime.combine(
        latest.trade_date,
        datetime.min.time(),
        tzinfo=UTC,
    )
    return ResearchMarketResponse(
        symbol=latest.symbol,
        market=latest.market,
        source=latest.source,
        data_source="REAL MARKET DATA",
        latest=market_bar_response(latest),
        bars=[market_bar_response(bar) for bar in bars],
        change=change,
        change_percent=change_percent,
        observed_at=observed_at,
        available_at=latest.fetched_at,
    )


@router.post(
    "/evidence",
    response_model=ResearchEvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_market_evidence(
    request: ResearchEvidenceRequest,
    lifecycle: LifecycleDep,
    adapter: BaoStockMarketDataAdapterDep,
) -> ResearchEvidenceResponse:
    result = MarketEvidenceImportService(
        adapter=adapter,
        lifecycle=lifecycle,
    ).import_daily_bars(
        symbol=request.symbol,
        start_date=_start_date(request.days),
        end_date=_today(),
        adjustment=Adjustment.NONE,
    )
    latest = _latest_by_id(lifecycle.list_entities(Evidence), result.evidence_ids)
    return ResearchEvidenceResponse(
        symbol=result.symbol,
        requested=result.requested,
        created=result.created,
        existing=result.existing,
        evidence_ids=result.evidence_ids,
        latest_evidence=evidence_response(latest) if latest else None,
    )


@router.post(
    "/experiments",
    response_model=ExperimentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_research_experiment(
    request: ResearchExperimentRequest,
    lifecycle: LifecycleDep,
) -> ExperimentResponse:
    model = request.model or os.getenv("AIOS_EXTERNAL_LLM_MODEL")
    if not model:
        msg = "AIOS_EXTERNAL_LLM_MODEL is required to create a research Experiment"
        raise EvaluationConfigurationError(msg)
    experiment = lifecycle.start_experiment(
        Experiment(
            name=f"research-{request.symbol}",
            model=model,
            prompt_version="decision-v1",
            agent_config_version="manual-research-ui",
            dataset_snapshot=f"market-evidence:{request.symbol}",
            evidence_ids=tuple(request.evidence_ids),
            parameters={"temperature": 0},
            started_at=datetime.now(UTC),
        )
    )
    return experiment_response(experiment)


@router.post(
    "/decisions",
    response_model=ResearchDecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_research_decision(
    request: ResearchDecisionRequest,
    lifecycle: LifecycleDep,
    llm_adapter: LLMAdapterDep,
    generation_recorder: GenerationRecorderDep,
) -> ResearchDecisionResponse:
    result = DecisionGenerationService(
        lifecycle=lifecycle,
        llm_adapter=llm_adapter,
        generation_recorder=generation_recorder,
    ).generate(
        experiment_id=request.experiment_id,
        symbol=request.symbol,
        horizon=request.horizon,
    )
    return ResearchDecisionResponse(
        decision=decision_response(result.decision),
        generation=generation_metadata_response(result.generation),
    )


@router.post(
    "/settlements/{decision_id}",
    response_model=ResearchSettlementResponse,
    status_code=status.HTTP_201_CREATED,
)
def settle_research_decision(
    decision_id: str,
    request: ResearchSettlementRequest,
    lifecycle: LifecycleDep,
    adapter: BaoStockMarketDataAdapterDep,
) -> ResearchSettlementResponse:
    result = DecisionSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=adapter,
    ).settle(decision_id=decision_id, as_of=request.as_of)
    return ResearchSettlementResponse(
        outcome=decision_outcome_response(result.outcome),
        evaluation=decision_evaluation_response(result.evaluation),
        review=review_response(result.review),
    )


@router.get("/history", response_model=ResearchHistoryResponse)
def research_history(
    lifecycle: LifecycleDep,
    symbol: str = Query(min_length=1),
) -> ResearchHistoryResponse:
    evidence = [
        item for item in lifecycle.list_entities(Evidence) if symbol in item.symbols
    ]
    decisions = [
        item for item in lifecycle.list_entities(Decision) if item.symbol == symbol
    ]
    experiments = [
        item
        for item in lifecycle.list_entities(Experiment)
        if any(evidence_id in set(item.evidence_ids) for evidence_id in _ids(evidence))
    ]
    outcomes = [
        item
        for item in lifecycle.list_entities(DecisionOutcome)
        if item.symbol == symbol
    ]
    evaluations = []
    for decision in decisions:
        evaluation = lifecycle.get_decision_evaluation(
            decision.decision_id,
            "decision-evaluation-v1",
        )
        if evaluation is not None:
            evaluations.append(evaluation)
    reviews = []
    for decision in decisions:
        review = lifecycle.get_review_by_decision_id(decision.decision_id)
        if review is not None:
            reviews.append(review)
    rows = _history_rows(decisions, outcomes, reviews)
    return ResearchHistoryResponse(
        symbol=symbol,
        latest_evidence=evidence_response(evidence[-1]) if evidence else None,
        latest_experiment=experiment_response(experiments[-1]) if experiments else None,
        latest_decision=decision_response(decisions[-1]) if decisions else None,
        latest_outcome=decision_outcome_response(outcomes[-1]) if outcomes else None,
        latest_evaluation=(
            decision_evaluation_response(evaluations[-1]) if evaluations else None
        ),
        latest_review=review_response(reviews[-1]) if reviews else None,
        rows=rows,
    )


def _history_rows(
    decisions: list[Decision],
    outcomes: list[DecisionOutcome],
    reviews: list[Review],
) -> list[ResearchHistoryRow]:
    outcome_by_decision = {item.decision_id: item for item in outcomes}
    review_by_decision = {item.decision_id: item for item in reviews}
    rows: list[ResearchHistoryRow] = []
    for decision in reversed(decisions):
        outcome = outcome_by_decision.get(decision.decision_id)
        review = review_by_decision.get(decision.decision_id)
        rows.append(
            ResearchHistoryRow(
                time=review.created_at if review else decision.created_at,
                type="decision",
                decision_id=decision.decision_id,
                direction=decision.action.value,
                confidence=decision.confidence,
                realized_return=outcome.realized_return if outcome else None,
                review_outcome=review.outcome.value if review else None,
                status=review.outcome.value if review else decision.status.value,
            )
        )
    return rows


def _latest_by_id(items: list[Evidence], ids: list[str]) -> Evidence | None:
    by_id = {item.evidence_id: item for item in items}
    for evidence_id in reversed(ids):
        if evidence_id in by_id:
            return by_id[evidence_id]
    return None


def _ids(items: list[Evidence]) -> list[str]:
    return [item.evidence_id for item in items]


def _today() -> date:
    return datetime.now(UTC).date()


def _start_date(days: int) -> date:
    return _today() - timedelta(days=days)
