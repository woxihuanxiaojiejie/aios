from __future__ import annotations

from collections.abc import Iterable

from aios.adapters.storage import Storage
from aios.kernel.brain002 import SkillExecution, SkillResult
from aios.kernel.brain003 import DiscussionResult
from aios.kernel.brain004 import DecisionResult
from aios.kernel.debate import RiskReview
from aios.kernel.enums import Action, ResearchConclusion, RiskVerdict
from aios.kernel.errors import ReferenceIntegrityError, StorageOperationError
from aios.kernel.evidence import Evidence
from aios.kernel.research import ResearchSession


class RiskReviewService:
    """BRAIN-native gate between DecisionResult and formal Decision creation."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def submit_brain_risk_review(
        self,
        *,
        session: ResearchSession,
        decision_result: DecisionResult,
        discussion_result: DiscussionResult,
        skill_results: tuple[SkillResult, ...],
        evidence: tuple[Evidence, ...],
        verdict: RiskVerdict = RiskVerdict.APPROVE,
        confidence_delta: float | None = None,
        adjusted_position: float | None = None,
        condition_changes: tuple[str, ...] | list[str] = (),
        reasons: tuple[str, ...] | list[str] = (),
        supporting_arguments: tuple[str, ...] | list[str] = (),
        opposing_arguments: tuple[str, ...] | list[str] = (),
    ) -> RiskReview:
        existing = self._storage.get_risk_review_by_decision_result_id(
            decision_result.decision_result_id
        )
        if existing is not None:
            return existing
        latest_session = self._storage.get(
            ResearchSession,
            session.research_session_id,
        )

        self._validate_chain(
            session=latest_session,
            decision_result=decision_result,
            discussion_result=discussion_result,
            skill_results=skill_results,
            evidence=evidence,
        )
        review = RiskReview(
            proposal_id=None,
            verdict=verdict,
            final_conclusion=_final_conclusion(decision_result.action, verdict),
            final_confidence=_final_confidence(
                decision_result.confidence,
                verdict,
                confidence_delta,
            ),
            reasons=tuple(reasons) or _default_reasons(decision_result),
            confidence_delta=_normalized_delta(verdict, confidence_delta),
            adjusted_position=adjusted_position,
            condition_changes=tuple(condition_changes),
            converted_to_no_trade=verdict is RiskVerdict.VETO,
            research_session_id=latest_session.research_session_id,
            decision_result_id=decision_result.decision_result_id,
            discussion_result_id=discussion_result.discussion_result_id,
            skill_result_ids=tuple(result.result_id for result in skill_results),
            evidence_ids=tuple(item.evidence_id for item in evidence),
            supporting_arguments=tuple(supporting_arguments)
            or tuple(decision_result.supporting_skills),
            opposing_arguments=tuple(opposing_arguments)
            or tuple(decision_result.opposing_skills),
            created_at=latest_session.scope.as_of,
        )
        try:
            self._storage.save(review)
        except StorageOperationError:
            concurrent = self._storage.get_risk_review_by_decision_result_id(
                decision_result.decision_result_id
            )
            if concurrent is not None:
                return concurrent
            raise
        return review

    def _validate_chain(
        self,
        *,
        session: ResearchSession,
        decision_result: DecisionResult,
        discussion_result: DiscussionResult,
        skill_results: tuple[SkillResult, ...],
        evidence: tuple[Evidence, ...],
    ) -> None:
        if (
            decision_result.discussion_result_id
            != discussion_result.discussion_result_id
        ):
            msg = "DecisionResult must reference the supplied DiscussionResult"
            raise ReferenceIntegrityError(msg)
        if decision_result.task_id != discussion_result.task_id:
            msg = "DecisionResult task_id must match DiscussionResult task_id"
            raise ReferenceIntegrityError(msg)

        skill_result_ids = tuple(result.result_id for result in skill_results)
        if set(skill_result_ids) != set(decision_result.skill_result_ids):
            msg = "DecisionResult SkillResult IDs must match supplied SkillResults"
            raise ReferenceIntegrityError(msg)
        if not set(discussion_result.skill_result_ids).issubset(set(skill_result_ids)):
            msg = "DiscussionResult SkillResult IDs must be supplied"
            raise ReferenceIntegrityError(msg)

        for result in skill_results:
            execution = self._storage.get(SkillExecution, result.execution_id)
            if execution.task_id != decision_result.task_id:
                msg = "SkillResult execution task_id must match DecisionResult task_id"
                raise ReferenceIntegrityError(msg)

        evidence_ids = tuple(item.evidence_id for item in evidence)
        self._validate_ids("Evidence", evidence_ids, session.evidence_ids)
        self._validate_ids(
            "DecisionResult evidence_refs",
            decision_result.evidence_refs,
            evidence_ids,
        )
        for result in skill_results:
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


def _final_conclusion(action: Action, verdict: RiskVerdict) -> ResearchConclusion:
    if verdict is RiskVerdict.VETO:
        return ResearchConclusion.NO_TRADE
    return {
        Action.BUY: ResearchConclusion.BUY,
        Action.SELL: ResearchConclusion.SELL,
        Action.HOLD: ResearchConclusion.HOLD,
        Action.OBSERVE: ResearchConclusion.WATCH,
        Action.NO_TRADE: ResearchConclusion.NO_TRADE,
    }[action]


def _final_confidence(
    confidence: float,
    verdict: RiskVerdict,
    confidence_delta: float | None,
) -> float:
    if verdict is RiskVerdict.VETO:
        return 0.0
    return max(0.0, confidence + (_normalized_delta(verdict, confidence_delta) or 0.0))


def _normalized_delta(
    verdict: RiskVerdict,
    confidence_delta: float | None,
) -> float | None:
    if verdict in {RiskVerdict.REDUCE_CONFIDENCE, RiskVerdict.DOWNGRADE}:
        return confidence_delta if confidence_delta is not None else -0.1
    return confidence_delta


def _default_reasons(decision_result: DecisionResult) -> tuple[str, ...]:
    return tuple(item.risk for item in decision_result.risks) or (
        "BRAIN risk review completed",
    )
