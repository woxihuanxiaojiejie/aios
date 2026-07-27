from __future__ import annotations

from datetime import timedelta

from tests.factories import fixed_now, make_decision, make_evidence, make_experiment

from aios.application.trade_plan import TradePlanService
from aios.kernel.decision import Decision
from aios.kernel.enums import Action, DecisionDirection, TradePlanStatus
from aios.kernel.settlement import DecisionOutcome
from aios.kernel.trade_plan import TradePlan
from aios.storage.memory import InMemoryStorage
from aios.storage.postgres.mapper import model_to_entity, to_model
from aios.workflows.decision_lifecycle import DecisionLifecycleService


def test_trade_plan_mapper_round_trips_all_fields() -> None:
    plan = _ready_trade_plan()

    assert model_to_entity(to_model(plan)) == plan


def test_ready_decision_maps_to_ready_trade_plan_without_fabrication() -> None:
    storage = _storage_with_decision(_ready_decision())

    plan = TradePlanService(DecisionLifecycleService(storage)).create_from_decision(
        "dc_00000000-0000-0000-0000-000000000001"
    )

    assert plan.status is TradePlanStatus.READY
    assert plan.direction is DecisionDirection.BULLISH
    assert plan.planned_entry == ("close above 10",)
    assert plan.target == (12.0, 13.0)
    assert plan.stop_loss == 9.25
    assert plan.planned_position == 0.25
    assert plan.unavailable_fields == ()
    assert plan.no_trade_reasons == ()
    assert storage.get_decision_outcome_by_decision_id(plan.decision_id) is None
    assert storage.list(DecisionOutcome) == []


def test_no_trade_decision_maps_to_no_trade_without_trade_fields() -> None:
    storage = _storage_with_decision(_no_trade_decision())

    plan = TradePlanService(DecisionLifecycleService(storage)).create_from_decision(
        "dc_00000000-0000-0000-0000-000000000001"
    )

    assert plan.status is TradePlanStatus.NO_TRADE
    assert plan.planned_entry == ()
    assert plan.target is None
    assert plan.stop_loss is None
    assert plan.planned_position is None
    assert plan.no_trade_reasons == ("risk review converted decision to no_trade",)


def test_tradeable_decision_missing_critical_fields_maps_to_invalid() -> None:
    storage = _storage_with_decision(_historical_incomplete_decision())

    plan = TradePlanService(DecisionLifecycleService(storage)).create_from_decision(
        "dc_00000000-0000-0000-0000-000000000001"
    )

    assert plan.status is TradePlanStatus.INVALID
    assert plan.planned_entry == ("close above 10",)
    assert plan.target is None
    assert plan.stop_loss is None
    assert plan.planned_position is None
    assert plan.unavailable_fields == (
        "target_range",
        "stop_loss",
        "invalidation_conditions",
        "position_suggestion",
    )


def test_one_decision_has_one_trade_plan_and_repeated_calls_are_idempotent() -> None:
    storage = _storage_with_decision(_ready_decision())
    service = TradePlanService(DecisionLifecycleService(storage))

    first = service.create_from_decision("dc_00000000-0000-0000-0000-000000000001")
    second = service.create_from_decision("dc_00000000-0000-0000-0000-000000000001")

    assert second == first
    assert storage.get_trade_plan_by_decision_id(first.decision_id) == first
    assert storage.list(TradePlan) == [first]


def _storage_with_decision(decision: Decision) -> InMemoryStorage:
    storage = InMemoryStorage()
    evidence = make_evidence()
    experiment = make_experiment(evidence.evidence_id)
    storage.save(evidence)
    storage.save(experiment)
    storage.save(decision)
    return storage


def _ready_decision() -> Decision:
    decision = make_decision(
        "ex_00000000-0000-0000-0000-000000000001",
        "ev_00000000-0000-0000-0000-000000000001",
    )
    return decision.model_copy(
        update={
            "research_session_id": "rs_00000000-0000-0000-0000-000000000001",
            "decision_result_id": None,
            "direction": DecisionDirection.BULLISH,
            "target_range": (12.0, 13.0),
            "entry_conditions": ("close above 10",),
            "stop_loss": 9.25,
            "invalidation_conditions": ("close below 9.25",),
            "position_suggestion": 0.25,
            "planned_settlement_at": decision.valid_until,
        }
    )


def _no_trade_decision() -> Decision:
    decision = make_decision(
        "ex_00000000-0000-0000-0000-000000000001",
        "ev_00000000-0000-0000-0000-000000000001",
    )
    return decision.model_copy(
        update={
            "action": Action.NO_TRADE,
            "direction": DecisionDirection.NO_TRADE,
            "expected_return": None,
            "max_expected_loss": None,
            "target_range": None,
            "entry_conditions": (),
            "stop_loss": None,
            "position_suggestion": None,
            "unavailable_fields": ("target_range", "position_suggestion"),
            "downgrade_reasons": ("risk review converted decision to no_trade",),
            "research_session_id": "rs_00000000-0000-0000-0000-000000000001",
        }
    )


def _historical_incomplete_decision() -> Decision:
    decision = make_decision(
        "ex_00000000-0000-0000-0000-000000000001",
        "ev_00000000-0000-0000-0000-000000000001",
    )
    return decision.model_copy(
        update={
            "direction": DecisionDirection.BULLISH,
            "entry_conditions": ("close above 10",),
            "target_range": None,
            "stop_loss": None,
            "invalidation_conditions": (),
            "position_suggestion": None,
            "research_session_id": "rs_00000000-0000-0000-0000-000000000001",
        }
    )


def _ready_trade_plan() -> TradePlan:
    created = fixed_now()
    return TradePlan(
        trade_plan_id="tp_00000000-0000-0000-0000-000000000001",
        decision_id="dc_00000000-0000-0000-0000-000000000001",
        research_session_id="rs_00000000-0000-0000-0000-000000000001",
        symbol="600519",
        direction=DecisionDirection.BULLISH,
        status=TradePlanStatus.READY,
        planned_entry=("close above 10",),
        entry_conditions=("close above 10",),
        target=(12.0, 13.0),
        stop_loss=9.25,
        invalidation_conditions=("close below 9.25",),
        planned_position=0.25,
        horizon="3d",
        expiry=created + timedelta(days=3),
        fee_model={"type": "not_specified"},
        slippage_model={"type": "not_specified"},
        unavailable_fields=(),
        no_trade_reasons=(),
        created_at=created,
        updated_at=created,
    )
