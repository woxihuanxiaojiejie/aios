from __future__ import annotations

from datetime import UTC, datetime

from aios.kernel.decision import TRADEABLE_ACTIONS, Decision
from aios.kernel.enums import Action, DecisionDirection, TradePlanStatus
from aios.kernel.errors import InvalidStateTransitionError, StorageOperationError
from aios.kernel.trade_plan import TradePlan
from aios.workflows.decision_lifecycle import DecisionLifecycleService

_DEFAULT_FEE_MODEL = {"type": "not_specified"}
_DEFAULT_SLIPPAGE_MODEL = {"type": "not_specified"}


class TradePlanService:
    """Create one deterministic TradePlan from one persisted formal Decision."""

    def __init__(self, lifecycle: DecisionLifecycleService) -> None:
        self._lifecycle = lifecycle
        self._storage = lifecycle.storage

    def create_from_decision(self, decision_id: str) -> TradePlan:
        existing = self._storage.get_trade_plan_by_decision_id(decision_id)
        if existing is not None:
            return existing

        decision = self._storage.get(Decision, decision_id)
        plan = self._build(decision)
        try:
            self._storage.save(plan)
            return plan
        except StorageOperationError:
            concurrent = self._storage.get_trade_plan_by_decision_id(decision_id)
            if concurrent is not None:
                return concurrent
            raise

    def get_trade_plan(self, trade_plan_id: str) -> TradePlan:
        return self._storage.get(TradePlan, trade_plan_id)

    def _build(self, decision: Decision) -> TradePlan:
        now = datetime.now(UTC)
        direction = _direction(decision)
        if decision.research_session_id is None:
            msg = "TradePlan requires Decision research_session_id"
            raise InvalidStateTransitionError(msg)
        research_session_id = decision.research_session_id
        expiry = decision.planned_settlement_at or decision.valid_until
        status = _status(decision, expiry, now)
        unavailable_fields = _missing_critical_fields(decision)
        no_trade_reasons = _no_trade_reasons(decision)
        if status is TradePlanStatus.READY and unavailable_fields:
            status = TradePlanStatus.INVALID
        planned_entry: tuple[str, ...]
        target: tuple[float, float] | None
        stop_loss: float | None
        planned_position: float | None
        if status is TradePlanStatus.NO_TRADE:
            planned_entry = ()
            target = None
            stop_loss = None
            planned_position = None
        else:
            planned_entry = decision.entry_conditions
            target = decision.target_range
            stop_loss = decision.stop_loss
            planned_position = decision.position_suggestion

        return TradePlan(
            decision_id=decision.decision_id,
            research_session_id=research_session_id,
            symbol=decision.symbol,
            direction=direction,
            status=status,
            planned_entry=planned_entry,
            entry_conditions=decision.entry_conditions,
            target=target,
            stop_loss=stop_loss,
            invalidation_conditions=decision.invalidation_conditions,
            planned_position=planned_position,
            horizon=decision.horizon,
            expiry=expiry,
            fee_model=_DEFAULT_FEE_MODEL,
            slippage_model=_DEFAULT_SLIPPAGE_MODEL,
            unavailable_fields=unavailable_fields,
            no_trade_reasons=no_trade_reasons,
            created_at=now,
            updated_at=now,
        )


def _direction(decision: Decision) -> DecisionDirection:
    if decision.direction is not None:
        return decision.direction
    if decision.action is Action.BUY:
        return DecisionDirection.BULLISH
    if decision.action is Action.SELL:
        return DecisionDirection.BEARISH
    if decision.action is Action.NO_TRADE:
        return DecisionDirection.NO_TRADE
    return DecisionDirection.NEUTRAL


def _status(
    decision: Decision,
    expiry: datetime,
    now: datetime,
) -> TradePlanStatus:
    if decision.action is Action.NO_TRADE or _direction(decision) is (
        DecisionDirection.NO_TRADE
    ):
        return TradePlanStatus.NO_TRADE
    if expiry <= now:
        return TradePlanStatus.EXPIRED
    if decision.action in TRADEABLE_ACTIONS or _direction(decision) in {
        DecisionDirection.BULLISH,
        DecisionDirection.BEARISH,
    }:
        return TradePlanStatus.READY
    return TradePlanStatus.INVALID


def _missing_critical_fields(decision: Decision) -> tuple[str, ...]:
    if decision.action is Action.NO_TRADE or _direction(decision) is (
        DecisionDirection.NO_TRADE
    ):
        return tuple(decision.unavailable_fields)
    missing = list(decision.unavailable_fields)
    if decision.research_session_id is None:
        missing.append("research_session_id")
    if _direction(decision) not in {
        DecisionDirection.BULLISH,
        DecisionDirection.BEARISH,
    }:
        missing.append("direction")
    if not decision.entry_conditions:
        missing.append("entry_conditions")
    if decision.target_range is None:
        missing.append("target_range")
    if decision.stop_loss is None:
        missing.append("stop_loss")
    if not decision.invalidation_conditions:
        missing.append("invalidation_conditions")
    if decision.position_suggestion is None:
        missing.append("position_suggestion")
    return tuple(dict.fromkeys(missing))


def _no_trade_reasons(decision: Decision) -> tuple[str, ...]:
    if decision.action is not Action.NO_TRADE and _direction(decision) is not (
        DecisionDirection.NO_TRADE
    ):
        return ()
    if decision.downgrade_reasons:
        return decision.downgrade_reasons
    return ("formal decision is no_trade",)
