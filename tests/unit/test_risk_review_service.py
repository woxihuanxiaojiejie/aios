from __future__ import annotations

from datetime import timedelta

import pytest
from tests.factories import fixed_now, make_evidence, make_research_session
from tests.unit.test_brain004_persistence import decision_execution
from tests.unit.test_brain004_persistence import decision_result as make_decision_result

from aios.application.brain_risk_review import RiskReviewService
from aios.kernel.brain002 import SkillExecution, SkillResult
from aios.kernel.brain003 import DiscussionExecution, DiscussionResult
from aios.kernel.debate import RiskReview
from aios.kernel.enums import (
    DecisionDirection,
    ResearchConclusion,
    RiskVerdict,
    SkillDirection,
    SkillExecutionStatus,
)
from aios.kernel.errors import ReferenceIntegrityError, StorageOperationError
from aios.storage.memory import InMemoryStorage


def test_risk_review_model_accepts_all_brain_verdicts_and_adjustments() -> None:
    for verdict in (
        RiskVerdict.APPROVE,
        RiskVerdict.REDUCE_CONFIDENCE,
        RiskVerdict.REDUCE_POSITION,
        RiskVerdict.MODIFY_CONDITIONS,
        RiskVerdict.VETO,
    ):
        review = RiskReview(
            proposal_id=None,
            verdict=verdict,
            final_conclusion=ResearchConclusion.NO_TRADE
            if verdict is RiskVerdict.VETO
            else ResearchConclusion.BUY,
            final_confidence=0.4,
            reasons=("risk reviewed",),
            confidence_delta=-0.2,
            adjusted_position=0.25,
            condition_changes=("wait for earnings",),
            converted_to_no_trade=verdict is RiskVerdict.VETO,
            research_session_id="rs_00000000-0000-0000-0000-000000000001",
            decision_result_id="ds_00000000-0000-0000-0000-000000000001",
            discussion_result_id="dr_00000000-0000-0000-0000-000000000001",
            skill_result_ids=("sr_00000000-0000-0000-0000-000000000001",),
            evidence_ids=("ev_00000000-0000-0000-0000-000000000001",),
            supporting_arguments=("technical trend supports buy",),
            opposing_arguments=("announcement risk remains",),
        )

        assert review.verdict is verdict


def test_veto_requires_no_trade_conversion() -> None:
    with pytest.raises(ValueError, match="veto RiskReview"):
        RiskReview(
            proposal_id=None,
            verdict=RiskVerdict.VETO,
            final_conclusion=ResearchConclusion.BUY,
            final_confidence=0.4,
            reasons=("risk reviewed",),
            converted_to_no_trade=False,
        )


def test_brain_risk_review_service_validates_references_and_is_idempotent() -> None:
    storage, session, evidence, skill_result, discussion, decision_result = (
        _seed_brain_chain()
    )

    first = RiskReviewService(storage).submit_brain_risk_review(
        session=session,
        decision_result=decision_result,
        discussion_result=discussion,
        skill_results=(skill_result,),
        evidence=(evidence,),
        verdict=RiskVerdict.REDUCE_CONFIDENCE,
        confidence_delta=-0.15,
        reasons=("risk needs lower confidence",),
        opposing_arguments=("policy uncertainty",),
    )
    replay = RiskReviewService(storage).submit_brain_risk_review(
        session=session,
        decision_result=decision_result,
        discussion_result=discussion,
        skill_results=(skill_result,),
        evidence=(evidence,),
        verdict=RiskVerdict.APPROVE,
        reasons=("would otherwise duplicate",),
    )

    assert replay.risk_review_id == first.risk_review_id
    assert first.research_session_id == session.research_session_id
    assert first.decision_result_id == decision_result.decision_result_id
    assert first.discussion_result_id == discussion.discussion_result_id
    assert first.skill_result_ids == (skill_result.result_id,)
    assert first.evidence_ids == (evidence.evidence_id,)
    assert first.confidence_delta == -0.15


def test_brain_risk_review_service_rejects_foreign_references() -> None:
    storage, session, evidence, skill_result, discussion, decision_result = (
        _seed_brain_chain()
    )
    foreign = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000099",
        created_at=fixed_now() + timedelta(minutes=2),
    )
    storage.save(foreign)

    with pytest.raises(ReferenceIntegrityError, match="Evidence"):
        RiskReviewService(storage).submit_brain_risk_review(
            session=session,
            decision_result=decision_result,
            discussion_result=discussion,
            skill_results=(skill_result,),
            evidence=(evidence, foreign),
            verdict=RiskVerdict.APPROVE,
            reasons=("bad evidence",),
        )


def test_veto_brain_review_converts_to_no_trade() -> None:
    storage, session, evidence, skill_result, discussion, decision_result = (
        _seed_brain_chain(direction=DecisionDirection.BULLISH)
    )

    review = RiskReviewService(storage).submit_brain_risk_review(
        session=session,
        decision_result=decision_result,
        discussion_result=discussion,
        skill_results=(skill_result,),
        evidence=(evidence,),
        verdict=RiskVerdict.VETO,
        reasons=("risk veto",),
    )

    assert review.converted_to_no_trade is True
    assert review.final_conclusion is ResearchConclusion.NO_TRADE


def test_brain_risk_review_service_recovers_from_concurrent_unique_conflict() -> None:
    storage, session, evidence, skill_result, discussion, decision_result = (
        _seed_brain_chain()
    )
    concurrent = ConcurrentRiskReviewStorage()
    for entity_type in (
        type(evidence),
        type(session),
        SkillExecution,
        SkillResult,
        DiscussionExecution,
        DiscussionResult,
        type(decision_result),
    ):
        for entity in storage.list(entity_type):
            concurrent.save(entity)

    review = RiskReviewService(concurrent).submit_brain_risk_review(
        session=session,
        decision_result=decision_result,
        discussion_result=discussion,
        skill_results=(skill_result,),
        evidence=(evidence,),
        verdict=RiskVerdict.APPROVE,
        reasons=("race",),
    )

    assert review.risk_review_id == concurrent.concurrent_review_id


class ConcurrentRiskReviewStorage(InMemoryStorage):
    concurrent_review_id = "rr_00000000-0000-0000-0000-000000000099"

    def save(self, entity: object) -> None:
        if isinstance(entity, RiskReview):
            super().save(
                entity.model_copy(update={"risk_review_id": self.concurrent_review_id})
            )
            raise StorageOperationError("unique conflict")
        super().save(entity)


def _seed_brain_chain(
    *,
    direction: DecisionDirection = DecisionDirection.BULLISH,
) -> tuple[
    InMemoryStorage,
    object,
    object,
    SkillResult,
    DiscussionResult,
    object,
]:
    storage = InMemoryStorage()
    evidence = make_evidence()
    session = make_research_session(evidence_ids=(evidence.evidence_id,))
    execution = SkillExecution(
        task_id="at_example",
        skill_id="technical_trend",
        skill_version="1.0.0",
        started_at=fixed_now(),
        finished_at=fixed_now(),
        status=SkillExecutionStatus.SUCCEEDED,
    )
    skill_result = SkillResult(
        result_id="sr_00000000-0000-0000-0000-000000000001",
        execution_id=execution.execution_id,
        skill_id=execution.skill_id,
        skill_version=execution.skill_version,
        conclusion="trend supports upside",
        direction=SkillDirection.BULLISH,
        confidence=0.7,
        supporting_evidence_ids=(evidence.evidence_id,),
        risk_factors=("event risk",),
        invalid_conditions=("break support",),
        missing_information=("next filing",),
        reasoning_summary="trend is constructive",
        raw_output={},
        created_at=fixed_now(),
    )
    discussion_execution = DiscussionExecution(
        task_id=execution.task_id,
        skill_result_ids=(skill_result.result_id,),
        started_at=fixed_now(),
        finished_at=fixed_now(),
        status=SkillExecutionStatus.SUCCEEDED,
    )
    discussion = DiscussionResult(
        discussion_execution_id=discussion_execution.discussion_execution_id,
        task_id=execution.task_id,
        skill_result_ids=(skill_result.result_id,),
        discussion_summary="support and opposition reviewed",
        discussion_confidence=0.65,
        created_at=fixed_now(),
    )
    dec_execution = decision_execution().model_copy(
        update={
            "task_id": execution.task_id,
            "discussion_result_id": discussion.discussion_result_id,
            "skill_result_ids": (skill_result.result_id,),
            "evidence_ids": (evidence.evidence_id,),
        }
    )
    decision_result = make_decision_result(dec_execution.decision_execution_id)
    decision_result = decision_result.model_copy(
        update={
            "task_id": execution.task_id,
            "discussion_result_id": discussion.discussion_result_id,
            "skill_result_ids": (skill_result.result_id,),
            "direction": direction,
            "evidence_refs": (evidence.evidence_id,),
            "supporting_skills": (skill_result.skill_id,),
        }
    )
    for entity in (
        evidence,
        session,
        execution,
        skill_result,
        discussion_execution,
        discussion,
        dec_execution,
        decision_result,
    ):
        storage.save(entity)
    return storage, session, evidence, skill_result, discussion, decision_result
