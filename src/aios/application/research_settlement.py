from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from aios.adapters.llm import LLMAdapter, LLMStructuredResult
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
    OutcomeStatus,
)
from aios.kernel.errors import DecisionNotReadyForSettlementError
from aios.kernel.evidence import Evidence
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

REAL_MARKET_SOURCE_PREFIXES = ("akshare", "baostock")
FIXTURE_MARKET_PREFIXES = ("fixture",)
BRAIN005_LEARNING_PROMPT_VERSION = "brain005-learning-advice-v1"
MAX_SKILL_WEIGHT_DELTA = Decimal("0.05")
DEFAULT_SKILL_WEIGHT_DELTA = Decimal("0.02")


@dataclass(frozen=True)
class ResearchSettlementResult:
    record: ResearchSettlementRecord
    outcome: DecisionOutcome
    evaluation: DecisionEvaluation
    review: Review
    learnings: tuple[Learning, ...]


class SkillWeightAdjustmentAdvice(BaseModel):
    skill_id: str = Field(min_length=1)
    report_id: str = Field(min_length=1)
    delta: Decimal
    reason: str = Field(min_length=1, max_length=300)

    @field_validator("delta", mode="before")
    @classmethod
    def validate_delta(cls, value: object) -> Decimal:
        return Decimal(str(value))


class Brain005LearningAdvice(BaseModel):
    cause_summary: str = Field(min_length=1, max_length=600)
    evidence_references: tuple[str, ...] = ()
    report_references: tuple[str, ...] = ()
    skill_weight_adjustments: tuple[SkillWeightAdjustmentAdvice, ...] = ()
    learning_recommendations: tuple[str, ...] = ()


@dataclass(frozen=True)
class _LearningAdviceResult:
    advice: Brain005LearningAdvice
    audit: dict[str, object]


class ResearchSettlementService:
    def __init__(
        self,
        *,
        lifecycle: DecisionLifecycleService,
        market_data_adapter: MarketDataAdapter,
        llm_adapter: LLMAdapter | None = None,
        llm_model: str | None = None,
    ) -> None:
        self._lifecycle = lifecycle
        self._market_data_adapter = market_data_adapter
        self._llm_adapter = llm_adapter
        self._llm_model = llm_model

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

    def settle_due(
        self,
        *,
        as_of: datetime | None = None,
        limit: int | None = None,
    ) -> tuple[ResearchSettlementResult, ...]:
        settled_as_of = _as_utc(as_of or utc_now())
        results: list[ResearchSettlementResult] = []
        for assembly in self._lifecycle.list_entities(DecisionAssemblyRecord):
            if limit is not None and len(results) >= limit:
                break
            if (
                self._lifecycle.storage.get_research_settlement_by_assembly_id(
                    assembly.assembly_id
                )
                is not None
            ):
                continue
            decision = self._lifecycle.get_entity(Decision, assembly.decision_id)
            if decision.valid_until > settled_as_of:
                continue
            results.append(
                self.settle_assembly(
                    assembly_id=assembly.assembly_id,
                    as_of=settled_as_of,
                )
            )
        return tuple(results)

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
        if outcome.status is OutcomeStatus.INSUFFICIENT_DATA:
            return
        source = outcome.market_data_source.lower()
        if source.startswith(REAL_MARKET_SOURCE_PREFIXES):
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
        performance = (
            "passed"
            if (settlement.evaluation.final_result is EvaluationFinalResult.PASS)
            else "did not pass"
        )
        advice_result = self._learning_advice(settlement, context)
        advice = advice_result.advice if advice_result else None
        source_refs = _source_refs(settlement, context)
        weight_adjustments = _skill_weight_adjustments(
            settlement,
            context,
            advice,
        )
        proposals = (
            Learning(
                review_id=settlement.review.review_id,
                learning_type=LearningType.AGENT_WEIGHT_UPDATE,
                target=f"research-session:{context.session.research_session_id}:agent-weights",
                before={
                    "report_ids": list(context.assembly.report_ids),
                    "current_weights": "not_loaded",
                },
                after={
                    "application_mode": "proposal_only",
                    "status": "pending_approval",
                    "prompt_version": BRAIN005_LEARNING_PROMPT_VERSION,
                    "source_refs": source_refs,
                    "llm_audit": advice_result.audit if advice_result else None,
                    "llm_cause_summary": advice.cause_summary if advice else None,
                    "llm_evidence_references": list(
                        advice.evidence_references if advice else ()
                    ),
                    "llm_report_references": list(
                        advice.report_references if advice else ()
                    ),
                    "stronger_report_ids": list(
                        _stronger_report_ids(settlement.evaluation, context)
                    ),
                    "weaker_report_ids": list(
                        _weaker_report_ids(settlement.evaluation, context)
                    ),
                    "skill_weight_adjustments": weight_adjustments,
                    "learning_recommendations": list(
                        advice.learning_recommendations if advice else ()
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
                    "application_mode": "proposal_only",
                    "status": "pending_approval",
                    "source_refs": source_refs,
                    "suggestion": "review Debate and RiskReview gates manually",
                    "evaluation_final_result": settlement.evaluation.final_result.value,
                },
                reason=(
                    "Debate/RiskReview effect was recorded for audit; no runtime "
                    "or trading rule was changed automatically."
                ),
            ),
        )
        existing_by_key = {
            (learning.learning_type, learning.target): learning for learning in existing
        }
        saved: list[Learning] = []
        for proposal in proposals:
            key = (proposal.learning_type, proposal.target)
            existing_proposal = existing_by_key.get(key)
            if existing_proposal is not None:
                saved.append(existing_proposal)
                continue
            saved.append(self._lifecycle.propose_learning(proposal))
        return tuple(saved)

    def _learning_advice(
        self,
        settlement: DecisionSettlementResult,
        context: _ResearchContext,
    ) -> _LearningAdviceResult | None:
        if self._llm_adapter is None:
            return None
        model = self._llm_model or os.getenv("AIOS_EXTERNAL_LLM_MODEL")
        if not model:
            msg = "llm_model or AIOS_EXTERNAL_LLM_MODEL is required for LLM advice"
            raise ValueError(msg)
        result = self._llm_adapter.generate_structured(
            model=model,
            system_prompt=(
                "You produce BRAIN-005 settlement learning advice. "
                "Do not calculate prices, returns, scores, or final results. "
                "Only attribute errors and propose auditable, pending learning "
                "recommendations. Weight deltas are recommendations only. "
                "Return only one JSON object with exactly these top-level keys: "
                "cause_summary, evidence_references, report_references, "
                "skill_weight_adjustments, learning_recommendations. "
                "Each skill_weight_adjustments item must contain skill_id, "
                "report_id, delta, and reason. Do not use alternative keys."
            ),
            user_prompt=json.dumps(
                _learning_prompt_payload(settlement, context),
                sort_keys=True,
                default=str,
            ),
            response_schema=Brain005LearningAdvice,
            temperature=0,
        )
        advice = (
            result.parsed
            if isinstance(result.parsed, Brain005LearningAdvice)
            else Brain005LearningAdvice.model_validate(result.parsed)
        )
        return _LearningAdviceResult(advice=advice, audit=_llm_audit(result))


@dataclass(frozen=True)
class _ResearchContext:
    assembly: DecisionAssemblyRecord
    session: ResearchSession
    debate: DebateRecord
    proposal: DecisionProposal
    risk: RiskReview
    evidence: tuple[Evidence, ...]
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
            evidence=tuple(
                lifecycle.get_entity(Evidence, evidence_id)
                for evidence_id in assembly.evidence_ids
            ),
            hypotheses=tuple(
                lifecycle.get_entity(Hypothesis, hypothesis_id)
                for hypothesis_id in assembly.hypothesis_ids
            ),
            reports=tuple(
                lifecycle.get_entity(AgentReport, report_id)
                for report_id in assembly.report_ids
            ),
        )


def _source_refs(
    settlement: DecisionSettlementResult,
    context: _ResearchContext,
) -> dict[str, object]:
    return {
        "decision_id": settlement.outcome.decision_id,
        "outcome_id": settlement.outcome.outcome_id,
        "evaluation_id": settlement.evaluation.evaluation_id,
        "review_id": settlement.review.review_id,
        "assembly_id": context.assembly.assembly_id,
        "research_session_id": context.session.research_session_id,
        "debate_id": context.debate.debate_id,
        "proposal_id": context.proposal.proposal_id,
        "risk_review_id": context.risk.risk_review_id,
        "evidence_ids": list(context.assembly.evidence_ids),
        "report_ids": list(context.assembly.report_ids),
        "hypothesis_ids": list(context.assembly.hypothesis_ids),
    }


def _learning_prompt_payload(
    settlement: DecisionSettlementResult,
    context: _ResearchContext,
) -> dict[str, object]:
    return {
        "decision": {
            "decision_id": settlement.outcome.decision_id,
            "symbol": settlement.outcome.symbol,
            "horizon": settlement.outcome.horizon,
            "realized_return": settlement.outcome.realized_return,
            "maximum_adverse_excursion": settlement.outcome.maximum_adverse_excursion,
            "maximum_favorable_excursion": (
                settlement.outcome.maximum_favorable_excursion
            ),
            "status": settlement.outcome.status.value,
        },
        "evaluation": {
            "directional_result": settlement.evaluation.directional_result.value,
            "return_result": settlement.evaluation.return_result.value,
            "risk_result": settlement.evaluation.risk_result.value,
            "final_result": settlement.evaluation.final_result.value,
            "explanation": settlement.evaluation.explanation,
        },
        "review": {
            "cause_tags": list(settlement.review.cause_tags),
            "review_summary": settlement.review.review_summary,
        },
        "proposal": {
            "proposal_id": context.proposal.proposal_id,
            "conclusion": context.proposal.conclusion.value,
            "confidence": context.proposal.confidence,
            "thesis": context.proposal.thesis,
            "supporting_hypothesis_ids": list(
                context.proposal.supporting_hypothesis_ids
            ),
            "rejected_hypothesis_ids": list(context.proposal.rejected_hypothesis_ids),
        },
        "risk_review": {
            "risk_review_id": context.risk.risk_review_id,
            "verdict": context.risk.verdict.value,
            "final_conclusion": context.risk.final_conclusion.value,
            "final_confidence": context.risk.final_confidence,
            "reasons": list(context.risk.reasons),
        },
        "reports": [
            {
                "report_id": report.report_id,
                "skill_id": report.source,
                "role": report.role.value,
                "summary": report.summary,
                "stance": report.stance,
                "confidence": report.confidence,
                "evidence_ids": list(report.evidence_ids),
                "raw_reference": report.raw_reference,
            }
            for report in context.reports
        ],
        "hypotheses": [
            {
                "hypothesis_id": hypothesis.hypothesis_id,
                "statement": hypothesis.statement,
                "direction": hypothesis.direction,
                "confidence": hypothesis.confidence,
                "supporting_report_ids": list(hypothesis.supporting_report_ids),
                "supporting_evidence_ids": list(hypothesis.supporting_evidence_ids),
            }
            for hypothesis in context.hypotheses
        ],
        "evidence": [
            {
                "evidence_id": evidence.evidence_id,
                "evidence_type": evidence.evidence_type,
                "source": evidence.source,
                "summary": evidence.summary,
                "reliability": evidence.reliability,
            }
            for evidence in context.evidence
        ],
        "source_refs": _source_refs(settlement, context),
        "constraints": {
            "max_abs_skill_weight_delta": str(MAX_SKILL_WEIGHT_DELTA),
            "proposal_status": "pending_approval",
            "do_not_apply_weights": True,
        },
        "required_response_shape": {
            "cause_summary": "string",
            "evidence_references": ["evidence_id"],
            "report_references": ["report_id"],
            "skill_weight_adjustments": [
                {
                    "skill_id": "string",
                    "report_id": "report_id",
                    "delta": "decimal string between -0.05 and 0.05",
                    "reason": "string",
                }
            ],
            "learning_recommendations": ["string"],
        },
    }


def _llm_audit(result: LLMStructuredResult) -> dict[str, object]:
    return {
        "provider": result.provider,
        "model": result.model,
        "request_id": result.request_id,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens,
        "latency_ms": result.latency_ms,
        "raw_finish_reason": result.raw_finish_reason,
        "extracted_payload": result.extracted_payload,
    }


def _skill_weight_adjustments(
    settlement: DecisionSettlementResult,
    context: _ResearchContext,
    advice: Brain005LearningAdvice | None,
) -> list[dict[str, str]]:
    report_by_id = {report.report_id: report for report in context.reports}
    if advice is not None:
        adjustments = [
            _bounded_adjustment(item, report_by_id)
            for item in advice.skill_weight_adjustments
            if item.report_id in report_by_id
        ]
        if adjustments:
            return adjustments
    return _default_skill_weight_adjustments(settlement, context, report_by_id)


def _bounded_adjustment(
    item: SkillWeightAdjustmentAdvice,
    report_by_id: dict[str, AgentReport],
) -> dict[str, str]:
    report = report_by_id[item.report_id]
    delta = max(
        -MAX_SKILL_WEIGHT_DELTA,
        min(MAX_SKILL_WEIGHT_DELTA, item.delta),
    )
    return {
        "skill_id": item.skill_id or report.source,
        "report_id": item.report_id,
        "delta": str(delta),
        "reason": item.reason,
    }


def _default_skill_weight_adjustments(
    settlement: DecisionSettlementResult,
    context: _ResearchContext,
    report_by_id: dict[str, AgentReport],
) -> list[dict[str, str]]:
    adjustments: list[dict[str, str]] = []
    stronger = set(_stronger_report_ids(settlement.evaluation, context))
    weaker = set(_weaker_report_ids(settlement.evaluation, context))
    for report_id in context.assembly.report_ids:
        report = report_by_id[report_id]
        if report_id in stronger:
            adjustments.append(
                {
                    "skill_id": report.source,
                    "report_id": report_id,
                    "delta": str(DEFAULT_SKILL_WEIGHT_DELTA),
                    "reason": (
                        "settlement passed; supported report is eligible for a "
                        "small increase"
                    ),
                }
            )
        elif report_id in weaker:
            adjustments.append(
                {
                    "skill_id": report.source,
                    "report_id": report_id,
                    "delta": str(-DEFAULT_SKILL_WEIGHT_DELTA),
                    "reason": (
                        "settlement did not pass; denied report is eligible for a "
                        "small decrease"
                    ),
                }
            )
    return adjustments


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
