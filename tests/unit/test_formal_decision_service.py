from __future__ import annotations

from datetime import timedelta

import pytest
from tests.factories import fixed_now, make_evidence, make_research_session
from tests.unit.test_brain004_persistence import decision_execution
from tests.unit.test_brain004_persistence import decision_result as make_decision_result

from aios.application.formal_decision import FormalDecisionService
from aios.kernel.brain002 import SkillExecution, SkillResult
from aios.kernel.brain003 import DiscussionExecution, DiscussionResult
from aios.kernel.debate import RiskReview
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    Action,
    DecisionDirection,
    ResearchConclusion,
    RiskVerdict,
    SkillDirection,
    SkillExecutionStatus,
)
from aios.kernel.errors import ReferenceIntegrityError, StorageOperationError
from aios.storage.memory import InMemoryStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService


def test_formal_decision_approve_downgrades_incomplete_tradeable_decision() -> None:
    storage, session, evidence, skill_result, discussion, decision_result, risk = (
        _seed_chain(RiskVerdict.APPROVE)
    )

    decision = FormalDecisionService(
        lifecycle=DecisionLifecycleService(storage)
    ).assemble(
        session=session,
        decision_result=decision_result,
        risk_review=risk,
        discussion_result=discussion,
        skill_results=(skill_result,),
        evidence=(evidence,),
        model="fake-model",
        provider="fake",
    )

    assert decision.action is Action.NO_TRADE
    assert decision.direction is DecisionDirection.NO_TRADE
    assert decision.original_direction is DecisionDirection.BULLISH
    assert decision.confidence == decision_result.confidence
    assert decision.expected_return is None
    assert decision.max_expected_loss is None
    assert "target_range" in decision.unavailable_fields
    assert "position_suggestion" in decision.unavailable_fields
    assert "tradeable_fields_unavailable" in decision.downgrade_reasons


def test_reduce_confidence_clamps_confidence_and_records_reason() -> None:
    storage, session, evidence, skill_result, discussion, decision_result, risk = (
        _seed_chain(RiskVerdict.REDUCE_CONFIDENCE, confidence_delta=-1.0)
    )

    decision = FormalDecisionService(
        lifecycle=DecisionLifecycleService(storage)
    ).assemble(
        session=session,
        decision_result=decision_result,
        risk_review=risk,
        discussion_result=discussion,
        skill_results=(skill_result,),
        evidence=(evidence,),
        model="fake-model",
        provider="fake",
    )

    assert decision.confidence == 0.0
    assert "risk_review_reduce_confidence" in decision.downgrade_reasons


def test_reduce_position_maps_adjusted_position_without_trade_plan() -> None:
    storage, session, evidence, skill_result, discussion, decision_result, risk = (
        _seed_chain(RiskVerdict.REDUCE_POSITION, adjusted_position=0.25)
    )

    decision = FormalDecisionService(
        lifecycle=DecisionLifecycleService(storage)
    ).assemble(
        session=session,
        decision_result=decision_result,
        risk_review=risk,
        discussion_result=discussion,
        skill_results=(skill_result,),
        evidence=(evidence,),
        model="fake-model",
        provider="fake",
    )

    assert decision.position_suggestion == 0.25
    assert "position_suggestion" not in decision.unavailable_fields


def test_modify_conditions_merges_changes_deterministically() -> None:
    storage, session, evidence, skill_result, discussion, decision_result, risk = (
        _seed_chain(
            RiskVerdict.MODIFY_CONDITIONS,
            condition_changes=(
                "entry: wait for volume confirmation",
                "invalidation: closes below support",
                "stop_loss: 92.5",
            ),
        )
    )

    decision = FormalDecisionService(
        lifecycle=DecisionLifecycleService(storage)
    ).assemble(
        session=session,
        decision_result=decision_result,
        risk_review=risk,
        discussion_result=discussion,
        skill_results=(skill_result,),
        evidence=(evidence,),
        model="fake-model",
        provider="fake",
    )

    assert "wait for volume confirmation" in decision.entry_conditions
    assert "closes below support" in decision.invalidation_conditions
    assert decision.stop_loss == 92.5


def test_veto_converts_to_no_trade_and_preserves_original_direction() -> None:
    storage, session, evidence, skill_result, discussion, decision_result, risk = (
        _seed_chain(RiskVerdict.VETO)
    )

    decision = FormalDecisionService(
        lifecycle=DecisionLifecycleService(storage)
    ).assemble(
        session=session,
        decision_result=decision_result,
        risk_review=risk,
        discussion_result=discussion,
        skill_results=(skill_result,),
        evidence=(evidence,),
        model="fake-model",
        provider="fake",
    )

    assert decision.action is Action.NO_TRADE
    assert decision.direction is DecisionDirection.NO_TRADE
    assert decision.original_direction is DecisionDirection.BULLISH
    assert "risk_review_veto" in decision.downgrade_reasons


def test_unavailable_fields_reject_natural_language() -> None:
    with pytest.raises(ValueError, match="unavailable_fields"):
        Decision(
            experiment_id="ex_00000000-0000-0000-0000-000000000001",
            symbol="600519",
            action=Action.NO_TRADE,
            horizon="3d",
            confidence=0.5,
            expected_return=None,
            max_expected_loss=None,
            evidence_ids=("ev_00000000-0000-0000-0000-000000000001",),
            reasoning_summary="summary",
            valid_until=fixed_now() + timedelta(days=3),
            unavailable_fields=("target price was not available",),
        )


def test_reference_objects_must_belong_to_current_session() -> None:
    storage, session, evidence, skill_result, discussion, decision_result, risk = (
        _seed_chain(RiskVerdict.APPROVE)
    )
    foreign = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000099",
        created_at=fixed_now() + timedelta(minutes=1),
    )
    storage.save(foreign)

    with pytest.raises(ReferenceIntegrityError, match="Evidence"):
        FormalDecisionService(lifecycle=DecisionLifecycleService(storage)).assemble(
            session=session,
            decision_result=decision_result,
            risk_review=risk,
            discussion_result=discussion,
            skill_results=(skill_result,),
            evidence=(evidence, foreign),
            model="fake-model",
            provider="fake",
        )


def test_repeated_execution_returns_existing_decision() -> None:
    storage, session, evidence, skill_result, discussion, decision_result, risk = (
        _seed_chain(RiskVerdict.APPROVE)
    )
    service = FormalDecisionService(lifecycle=DecisionLifecycleService(storage))

    first = service.assemble(
        session=session,
        decision_result=decision_result,
        risk_review=risk,
        discussion_result=discussion,
        skill_results=(skill_result,),
        evidence=(evidence,),
        model="fake-model",
        provider="fake",
    )
    replay = service.assemble(
        session=session,
        decision_result=decision_result,
        risk_review=risk,
        discussion_result=discussion,
        skill_results=(skill_result,),
        evidence=(evidence,),
        model="fake-model",
        provider="fake",
    )

    assert replay.decision_id == first.decision_id


def test_concurrent_unique_conflict_returns_existing_decision() -> None:
    storage, session, evidence, skill_result, discussion, decision_result, risk = (
        _seed_chain(RiskVerdict.APPROVE)
    )
    concurrent = ConcurrentDecisionStorage()
    for entity_type in (
        type(evidence),
        type(session),
        SkillExecution,
        SkillResult,
        DiscussionExecution,
        DiscussionResult,
        type(decision_result),
        RiskReview,
    ):
        for entity in storage.list(entity_type):
            concurrent.save(entity)

    decision = FormalDecisionService(
        lifecycle=DecisionLifecycleService(concurrent)
    ).assemble(
        session=session,
        decision_result=decision_result,
        risk_review=risk,
        discussion_result=discussion,
        skill_results=(skill_result,),
        evidence=(evidence,),
        model="fake-model",
        provider="fake",
    )

    assert decision.decision_id == concurrent.concurrent_decision_id


class ConcurrentDecisionStorage(InMemoryStorage):
    concurrent_decision_id = "dc_00000000-0000-0000-0000-000000000099"

    def save(self, entity: object) -> None:
        if isinstance(entity, Decision):
            super().save(
                entity.model_copy(update={"decision_id": self.concurrent_decision_id})
            )
            raise StorageOperationError("unique conflict")
        super().save(entity)


def _seed_chain(
    verdict: RiskVerdict,
    *,
    confidence_delta: float | None = None,
    adjusted_position: float | None = None,
    condition_changes: tuple[str, ...] = (),
) -> tuple[
    InMemoryStorage,
    object,
    object,
    SkillResult,
    DiscussionResult,
    object,
    RiskReview,
]:
    storage = InMemoryStorage()
    evidence = make_evidence().model_copy(update={"symbols": ("600519",)})
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
        missing_information=("target price",),
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
            "evidence_refs": (evidence.evidence_id,),
            "supporting_skills": (skill_result.skill_id,),
            "opposing_skills": (),
        }
    )
    risk = RiskReview(
        proposal_id=None,
        verdict=verdict,
        final_conclusion=ResearchConclusion.NO_TRADE
        if verdict is RiskVerdict.VETO
        else ResearchConclusion.BUY,
        final_confidence=0.0
        if verdict is RiskVerdict.VETO
        else max(0.0, decision_result.confidence + (confidence_delta or 0.0)),
        reasons=("risk reviewed",),
        confidence_delta=confidence_delta,
        adjusted_position=adjusted_position,
        condition_changes=condition_changes,
        converted_to_no_trade=verdict is RiskVerdict.VETO,
        research_session_id=session.research_session_id,
        decision_result_id=decision_result.decision_result_id,
        discussion_result_id=discussion.discussion_result_id,
        skill_result_ids=(skill_result.result_id,),
        evidence_ids=(evidence.evidence_id,),
        created_at=fixed_now(),
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
        risk,
    ):
        storage.save(entity)
    return storage, session, evidence, skill_result, discussion, decision_result, risk
