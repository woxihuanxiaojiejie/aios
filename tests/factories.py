from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from aios.kernel.debate import (
    DebateRecord,
    DebateStatement,
    DecisionProposal,
    RiskReview,
)
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    Action,
    DirectionalResult,
    EvaluationFinalResult,
    OutcomeStatus,
    ReturnResult,
    RiskResult,
)
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.research import ResearchScope, ResearchSession
from aios.kernel.research_records import AgentReport, Hypothesis
from aios.kernel.review import Review
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.kernel.watchlist import WatchlistItem, WatchlistStatus


def fixed_now() -> datetime:
    return datetime(2026, 7, 19, 8, 0, tzinfo=UTC)


def make_evidence(
    *,
    evidence_id: str = "ev_00000000-0000-0000-0000-000000000001",
    summary: str = "updated guidance",
    created_at: datetime | None = None,
) -> Evidence:
    moment = fixed_now()
    return Evidence(
        evidence_id=evidence_id,
        evidence_type="filing",
        source="company-report",
        symbols=["NVDA", "MSFT"],
        published_at=moment,
        available_at=moment + timedelta(minutes=2),
        summary=summary,
        reliability=0.85,
        content_hash=f"hash-{evidence_id}",
        metadata={"form": "10-Q", "nested": {"page": 3}},
        created_at=created_at or moment,
    )


def make_experiment(
    evidence_id: str,
    *,
    experiment_id: str = "ex_00000000-0000-0000-0000-000000000001",
    model: str = "model-v1",
    prompt_version: str = "prompt-v1",
    parameters: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> Experiment:
    moment = fixed_now()
    return Experiment(
        experiment_id=experiment_id,
        name="guidance-check",
        model=model,
        prompt_version=prompt_version,
        agent_config_version="agent-v1",
        dataset_snapshot="snapshot-v1",
        evidence_ids=[evidence_id],
        parameters=parameters or {"temperature": 0, "weights": [1, 2]},
        started_at=moment + timedelta(minutes=3),
        finished_at=moment + timedelta(minutes=4),
        created_at=created_at or moment,
    )


def make_decision(
    experiment_id: str,
    evidence_id: str,
    *,
    decision_id: str = "dc_00000000-0000-0000-0000-000000000001",
    created_at: datetime | None = None,
) -> Decision:
    moment = fixed_now()
    created = created_at or moment + timedelta(minutes=5)
    return Decision(
        decision_id=decision_id,
        experiment_id=experiment_id,
        symbol="NVDA",
        action=Action.BUY,
        horizon="5d",
        confidence=0.72,
        expected_return=0.04,
        max_expected_loss=0.02,
        evidence_ids=[evidence_id],
        reasoning_summary="guidance improved while risk stayed bounded",
        created_at=created,
        valid_until=created + timedelta(days=5),
    )


def make_review(
    decision_id: str,
    *,
    review_id: str = "rv_00000000-0000-0000-0000-000000000001",
    created_at: datetime | None = None,
) -> Review:
    return Review(
        review_id=review_id,
        decision_id=decision_id,
        actual_return=0.03,
        direction_correct=True,
        risk_limit_breached=False,
        outcome="profit",
        cause_tags=["guidance", "momentum"],
        review_summary="decision matched the evidence-backed thesis",
        created_at=created_at or fixed_now() + timedelta(days=5),
    )


def make_learning(
    review_id: str,
    *,
    learning_id: str = "lr_00000000-0000-0000-0000-000000000001",
    created_at: datetime | None = None,
) -> Learning:
    return Learning(
        learning_id=learning_id,
        review_id=review_id,
        learning_type="agent_weight_update",
        target="guidance-signal-weight",
        before={"weight": 0.4, "tags": ["guidance"]},
        after={"weight": 0.45, "tags": ["guidance"]},
        reason="profitable reviewed decision",
        created_at=created_at or fixed_now() + timedelta(days=5, minutes=1),
    )


def make_outcome(
    decision_id: str,
    experiment_id: str,
    *,
    outcome_id: str = "oc_00000000-0000-0000-0000-000000000001",
    created_at: datetime | None = None,
) -> DecisionOutcome:
    moment = created_at or fixed_now() + timedelta(days=1)
    return DecisionOutcome(
        outcome_id=outcome_id,
        decision_id=decision_id,
        experiment_id=experiment_id,
        symbol="NVDA",
        horizon="1d",
        horizon_semantics="natural_time",
        observation_started_at=fixed_now(),
        observation_ended_at=fixed_now() + timedelta(days=1),
        entry_price="10.00",
        exit_price="10.30",
        realized_return="0.03",
        maximum_adverse_excursion="-0.01",
        maximum_favorable_excursion="0.04",
        market_data_source="deterministic-test",
        market_data_snapshot={"entry_trade_date": "2026-07-20"},
        settled_at=moment,
        status=OutcomeStatus.SETTLED,
        created_at=moment,
    )


def make_evaluation(
    decision_id: str,
    outcome_id: str,
    experiment_id: str,
    *,
    evaluation_id: str = "de_00000000-0000-0000-0000-000000000001",
    created_at: datetime | None = None,
) -> DecisionEvaluation:
    moment = created_at or fixed_now() + timedelta(days=1, minutes=1)
    return DecisionEvaluation(
        evaluation_id=evaluation_id,
        decision_id=decision_id,
        outcome_id=outcome_id,
        experiment_id=experiment_id,
        directional_result=DirectionalResult.CORRECT,
        return_result=ReturnResult.MET,
        risk_result=RiskResult.WITHIN_LIMIT,
        final_result=EvaluationFinalResult.PASS,
        evaluation_rules_version="decision-evaluation-v1",
        evaluated_at=moment,
        explanation="deterministic evaluation",
        created_at=moment,
    )


def make_watchlist_item(
    *,
    watchlist_item_id: str = "wl_00000000-0000-0000-0000-000000000001",
    symbol: str = "600519",
    market: str = "CN",
    note: str | None = "policy and consumption recovery watch",
    status: WatchlistStatus = WatchlistStatus.ACTIVE,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    archived_at: datetime | None = None,
) -> WatchlistItem:
    moment = fixed_now()
    if status is WatchlistStatus.ARCHIVED and archived_at is None:
        archived_at = moment + timedelta(minutes=10)
    return WatchlistItem(
        watchlist_item_id=watchlist_item_id,
        symbol=symbol,
        market=market,
        note=note,
        status=status,
        created_at=created_at or moment,
        updated_at=updated_at or moment,
        archived_at=archived_at,
    )


def make_research_session(
    *,
    research_session_id: str = "rs_00000000-0000-0000-0000-000000000001",
    watchlist_item_id: str = "wl_00000000-0000-0000-0000-000000000001",
    symbol: str = "600519",
    market: str = "CN",
    evidence_ids: tuple[str, ...] = (),
    as_of: datetime | None = None,
) -> ResearchSession:
    moment = as_of or fixed_now() + timedelta(hours=1)
    return ResearchSession(
        research_session_id=research_session_id,
        scope=ResearchScope(
            watchlist_item_id=watchlist_item_id,
            symbol=symbol,
            market=market,
            watchlist_note_snapshot="policy and consumption recovery watch",
            horizon_days=3,
            as_of=moment,
            valid_until=moment + timedelta(days=3),
        ),
        evidence_ids=evidence_ids,
    )


def make_agent_report(
    *,
    report_id: str = "ar_00000000-0000-0000-0000-000000000001",
    research_session_id: str = "rs_00000000-0000-0000-0000-000000000001",
    evidence_ids: tuple[str, ...] = (),
) -> AgentReport:
    return AgentReport(
        report_id=report_id,
        research_session_id=research_session_id,
        role="technical",
        summary="trend remains constructive",
        stance="watch",
        confidence=0.7,
        evidence_ids=evidence_ids,
        source="manual",
        raw_reference=None,
        created_at=fixed_now(),
        updated_at=fixed_now(),
    )


def make_hypothesis(
    *,
    hypothesis_id: str = "hp_00000000-0000-0000-0000-000000000001",
    research_session_id: str = "rs_00000000-0000-0000-0000-000000000001",
    report_ids: tuple[str, ...] = ("ar_00000000-0000-0000-0000-000000000001",),
    evidence_ids: tuple[str, ...] = (),
) -> Hypothesis:
    return Hypothesis(
        hypothesis_id=hypothesis_id,
        research_session_id=research_session_id,
        statement="Demand recovery supports upside",
        rationale="Agent report cites evidence aligned with the session scope.",
        direction="bullish",
        horizon_days=3,
        confidence=0.65,
        supporting_report_ids=report_ids,
        supporting_evidence_ids=evidence_ids,
        created_at=fixed_now(),
        updated_at=fixed_now(),
    )


def make_debate(
    *,
    debate_id: str = "db_00000000-0000-0000-0000-000000000001",
    research_session_id: str = "rs_00000000-0000-0000-0000-000000000001",
    report_ids: tuple[str, ...] = ("ar_00000000-0000-0000-0000-000000000001",),
    hypothesis_ids: tuple[str, ...] = ("hp_00000000-0000-0000-0000-000000000001",),
) -> DebateRecord:
    return DebateRecord(
        debate_id=debate_id,
        research_session_id=research_session_id,
        report_ids=report_ids,
        hypothesis_ids=hypothesis_ids,
        created_at=fixed_now(),
        updated_at=fixed_now(),
    )


def make_debate_statement(
    *,
    statement_id: str = "ds_00000000-0000-0000-0000-000000000001",
    debate_id: str = "db_00000000-0000-0000-0000-000000000001",
    report_id: str = "ar_00000000-0000-0000-0000-000000000001",
    hypothesis_id: str = "hp_00000000-0000-0000-0000-000000000001",
    evidence_ids: tuple[str, ...] = (),
) -> DebateStatement:
    return DebateStatement(
        statement_id=statement_id,
        debate_id=debate_id,
        agent_report_id=report_id,
        hypothesis_id=hypothesis_id,
        stance="support",
        reasoning="evidence supports the hypothesis",
        evidence_ids=evidence_ids,
        confidence_before=0.5,
        confidence_after=0.6,
        created_at=fixed_now(),
    )


def make_decision_proposal(
    *,
    proposal_id: str = "dp_00000000-0000-0000-0000-000000000001",
    debate_id: str = "db_00000000-0000-0000-0000-000000000001",
    hypothesis_ids: tuple[str, ...] = ("hp_00000000-0000-0000-0000-000000000001",),
    evidence_ids: tuple[str, ...] = (),
) -> DecisionProposal:
    return DecisionProposal(
        proposal_id=proposal_id,
        debate_id=debate_id,
        conclusion="watch",
        confidence=0.6,
        thesis="watch pending confirmation",
        supporting_hypothesis_ids=hypothesis_ids,
        rejected_hypothesis_ids=(),
        evidence_ids=evidence_ids,
        risk_notes=("position size pending",),
        created_at=fixed_now(),
    )


def make_risk_review(
    *,
    risk_review_id: str = "rr_00000000-0000-0000-0000-000000000001",
    proposal_id: str = "dp_00000000-0000-0000-0000-000000000001",
) -> RiskReview:
    return RiskReview(
        risk_review_id=risk_review_id,
        proposal_id=proposal_id,
        verdict="approve",
        final_conclusion="watch",
        final_confidence=0.5,
        reasons=("risk is bounded",),
        created_at=fixed_now(),
    )
