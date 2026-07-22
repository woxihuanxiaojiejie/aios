from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from aios.adapters.market_data import MarketDataAdapter
from aios.application.decision_settlement import (
    DecisionSettlementResult,
    DecisionSettlementService,
)
from aios.kernel.base import utc_now
from aios.kernel.debate import (
    DebateRecord,
    DecisionAssemblyRecord,
    DecisionProposal,
    RiskReview,
)
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    EvaluationFinalResult,
    LearningType,
)
from aios.kernel.errors import DecisionNotReadyForSettlementError
from aios.kernel.learning import Learning
from aios.kernel.research import ResearchSession
from aios.kernel.research_records import AgentReport, Hypothesis
from aios.kernel.review import Review
from aios.kernel.settlement import (
    DecisionEvaluation,
    DecisionOutcome,
    ResearchSettlementRecord,
)
from aios.workflows.decision_lifecycle import DecisionLifecycleService

REAL_MARKET_SOURCES = {"akshare", "baostock"}
FIXTURE_MARKET_PREFIXES = ("fixture",)


@dataclass(frozen=True)
class ResearchSettlementResult:
    record: ResearchSettlementRecord
    outcome: DecisionOutcome
    evaluation: DecisionEvaluation
    review: Review
    learnings: tuple[Learning, ...]


class ResearchSettlementService:
    def __init__(
        self,
        *,
        lifecycle: DecisionLifecycleService,
        market_data_adapter: MarketDataAdapter,
    ) -> None:
        self._lifecycle = lifecycle
        self._market_data_adapter = market_data_adapter

    def settle_assembly(
        self,
        *,
        assembly_id: str,
        as_of: datetime | None = None,
    ) -> ResearchSettlementResult:
        existing = self._lifecycle.storage.get_research_settlement_by_assembly_id(
            assembly_id
        )
        if existing is not None:
            return self._result_from_record(existing)

        assembly = self._lifecycle.get_entity(DecisionAssemblyRecord, assembly_id)
        session = self._lifecycle.get_entity(
            ResearchSession,
            assembly.research_session_id,
        )
        decision = self._lifecycle.get_entity(Decision, assembly.decision_id)
        self._validate_session_decision(session, decision)

        settled_as_of = _as_utc(as_of or utc_now())
        if settled_as_of < session.scope.valid_until:
            msg = f"ResearchSession {session.research_session_id} is not ready"
            raise DecisionNotReadyForSettlementError(msg)

        context = _ResearchContext.from_storage(self._lifecycle, assembly)
        settlement = DecisionSettlementService(
            lifecycle=self._lifecycle,
            market_data_adapter=self._market_data_adapter,
            review_builder=lambda outcome, evaluation: _research_review(
                outcome,
                evaluation,
                context,
            ),
        ).settle(decision_id=decision.decision_id, as_of=settled_as_of)
        self._validate_market_source(settlement.outcome)
        learnings = self._propose_learnings(settlement, context)
        record = ResearchSettlementRecord(
            assembly_id=assembly.assembly_id,
            research_session_id=assembly.research_session_id,
            debate_id=assembly.debate_id,
            proposal_id=assembly.proposal_id,
            risk_review_id=assembly.risk_review_id,
            decision_id=assembly.decision_id,
            outcome_id=settlement.outcome.outcome_id,
            evaluation_id=settlement.evaluation.evaluation_id,
            review_id=settlement.review.review_id,
            learning_ids=tuple(learning.learning_id for learning in learnings),
            evidence_ids=assembly.evidence_ids,
            report_ids=assembly.report_ids,
            hypothesis_ids=assembly.hypothesis_ids,
            settled_at=settlement.outcome.settled_at,
        )
        self._lifecycle.storage.save(record)
        return ResearchSettlementResult(
            record=record,
            outcome=settlement.outcome,
            evaluation=settlement.evaluation,
            review=settlement.review,
            learnings=learnings,
        )

    def _result_from_record(
        self,
        record: ResearchSettlementRecord,
    ) -> ResearchSettlementResult:
        return ResearchSettlementResult(
            record=record,
            outcome=self._lifecycle.get_entity(DecisionOutcome, record.outcome_id),
            evaluation=self._lifecycle.get_entity(
                DecisionEvaluation,
                record.evaluation_id,
            ),
            review=self._lifecycle.get_entity(Review, record.review_id),
            learnings=tuple(
                self._lifecycle.get_entity(Learning, learning_id)
                for learning_id in record.learning_ids
            ),
        )

    def _validate_session_decision(
        self,
        session: ResearchSession,
        decision: Decision,
    ) -> None:
        expected_horizon = f"{session.scope.horizon_days}d"
        if decision.horizon != expected_horizon:
            msg = "ResearchSession horizon must match Decision horizon"
            raise ValueError(msg)
        if decision.valid_until != session.scope.valid_until:
            msg = "ResearchSession valid_until must match Decision valid_until"
            raise ValueError(msg)

    def _validate_market_source(self, outcome: DecisionOutcome) -> None:
        source = outcome.market_data_source.lower()
        if source in REAL_MARKET_SOURCES:
            return
        if source.startswith(FIXTURE_MARKET_PREFIXES):
            return
        msg = "settlement market data must be real or explicitly marked fixture"
        raise ValueError(msg)

    def _propose_learnings(
        self,
        settlement: DecisionSettlementResult,
        context: _ResearchContext,
    ) -> tuple[Learning, ...]:
        existing = [
            learning
            for learning in self._lifecycle.list_entities(Learning)
            if learning.review_id == settlement.review.review_id
        ]
        if existing:
            return tuple(existing)
        performance = (
            "passed"
            if (settlement.evaluation.final_result is EvaluationFinalResult.PASS)
            else "did not pass"
        )
        proposals = (
            Learning(
                review_id=settlement.review.review_id,
                learning_type=LearningType.AGENT_WEIGHT_UPDATE,
                target=f"research-session:{context.session.research_session_id}:agent-weights",
                before={"report_ids": list(context.assembly.report_ids)},
                after={
                    "suggestion": "review report weights manually",
                    "stronger_report_ids": list(
                        _stronger_report_ids(settlement.evaluation, context)
                    ),
                    "weaker_report_ids": list(
                        _weaker_report_ids(settlement.evaluation, context)
                    ),
                },
                reason=(
                    f"Settlement {performance}; keep this as an auditable "
                    "recommendation, not an automatic weight change."
                ),
            ),
            Learning(
                review_id=settlement.review.review_id,
                learning_type=LearningType.RULE_UPDATE,
                target=f"research-session:{context.session.research_session_id}:debate-risk-review",
                before={
                    "proposal_conclusion": context.proposal.conclusion.value,
                    "risk_final_conclusion": context.risk.final_conclusion.value,
                },
                after={
                    "suggestion": "review Debate and RiskReview gates manually",
                    "evaluation_final_result": settlement.evaluation.final_result.value,
                },
                reason=(
                    "Debate/RiskReview effect was recorded for audit; no runtime "
                    "or trading rule was changed automatically."
                ),
            ),
        )
        return tuple(
            self._lifecycle.propose_learning(learning) for learning in proposals
        )


@dataclass(frozen=True)
class _ResearchContext:
    assembly: DecisionAssemblyRecord
    session: ResearchSession
    debate: DebateRecord
    proposal: DecisionProposal
    risk: RiskReview
    hypotheses: tuple[Hypothesis, ...]
    reports: tuple[AgentReport, ...]

    @classmethod
    def from_storage(
        cls,
        lifecycle: DecisionLifecycleService,
        assembly: DecisionAssemblyRecord,
    ) -> _ResearchContext:
        return cls(
            assembly=assembly,
            session=lifecycle.get_entity(ResearchSession, assembly.research_session_id),
            debate=lifecycle.get_entity(DebateRecord, assembly.debate_id),
            proposal=lifecycle.get_entity(DecisionProposal, assembly.proposal_id),
            risk=lifecycle.get_entity(RiskReview, assembly.risk_review_id),
            hypotheses=tuple(
                lifecycle.get_entity(Hypothesis, hypothesis_id)
                for hypothesis_id in assembly.hypothesis_ids
            ),
            reports=tuple(
                lifecycle.get_entity(AgentReport, report_id)
                for report_id in assembly.report_ids
            ),
        )


def _research_review(
    outcome: DecisionOutcome,
    evaluation: DecisionEvaluation,
    context: _ResearchContext,
) -> Review:
    base = DecisionSettlementService.review_from_settlement(outcome, evaluation)
    supported_hypotheses = _supported_hypothesis_ids(evaluation, context)
    denied_hypotheses = _denied_hypothesis_ids(evaluation, context)
    stronger_reports = _stronger_report_ids(evaluation, context)
    weaker_reports = _weaker_report_ids(evaluation, context)
    correctness = (
        "final conclusion correct"
        if evaluation.final_result is EvaluationFinalResult.PASS
        else "final conclusion not confirmed"
    )
    debate_effect = _debate_effect(evaluation, context.proposal, context.risk)
    summary = (
        f"{base.review_summary}; {correctness}; "
        f"supported hypotheses: {', '.join(supported_hypotheses) or 'none'}; "
        f"denied hypotheses: {', '.join(denied_hypotheses) or 'none'}; "
        f"stronger reports: {', '.join(stronger_reports) or 'none'}; "
        f"weaker reports: {', '.join(weaker_reports) or 'none'}; "
        f"Debate/RiskReview: {debate_effect}."
    )
    return base.model_copy(
        update={
            "review_summary": summary,
            "cause_tags": (*base.cause_tags, "research_settlement_closeout"),
        }
    )


def _supported_hypothesis_ids(
    evaluation: DecisionEvaluation,
    context: _ResearchContext,
) -> tuple[str, ...]:
    if evaluation.final_result is EvaluationFinalResult.PASS:
        return context.proposal.supporting_hypothesis_ids
    return context.proposal.rejected_hypothesis_ids


def _denied_hypothesis_ids(
    evaluation: DecisionEvaluation,
    context: _ResearchContext,
) -> tuple[str, ...]:
    if evaluation.final_result is EvaluationFinalResult.PASS:
        return context.proposal.rejected_hypothesis_ids
    return context.proposal.supporting_hypothesis_ids


def _stronger_report_ids(
    evaluation: DecisionEvaluation,
    context: _ResearchContext,
) -> tuple[str, ...]:
    supported = set(_supported_hypothesis_ids(evaluation, context))
    return tuple(
        report_id
        for hypothesis in context.hypotheses
        if hypothesis.hypothesis_id in supported
        for report_id in hypothesis.supporting_report_ids
    )


def _weaker_report_ids(
    evaluation: DecisionEvaluation,
    context: _ResearchContext,
) -> tuple[str, ...]:
    denied = set(_denied_hypothesis_ids(evaluation, context))
    return tuple(
        report_id
        for hypothesis in context.hypotheses
        if hypothesis.hypothesis_id in denied
        for report_id in hypothesis.supporting_report_ids
    )


def _debate_effect(
    evaluation: DecisionEvaluation,
    proposal: DecisionProposal,
    risk: RiskReview,
) -> str:
    changed = proposal.conclusion is not risk.final_conclusion
    if not changed:
        return "preserved the proposal conclusion"
    if evaluation.final_result is EvaluationFinalResult.PASS:
        return "improved the proposal through risk adjustment"
    return "changed the proposal but did not improve the final result"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        msg = "as_of must be timezone-aware"
        raise ValueError(msg)
    return value.astimezone(UTC)
