from __future__ import annotations

from datetime import timedelta

from tests.factories import fixed_now

from aios.kernel.decision import Decision
from aios.kernel.enums import Action, DecisionDirection
from aios.storage.memory import InMemoryStorage
from aios.storage.postgres.mapper import model_to_entity, to_model


def test_formal_decision_mapper_round_trips_rich_fields() -> None:
    decision = rich_decision()

    assert model_to_entity(to_model(decision)) == decision


def test_memory_storage_finds_decision_by_decision_result_id() -> None:
    storage = InMemoryStorage()
    decision = rich_decision()

    storage.save(decision)

    assert (
        storage.get_decision_by_decision_result_id(decision.decision_result_id or "")
        == decision
    )


def rich_decision() -> Decision:
    created = fixed_now()
    return Decision(
        decision_id="dc_00000000-0000-0000-0000-000000000201",
        experiment_id="ex_00000000-0000-0000-0000-000000000001",
        symbol="600519",
        action=Action.NO_TRADE,
        horizon="3d",
        confidence=0.4,
        expected_return=None,
        max_expected_loss=None,
        evidence_ids=("ev_00000000-0000-0000-0000-000000000001",),
        reasoning_summary="no trade because rich fields are unavailable",
        created_at=created,
        valid_until=created + timedelta(days=3),
        research_session_id="rs_00000000-0000-0000-0000-000000000001",
        decision_result_id="ds_00000000-0000-0000-0000-000000000001",
        risk_review_id="rr_00000000-0000-0000-0000-000000000001",
        direction=DecisionDirection.NO_TRADE,
        original_direction=DecisionDirection.BULLISH,
        entry_conditions=("entry confirmed by evidence",),
        invalidation_conditions=("break support",),
        stop_loss=None,
        position_suggestion=0.25,
        risk_factors=("event risk",),
        supporting_skill_ids=("technical_trend",),
        dissenting_opinions=("announcement_risk",),
        market_regime="risk_on",
        generated_at=created,
        planned_settlement_at=created + timedelta(days=3),
        unavailable_fields=("target_range", "expected_return", "max_expected_loss"),
        downgrade_reasons=("tradeable_fields_unavailable",),
    )
