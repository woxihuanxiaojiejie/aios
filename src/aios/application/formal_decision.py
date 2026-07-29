from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from aios.kernel.brain002 import SkillExecution, SkillResult
from aios.kernel.brain003 import DiscussionResult
from aios.kernel.brain004 import DecisionResult
from aios.kernel.debate import RiskReview
from aios.kernel.decision import STABLE_UNAVAILABLE_FIELDS, TRADEABLE_ACTIONS, Decision
from aios.kernel.enums import (
    Action,
    DecisionDirection,
    ExperimentStatus,
    RiskVerdict,
)
from aios.kernel.errors import ReferenceIntegrityError, StorageOperationError
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.research import ResearchSession
from aios.workflows.decision_lifecycle import DecisionLifecycleService

TRADEABLE_DIRECTIONS = frozenset({DecisionDirection.BULLISH, DecisionDirection.BEARISH})


class FormalDecisionService:
    """Assemble and persist BRAIN formal Decisions from DecisionResult + RiskReview."""

    def __init__(self, *, lifecycle: DecisionLifecycleService) -> None:
        self._lifecycle = lifecycle
        self._storage = lifecycle.storage

    def assemble(
        self,
        *,
        session: ResearchSession,
        decision_result: DecisionResult,
        risk_review: RiskReview,
        discussion_result: DiscussionResult,
        skill_results: tuple[SkillResult, ...],
        evidence: tuple[Evidence, ...],
        model: str,
        provider: str,
    ) -> Decision:
        existing = self._storage.get_decision_by_decision_result_id(
            decision_result.decision_result_id
        )
        if existing is not None:
            return existing

        latest_session = self._storage.get(
            ResearchSession,
            session.research_session_id,
        )
        self._validate_references(
            session=latest_session,
            decision_result=decision_result,
            risk_review=risk_review,
            discussion_result=discussion_result,
            skill_results=skill_results,
            evidence=evidence,
        )
        decision = self._build_decision(
            session=latest_session,
            decision_result=decision_result,
            risk_review=risk_review,
            skill_results=skill_results,
            evidence=evidence,
            model=model,
            provider=provider,
        )
        try:
            return self._lifecycle.create_decision(decision)
        except StorageOperationError:
            concurrent = self._storage.get_decision_by_decision_result_id(
                decision_result.decision_result_id
            )
            if concurrent is not None:
                return concurrent
            raise

    def _validate_references(
        self,
        *,
        session: ResearchSession,
        decision_result: DecisionResult,
        risk_review: RiskReview,
        discussion_result: DiscussionResult,
        skill_results: tuple[SkillResult, ...],
        evidence: tuple[Evidence, ...],
    ) -> None:
        if risk_review.research_session_id != session.research_session_id:
            msg = "RiskReview must belong to the supplied ResearchSession"
            raise ReferenceIntegrityError(msg)
        if risk_review.decision_result_id != decision_result.decision_result_id:
            msg = "RiskReview must reference the supplied DecisionResult"
            raise ReferenceIntegrityError(msg)
        if risk_review.discussion_result_id != discussion_result.discussion_result_id:
            msg = "RiskReview must reference the supplied DiscussionResult"
            raise ReferenceIntegrityError(msg)
        if (
            decision_result.discussion_result_id
            != discussion_result.discussion_result_id
        ):
            msg = "DecisionResult must reference the supplied DiscussionResult"
            raise ReferenceIntegrityError(msg)

        skill_result_ids = tuple(result.result_id for result in skill_results)
        if set(skill_result_ids) != set(decision_result.skill_result_ids):
            msg = "DecisionResult SkillResult IDs must match supplied SkillResults"
            raise ReferenceIntegrityError(msg)
        if set(risk_review.skill_result_ids) != set(skill_result_ids):
            msg = "RiskReview SkillResult IDs must match supplied SkillResults"
            raise ReferenceIntegrityError(msg)

        evidence_ids = tuple(item.evidence_id for item in evidence)
        self._validate_ids("Evidence", evidence_ids, session.evidence_ids)
        self._validate_ids(
            "DecisionResult evidence_refs",
            decision_result.evidence_refs,
            evidence_ids,
        )
        self._validate_ids(
            "RiskReview evidence_ids",
            risk_review.evidence_ids,
            evidence_ids,
        )
        for result in skill_results:
            execution = self._storage.get(SkillExecution, result.execution_id)
            if execution.task_id != decision_result.task_id:
                msg = "SkillResult execution task_id must match DecisionResult task_id"
                raise ReferenceIntegrityError(msg)
            self._validate_ids(
                f"SkillResult {result.result_id} supporting evidence",
                result.supporting_evidence_ids,
                evidence_ids,
            )
            self._validate_ids(
                f"SkillResult {result.result_id} contradicting evidence",
                result.contradicting_evidence_ids,
                evidence_ids,
            )

    def _validate_ids(
        self,
        label: str,
        referenced: Iterable[str],
        allowed: Iterable[str],
    ) -> None:
        unknown = set(referenced) - set(allowed)
        if unknown:
            msg = f"{label} references unknown IDs: {', '.join(sorted(unknown))}"
            raise ReferenceIntegrityError(msg)

    def _build_decision(
        self,
        *,
        session: ResearchSession,
        decision_result: DecisionResult,
        risk_review: RiskReview,
        skill_results: tuple[SkillResult, ...],
        evidence: tuple[Evidence, ...],
        model: str,
        provider: str,
    ) -> Decision:
        original_direction = decision_result.direction
        direction = _final_direction(decision_result, risk_review)
        confidence = _confidence(decision_result, risk_review)
        entry_conditions = tuple(item.reason for item in decision_result.reasoning)
        invalidation_conditions = tuple(
            item.invalid_condition for item in decision_result.risks
        )
        stop_loss: float | None = None
        condition_entry, condition_invalid, stop_loss = _condition_changes(
            risk_review.condition_changes
        )
        entry_conditions = tuple(dict.fromkeys((*entry_conditions, *condition_entry)))
        invalidation_conditions = tuple(
            dict.fromkeys((*invalidation_conditions, *condition_invalid))
        )
        position_suggestion = (
            risk_review.adjusted_position
            if risk_review.verdict is RiskVerdict.REDUCE_POSITION
            else None
        )
        trade_defaults = _trade_defaults(decision_result.action, direction, evidence)
        target_range = trade_defaults.target_range
        expected_return = trade_defaults.expected_return
        max_expected_loss = trade_defaults.max_expected_loss
        if trade_defaults.entry_price is not None:
            entry_conditions = (
                str(trade_defaults.entry_price),
                *entry_conditions,
            )
        if stop_loss is None:
            stop_loss = trade_defaults.stop_loss
        if position_suggestion is None:
            position_suggestion = trade_defaults.position_suggestion
        risk_factors = tuple(
            dict.fromkeys(
                (
                    *(item.risk for item in decision_result.risks),
                    *(
                        factor
                        for result in skill_results
                        for factor in result.risk_factors
                    ),
                )
            )
        )
        supporting_skill_ids = tuple(decision_result.supporting_skills)
        dissenting_opinions = tuple(
            dict.fromkeys(
                (
                    *decision_result.opposing_skills,
                    *risk_review.opposing_arguments,
                )
            )
        )
        unavailable_fields = _unavailable_fields(
            direction=direction,
            entry_conditions=entry_conditions,
            target_range=target_range,
            stop_loss=stop_loss,
            invalidation_conditions=invalidation_conditions,
            position_suggestion=position_suggestion,
            expected_return=expected_return,
            max_expected_loss=max_expected_loss,
            supporting_skill_ids=supporting_skill_ids,
            risk_factors=risk_factors,
            planned_settlement_at=session.scope.valid_until,
        )
        downgrade_reasons = _downgrade_reasons(risk_review, unavailable_fields)
        if unavailable_fields or risk_review.verdict is RiskVerdict.VETO:
            direction = DecisionDirection.NO_TRADE
            action = Action.NO_TRADE
        else:
            action = decision_result.action

        experiment = Experiment(
            name=f"brain-formal-decision-{session.research_session_id}",
            model=model,
            prompt_version="brain-formal-decision-v1",
            agent_config_version="brain001-005",
            dataset_snapshot=f"research-session:{session.research_session_id}",
            evidence_ids=tuple(decision_result.evidence_refs),
            parameters={
                "provider": provider,
                "decision_result_id": decision_result.decision_result_id,
                "risk_review_id": risk_review.risk_review_id,
            },
            status=ExperimentStatus.FINISHED,
            started_at=session.scope.as_of,
            finished_at=session.scope.as_of,
            created_at=session.scope.as_of,
        )
        self._storage.save(experiment)
        return Decision(
            experiment_id=experiment.experiment_id,
            symbol=session.scope.symbol,
            action=action,
            horizon=f"{session.scope.horizon_days}d",
            confidence=confidence,
            expected_return=expected_return,
            max_expected_loss=max_expected_loss,
            evidence_ids=tuple(decision_result.evidence_refs),
            reasoning_summary=_summary(decision_result, risk_review, downgrade_reasons),
            created_at=session.scope.as_of,
            valid_until=session.scope.valid_until,
            research_session_id=session.research_session_id,
            decision_result_id=decision_result.decision_result_id,
            risk_review_id=risk_review.risk_review_id,
            direction=direction,
            original_direction=original_direction,
            target_range=target_range,
            entry_conditions=entry_conditions,
            invalidation_conditions=invalidation_conditions,
            stop_loss=stop_loss,
            position_suggestion=position_suggestion,
            risk_factors=risk_factors,
            supporting_skill_ids=supporting_skill_ids,
            dissenting_opinions=dissenting_opinions,
            generated_at=session.scope.as_of,
            planned_settlement_at=session.scope.valid_until,
            unavailable_fields=unavailable_fields,
            downgrade_reasons=downgrade_reasons,
        )


class _TradeDefaults:
    def __init__(
        self,
        *,
        entry_price: Decimal | None,
        target_range: tuple[float, float] | None,
        stop_loss: float | None,
        position_suggestion: float | None,
        expected_return: float | None,
        max_expected_loss: float | None,
    ) -> None:
        self.entry_price = entry_price
        self.target_range = target_range
        self.stop_loss = stop_loss
        self.position_suggestion = position_suggestion
        self.expected_return = expected_return
        self.max_expected_loss = max_expected_loss


def _trade_defaults(
    action: Action,
    direction: DecisionDirection,
    evidence: tuple[Evidence, ...],
) -> _TradeDefaults:
    if action not in TRADEABLE_ACTIONS or direction not in TRADEABLE_DIRECTIONS:
        return _empty_trade_defaults()
    close = _latest_market_close(evidence)
    if close is None:
        return _empty_trade_defaults()
    if direction is DecisionDirection.BEARISH:
        target = close * Decimal("0.97")
        stop = close * Decimal("1.02")
    else:
        target = close * Decimal("1.03")
        stop = close * Decimal("0.98")
    return _TradeDefaults(
        entry_price=close,
        target_range=(float(target), float(target)),
        stop_loss=float(stop),
        position_suggestion=0.25,
        expected_return=0.03,
        max_expected_loss=0.02,
    )


def _empty_trade_defaults() -> _TradeDefaults:
    return _TradeDefaults(
        entry_price=None,
        target_range=None,
        stop_loss=None,
        position_suggestion=None,
        expected_return=None,
        max_expected_loss=None,
    )


def _latest_market_close(evidence: tuple[Evidence, ...]) -> Decimal | None:
    market_evidence = [
        item
        for item in evidence
        if item.evidence_type == "market_daily_bar"
        and isinstance(item.metadata.get("market_bar"), dict)
    ]
    if not market_evidence:
        return None
    latest = max(market_evidence, key=lambda item: item.published_at)
    market_bar = latest.metadata["market_bar"]
    close = market_bar.get("close")
    if close is None:
        return None
    return Decimal(str(close))


def _final_direction(
    decision_result: DecisionResult,
    risk_review: RiskReview,
) -> DecisionDirection:
    if risk_review.verdict is RiskVerdict.VETO or risk_review.converted_to_no_trade:
        return DecisionDirection.NO_TRADE
    return decision_result.direction


def _confidence(decision_result: DecisionResult, risk_review: RiskReview) -> float:
    if risk_review.verdict is RiskVerdict.REDUCE_CONFIDENCE:
        return min(
            1.0,
            max(0.0, decision_result.confidence + (risk_review.confidence_delta or 0)),
        )
    return min(1.0, max(0.0, risk_review.final_confidence))


def _condition_changes(
    changes: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...], float | None]:
    entries: list[str] = []
    invalidations: list[str] = []
    stop_loss: float | None = None
    for change in changes:
        label, separator, value = change.partition(":")
        if not separator:
            entries.append(change)
            continue
        normalized = value.strip()
        if label.strip() == "entry":
            entries.append(normalized)
        elif label.strip() == "invalidation":
            invalidations.append(normalized)
        elif label.strip() == "stop_loss":
            stop_loss = float(normalized)
        else:
            entries.append(change)
    return tuple(entries), tuple(invalidations), stop_loss


def _unavailable_fields(
    *,
    direction: DecisionDirection,
    entry_conditions: tuple[str, ...],
    target_range: tuple[float, float] | None,
    stop_loss: float | None,
    invalidation_conditions: tuple[str, ...],
    position_suggestion: float | None,
    expected_return: float | None,
    max_expected_loss: float | None,
    supporting_skill_ids: tuple[str, ...],
    risk_factors: tuple[str, ...],
    planned_settlement_at: object,
) -> tuple[str, ...]:
    if direction not in TRADEABLE_DIRECTIONS:
        return ()
    missing: list[str] = []
    checks = {
        "entry_conditions": bool(entry_conditions),
        "target_range": target_range is not None,
        "stop_loss": stop_loss is not None or bool(invalidation_conditions),
        "position_suggestion": position_suggestion is not None,
        "expected_return": expected_return is not None,
        "max_expected_loss": max_expected_loss is not None,
        "supporting_skill_ids": bool(supporting_skill_ids),
        "risk_factors": bool(risk_factors),
        "planned_settlement_at": planned_settlement_at is not None,
    }
    for field_name, available in checks.items():
        if not available:
            missing.append(field_name)
    return tuple(field for field in missing if field in STABLE_UNAVAILABLE_FIELDS)


def _downgrade_reasons(
    risk_review: RiskReview,
    unavailable_fields: tuple[str, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if risk_review.verdict is RiskVerdict.VETO:
        reasons.append("risk_review_veto")
    elif risk_review.verdict is RiskVerdict.REDUCE_CONFIDENCE:
        reasons.append("risk_review_reduce_confidence")
    elif risk_review.verdict is RiskVerdict.REDUCE_POSITION:
        reasons.append("risk_review_reduce_position")
    elif risk_review.verdict is RiskVerdict.MODIFY_CONDITIONS:
        reasons.append("risk_review_modify_conditions")
    if unavailable_fields:
        reasons.append("tradeable_fields_unavailable")
    return tuple(dict.fromkeys(reasons))


def _summary(
    decision_result: DecisionResult,
    risk_review: RiskReview,
    downgrade_reasons: tuple[str, ...],
) -> str:
    pieces = [
        decision_result.decision_summary,
        f"RiskReview: {risk_review.verdict.value}",
    ]
    if downgrade_reasons:
        pieces.append(f"Downgrade reasons: {', '.join(downgrade_reasons)}")
    return " ".join(pieces)
