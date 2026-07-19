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
)
from aios.api.schemas.decision import decision_response
from aios.api.schemas.decision_generation import generation_metadata_response
from aios.api.schemas.evidence import evidence_response
from aios.api.schemas.experiment import ExperimentResponse, experiment_response
from aios.api.schemas.market_data import market_bar_response
from aios.api.schemas.research import (
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
)
from aios.api.schemas.review import review_response
from aios.application.decision_generation import DecisionGenerationService
from aios.application.decision_settlement import DecisionSettlementService
from aios.application.market_evidence import MarketEvidenceImportService
from aios.kernel.decision import Decision
from aios.kernel.errors import EvaluationConfigurationError
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.review import Review
from aios.kernel.settlement import DecisionOutcome

router = APIRouter(prefix="/research", tags=["research"])


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
