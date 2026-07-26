from __future__ import annotations

from tests.factories import fixed_now

from aios.kernel.debate import RiskReview
from aios.kernel.enums import ResearchConclusion, RiskVerdict
from aios.storage.memory import InMemoryStorage
from aios.storage.postgres.mapper import model_to_entity, to_model


def test_risk_review_mapper_round_trips_brain_fields_for_all_verdicts() -> None:
    for verdict in (
        RiskVerdict.APPROVE,
        RiskVerdict.REDUCE_CONFIDENCE,
        RiskVerdict.REDUCE_POSITION,
        RiskVerdict.MODIFY_CONDITIONS,
        RiskVerdict.VETO,
    ):
        review = _review(verdict)

        assert model_to_entity(to_model(review)) == review


def test_memory_storage_finds_brain_risk_review_by_decision_result_id() -> None:
    storage = InMemoryStorage()
    review = _review(RiskVerdict.MODIFY_CONDITIONS)

    storage.save(review)

    assert (
        storage.get_risk_review_by_decision_result_id(review.decision_result_id or "")
        == review
    )


def _review(verdict: RiskVerdict) -> RiskReview:
    return RiskReview(
        risk_review_id=f"rr_00000000-0000-0000-0000-00000000000{verdicts()[verdict]}",
        proposal_id=None,
        verdict=verdict,
        final_conclusion=ResearchConclusion.NO_TRADE
        if verdict is RiskVerdict.VETO
        else ResearchConclusion.BUY,
        final_confidence=0.0 if verdict is RiskVerdict.VETO else 0.55,
        reasons=("risk reviewed",),
        confidence_delta=-0.1,
        adjusted_position=0.25,
        condition_changes=("wait for confirmation",),
        converted_to_no_trade=verdict is RiskVerdict.VETO,
        research_session_id="rs_00000000-0000-0000-0000-000000000001",
        decision_result_id="ds_00000000-0000-0000-0000-000000000001",
        discussion_result_id="dr_00000000-0000-0000-0000-000000000001",
        skill_result_ids=("sr_00000000-0000-0000-0000-000000000001",),
        evidence_ids=("ev_00000000-0000-0000-0000-000000000001",),
        supporting_arguments=("support",),
        opposing_arguments=("oppose",),
        created_at=fixed_now(),
    )


def verdicts() -> dict[RiskVerdict, int]:
    return {
        RiskVerdict.APPROVE: 1,
        RiskVerdict.REDUCE_CONFIDENCE: 2,
        RiskVerdict.REDUCE_POSITION: 3,
        RiskVerdict.MODIFY_CONDITIONS: 4,
        RiskVerdict.VETO: 5,
    }
