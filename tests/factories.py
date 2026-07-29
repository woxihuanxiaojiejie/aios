from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from aios.kernel.brain002 import AnalysisTask, SkillExecution, SkillResult
from aios.kernel.brain003 import DiscussionExecution, DiscussionResult
from aios.kernel.brain004 import (
    DecisionExecution,
    DecisionResult,
    DirectionRejection,
    ReferencedReason,
    RiskNote,
)
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
    SkillDirection,
    SkillExecutionStatus,
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
    return datetime.now(UTC).replace(microsecond=0)


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


def make_analysis_task(
    *,
    task_id: str = "at_00000000-0000-0000-0000-000000000001",
    symbol: str = "600519",
    market: str = "CN",
    evidence_ids: tuple[str, ...] = ("ev_00000000-0000-0000-0000-000000000001",),
    created_at: datetime | None = None,
) -> AnalysisTask:
    moment = created_at or fixed_now()
    return AnalysisTask(
        task_id=task_id,
        symbol=symbol,
        market=market,
        asset_type="stock",
        horizon="3d",
        as_of=moment,
        evidence_ids=evidence_ids,
        requested_skill_ids=(
            "technical_trend",
            "sector_strength",
            "policy_impact",
            "announcement_risk",
            "market_sentiment",
        ),
        created_at=moment,
    )


def make_skill_execution(
    *,
    execution_id: str = "sxn_00000000-0000-0000-0000-000000000001",
    task_id: str = "at_00000000-0000-0000-0000-000000000001",
    skill_id: str = "technical_trend",
    status: SkillExecutionStatus = SkillExecutionStatus.SUCCEEDED,
    created_at: datetime | None = None,
) -> SkillExecution:
    moment = created_at or fixed_now()
    return SkillExecution(
        execution_id=execution_id,
        task_id=task_id,
        skill_id=skill_id,
        skill_version="v1",
        started_at=moment,
        finished_at=moment + timedelta(seconds=2),
        status=status,
        provider="fixture",
        model="deterministic",
    )


def make_skill_result(
    *,
    result_id: str = "sr_00000000-0000-0000-0000-000000000001",
    execution_id: str = "sxn_00000000-0000-0000-0000-000000000001",
    skill_id: str = "technical_trend",
    evidence_ids: tuple[str, ...] = ("ev_00000000-0000-0000-0000-000000000001",),
    created_at: datetime | None = None,
) -> SkillResult:
    return SkillResult(
        result_id=result_id,
        execution_id=execution_id,
        skill_id=skill_id,
        skill_version="v1",
        conclusion="trend remains constructive",
        direction=SkillDirection.BULLISH,
        confidence=0.7,
        supporting_evidence_ids=evidence_ids,
        contradicting_evidence_ids=(),
        assumptions=("volume confirmation holds",),
        risk_factors=("policy reversal",),
        invalid_conditions=("breakdown below support",),
        missing_information=("next session volume",),
        reasoning_summary="price action and evidence support the hypothesis",
        raw_output={"summary": "structured fixture"},
        created_at=created_at or fixed_now(),
    )


def make_discussion_execution(
    *,
    discussion_execution_id: str = "dx_00000000-0000-0000-0000-000000000001",
    task_id: str = "at_00000000-0000-0000-0000-000000000001",
    skill_result_ids: tuple[str, ...] = ("sr_00000000-0000-0000-0000-000000000001",),
    created_at: datetime | None = None,
) -> DiscussionExecution:
    moment = created_at or fixed_now()
    return DiscussionExecution(
        discussion_execution_id=discussion_execution_id,
        task_id=task_id,
        skill_result_ids=skill_result_ids,
        started_at=moment,
        finished_at=moment + timedelta(seconds=3),
        status=SkillExecutionStatus.SUCCEEDED,
        provider="fixture",
        model="deterministic",
        created_at=moment,
    )


def make_discussion_result(
    *,
    discussion_result_id: str = "dr_00000000-0000-0000-0000-000000000001",
    discussion_execution_id: str = "dx_00000000-0000-0000-0000-000000000001",
    task_id: str = "at_00000000-0000-0000-0000-000000000001",
    skill_result_ids: tuple[str, ...] = ("sr_00000000-0000-0000-0000-000000000001",),
    evidence_ids: tuple[str, ...] = ("ev_00000000-0000-0000-0000-000000000001",),
    created_at: datetime | None = None,
) -> DiscussionResult:
    return DiscussionResult(
        discussion_result_id=discussion_result_id,
        discussion_execution_id=discussion_execution_id,
        task_id=task_id,
        skill_result_ids=skill_result_ids,
        conflicts=(
            {
                "skill_ids": ("technical_trend", "market_sentiment"),
                "conflict_type": "direction",
                "description": "technical evidence is stronger than sentiment caution",
                "reason": "sentiment input is less recent",
                "evidence_ids": evidence_ids,
            },
        ),
        evidence_reviews=(
            {
                "skill_id": "technical_trend",
                "sufficiency": "sufficient",
                "challenge": "needs follow-up volume confirmation",
                "referenced_evidence_ids": evidence_ids,
                "missing_evidence_categories": ("volume",),
            },
        ),
        counter_arguments=(
            {
                "skill_id": "market_sentiment",
                "argument": "sentiment may reverse quickly",
                "failure_mode": "momentum fades",
                "evidence_ids": evidence_ids,
            },
        ),
        revision_suggestions=(
            {
                "skill_id": "technical_trend",
                "original_confidence": 0.7,
                "suggested_confidence": 0.65,
                "reason": "sentiment conflict reduces confidence",
            },
        ),
        discussion_summary="discussion revised confidence lower",
        discussion_confidence=0.65,
        created_at=created_at or fixed_now(),
    )


def make_decision_execution(
    *,
    decision_execution_id: str = "dxe_00000000-0000-0000-0000-000000000001",
    task_id: str = "at_00000000-0000-0000-0000-000000000001",
    discussion_result_id: str = "dr_00000000-0000-0000-0000-000000000001",
    skill_result_ids: tuple[str, ...] = ("sr_00000000-0000-0000-0000-000000000001",),
    evidence_ids: tuple[str, ...] = ("ev_00000000-0000-0000-0000-000000000001",),
    created_at: datetime | None = None,
) -> DecisionExecution:
    moment = created_at or fixed_now()
    return DecisionExecution(
        decision_execution_id=decision_execution_id,
        task_id=task_id,
        discussion_result_id=discussion_result_id,
        skill_result_ids=skill_result_ids,
        evidence_ids=evidence_ids,
        started_at=moment,
        finished_at=moment + timedelta(seconds=2),
        status=SkillExecutionStatus.SUCCEEDED,
        provider="fixture",
        model="deterministic",
        created_at=moment,
    )


def make_decision_result(
    *,
    decision_result_id: str = "ds_00000000-0000-0000-0000-000000000001",
    decision_execution_id: str = "dxe_00000000-0000-0000-0000-000000000001",
    task_id: str = "at_00000000-0000-0000-0000-000000000001",
    discussion_result_id: str = "dr_00000000-0000-0000-0000-000000000001",
    skill_result_ids: tuple[str, ...] = ("sr_00000000-0000-0000-0000-000000000001",),
    evidence_ids: tuple[str, ...] = ("ev_00000000-0000-0000-0000-000000000001",),
    created_at: datetime | None = None,
) -> DecisionResult:
    return DecisionResult(
        decision_result_id=decision_result_id,
        decision_execution_id=decision_execution_id,
        task_id=task_id,
        discussion_result_id=discussion_result_id,
        skill_result_ids=skill_result_ids,
        direction="bullish",
        confidence=0.68,
        action=Action.BUY,
        reasoning=(
            ReferencedReason(
                reason="evidence and discussion support upside",
                skill_ids=skill_result_ids,
                discussion_refs=("discussion_summary",),
                evidence_ids=evidence_ids,
            ),
        ),
        supporting_skills=("technical_trend",),
        opposing_skills=("market_sentiment",),
        discussion_refs=("discussion_summary",),
        evidence_refs=evidence_ids,
        risks=(
            RiskNote(
                risk="policy reversal",
                uncertainty="sentiment conflict",
                invalid_condition="breakdown below support",
                evidence_ids=evidence_ids,
            ),
        ),
        rejected_directions=(
            DirectionRejection(
                direction="bearish",
                reason="supporting evidence is stronger",
                skill_ids=skill_result_ids,
                discussion_refs=("discussion_summary",),
                evidence_ids=evidence_ids,
            ),
        ),
        decision_summary="buy with reduced confidence",
        created_at=created_at or fixed_now(),
    )
