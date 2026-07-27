from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from aios.adapters.market_data import Adjustment, MarketBar, MarketDataAdapter
from aios.application.research_lifecycle import ResearchLifecycleService
from aios.kernel.enums import (
    DecisionDirection,
    ExecutionExitReason,
    ExecutionStatus,
    ResearchSessionStatus,
    TradePlanStatus,
)
from aios.kernel.errors import InvalidStateTransitionError, StorageOperationError
from aios.kernel.execution import SimulatedExecution
from aios.kernel.trade_plan import TradePlan

DEFAULT_FEE = Decimal("0.0010")
DEFAULT_SLIPPAGE = Decimal("0")


class SimulatedExecutionService:
    def __init__(
        self,
        *,
        lifecycle: ResearchLifecycleService,
        market_data_adapter: MarketDataAdapter,
        adjustment: Adjustment = Adjustment.NONE,
    ) -> None:
        self._lifecycle = lifecycle
        self._storage = lifecycle.storage
        self._market_data_adapter = market_data_adapter
        self._adjustment = adjustment

    def execute_trade_plan(self, trade_plan_id: str) -> SimulatedExecution:
        existing = self._storage.get_simulated_execution_by_trade_plan_id(trade_plan_id)
        if existing is not None:
            return existing

        plan = self._storage.get(TradePlan, trade_plan_id)
        if plan.status is not TradePlanStatus.READY:
            msg = "SimulatedExecution requires TradePlan status ready"
            raise InvalidStateTransitionError(msg)

        execution = self._build_execution(plan)
        try:
            self._storage.save(execution)
        except StorageOperationError:
            concurrent = self._storage.get_simulated_execution_by_trade_plan_id(
                trade_plan_id
            )
            if concurrent is not None:
                return concurrent
            raise

        if execution.execution_status is ExecutionStatus.WAITING_SETTLEMENT:
            self._lifecycle.transition(
                plan.research_session_id,
                ResearchSessionStatus.WAITING_SETTLEMENT,
                reason="simulated execution completed",
                allow_future_state=True,
            )
        return execution

    def _build_execution(self, plan: TradePlan) -> SimulatedExecution:
        entry = _planned_entry_price(plan)
        bars = sorted(
            self._market_data_adapter.fetch_daily_bars(
                plan.symbol,
                plan.created_at.date(),
                plan.expiry.date(),
                self._adjustment,
            ),
            key=lambda bar: bar.trade_date,
        )
        entry_index = _entry_index(bars, entry)
        now = datetime.now(UTC)
        position = Decimal(str(plan.planned_position or 0))
        if entry_index is None:
            return SimulatedExecution(
                trade_plan_id=plan.trade_plan_id,
                decision_id=plan.decision_id,
                research_session_id=plan.research_session_id,
                symbol=plan.symbol,
                direction=plan.direction,
                execution_status=ExecutionStatus.NOT_FILLED,
                planned_entry=str(entry),
                position_size=position,
                fee=DEFAULT_FEE,
                slippage=DEFAULT_SLIPPAGE,
                exit_reason=ExecutionExitReason.NOT_FILLED,
                created_at=now,
                updated_at=now,
            )

        _exit_bar, exit_price, exit_reason = _exit(bars[entry_index:], plan)
        realized = _directional_return(plan.direction, exit_price, entry)
        realized -= DEFAULT_FEE + DEFAULT_SLIPPAGE
        realized = _q(realized, "0.0001")
        return SimulatedExecution(
            trade_plan_id=plan.trade_plan_id,
            decision_id=plan.decision_id,
            research_session_id=plan.research_session_id,
            symbol=plan.symbol,
            direction=plan.direction,
            execution_status=ExecutionStatus.WAITING_SETTLEMENT,
            execution_date=bars[entry_index].trade_date,
            market_bar_id=_market_bar_id(bars[entry_index]),
            market_data_source=bars[entry_index].source,
            planned_entry=str(entry),
            executed_entry=entry,
            executed_exit=exit_price,
            position_size=position,
            fee=DEFAULT_FEE,
            slippage=DEFAULT_SLIPPAGE,
            realized_return=realized,
            exit_reason=exit_reason,
            created_at=now,
            updated_at=now,
        )


def _planned_entry_price(plan: TradePlan) -> Decimal:
    for candidate in plan.planned_entry:
        try:
            return Decimal(candidate)
        except Exception:
            continue
    msg = "TradePlan planned_entry must contain a deterministic numeric price"
    raise InvalidStateTransitionError(msg)


def _entry_index(bars: list[MarketBar], entry: Decimal) -> int | None:
    for index, bar in enumerate(bars):
        if bar.low <= entry <= bar.high:
            return index
    return None


def _exit(
    bars: list[MarketBar],
    plan: TradePlan,
) -> tuple[MarketBar, Decimal, ExecutionExitReason]:
    target = Decimal(str(plan.target[0])) if plan.target else None
    stop = Decimal(str(plan.stop_loss)) if plan.stop_loss is not None else None
    for bar in bars:
        target_hit = target is not None and bar.high >= target
        stop_hit = stop is not None and bar.low <= stop
        if target_hit and stop_hit:
            if stop is None:
                raise AssertionError("stop_hit requires stop")
            return bar, stop, ExecutionExitReason.STOP
        if stop_hit:
            if stop is None:
                raise AssertionError("stop_hit requires stop")
            return bar, stop, ExecutionExitReason.STOP
        if target_hit:
            if target is None:
                raise AssertionError("target_hit requires target")
            return bar, target, ExecutionExitReason.TARGET
    return bars[-1], bars[-1].close, ExecutionExitReason.EXPIRY


def _directional_return(
    direction: DecisionDirection,
    exit_price: Decimal,
    entry_price: Decimal,
) -> Decimal:
    raw = (exit_price - entry_price) / entry_price
    if direction is DecisionDirection.BEARISH:
        return -raw
    return raw


def _market_bar_id(bar: MarketBar) -> str:
    return (
        f"{bar.source}:{bar.symbol}:{bar.trade_date.isoformat()}:{bar.adjustment.value}"
    )


def _q(value: Decimal, unit: str) -> Decimal:
    return value.quantize(Decimal(unit), rounding=ROUND_HALF_UP)
