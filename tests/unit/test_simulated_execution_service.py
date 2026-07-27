from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from tests.factories import (
    fixed_now,
    make_decision,
    make_evidence,
    make_experiment,
    make_research_session,
    make_watchlist_item,
)

from aios.adapters.market_data import Adjustment, MarketBar
from aios.application.research_lifecycle import ResearchLifecycleService
from aios.application.simulated_execution import SimulatedExecutionService
from aios.application.trade_plan import TradePlanService
from aios.kernel.enums import (
    DecisionDirection,
    ExecutionExitReason,
    ExecutionStatus,
    ResearchSessionStatus,
    TradePlanStatus,
)
from aios.kernel.errors import InvalidStateTransitionError
from aios.kernel.execution import SimulatedExecution
from aios.kernel.trade_plan import TradePlan
from aios.storage.memory import InMemoryStorage
from aios.storage.postgres.mapper import model_to_entity, to_model


class StaticMarketDataAdapter:
    def __init__(self, bars: list[MarketBar]) -> None:
        self.bars = bars
        self.calls: list[tuple[str, date, date, Adjustment]] = []

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: Adjustment,
    ) -> list[MarketBar]:
        self.calls.append((symbol, start_date, end_date, adjustment))
        return [
            bar
            for bar in self.bars
            if bar.symbol == symbol and start_date <= bar.trade_date <= end_date
        ]


def test_simulated_execution_mapper_round_trips_all_fields() -> None:
    execution = SimulatedExecution(
        execution_id="sx_00000000-0000-0000-0000-000000000001",
        trade_plan_id="tp_00000000-0000-0000-0000-000000000001",
        decision_id="dc_00000000-0000-0000-0000-000000000001",
        research_session_id="rs_00000000-0000-0000-0000-000000000001",
        symbol="600519",
        direction=DecisionDirection.BULLISH,
        execution_status=ExecutionStatus.WAITING_SETTLEMENT,
        execution_date=date(2026, 7, 1),
        market_bar_id="akshare.stock_zh_a_hist:600519:2026-07-01:none",
        market_data_source="akshare.stock_zh_a_hist",
        planned_entry="10.00",
        executed_entry=Decimal("10.00"),
        executed_exit=Decimal("9.50"),
        position_size=Decimal("0.25"),
        fee=Decimal("0.0010"),
        slippage=Decimal("0.0005"),
        realized_return=Decimal("-0.0515"),
        exit_reason=ExecutionExitReason.STOP,
        created_at=datetime(2026, 7, 1, tzinfo=UTC),
        updated_at=datetime(2026, 7, 1, tzinfo=UTC),
    )

    assert model_to_entity(to_model(execution)) == execution


def test_ready_trade_plan_executes_stop_first_when_target_and_stop_hit_same_day() -> (
    None
):
    storage, plan = _storage_with_ready_trade_plan()
    service = SimulatedExecutionService(
        lifecycle=ResearchLifecycleService(storage),
        market_data_adapter=StaticMarketDataAdapter(
            [
                _bar(date(2026, 8, 1), open_="10.00", high="12.50", low="9.40"),
            ]
        ),
    )

    execution = service.execute_trade_plan(plan.trade_plan_id)

    assert execution.execution_status is ExecutionStatus.WAITING_SETTLEMENT
    assert execution.executed_entry == Decimal("10.00")
    assert execution.executed_exit == Decimal("9.50")
    assert execution.exit_reason is ExecutionExitReason.STOP
    assert execution.realized_return == Decimal("-0.0510")
    session = storage.get(
        type(make_research_session()),
        "rs_00000000-0000-0000-0000-000000000001",
    )
    assert session.status is ResearchSessionStatus.WAITING_SETTLEMENT


def test_execution_rejects_no_trade_and_expired_plans() -> None:
    storage, plan = _storage_with_ready_trade_plan()
    service = SimulatedExecutionService(
        lifecycle=ResearchLifecycleService(storage),
        market_data_adapter=StaticMarketDataAdapter([]),
    )
    storage.replace(plan.model_copy(update={"status": TradePlanStatus.EXPIRED}))

    with pytest.raises(InvalidStateTransitionError, match="ready"):
        service.execute_trade_plan(plan.trade_plan_id)


def test_execution_records_not_filled_without_fake_price() -> None:
    storage, plan = _storage_with_ready_trade_plan()
    service = SimulatedExecutionService(
        lifecycle=ResearchLifecycleService(storage),
        market_data_adapter=StaticMarketDataAdapter(
            [
                _bar(
                    date(2026, 8, 1),
                    open_="9.70",
                    high="9.90",
                    low="9.60",
                    close="9.80",
                )
            ]
        ),
    )

    execution = service.execute_trade_plan(plan.trade_plan_id)

    assert execution.execution_status is ExecutionStatus.NOT_FILLED
    assert execution.executed_entry is None
    assert execution.executed_exit is None
    assert execution.realized_return is None
    assert execution.exit_reason is ExecutionExitReason.NOT_FILLED


def test_execution_is_idempotent_and_concurrency_resumes_existing_object() -> None:
    storage, plan = _storage_with_ready_trade_plan()
    service = SimulatedExecutionService(
        lifecycle=ResearchLifecycleService(storage),
        market_data_adapter=StaticMarketDataAdapter(
            [_bar(date(2026, 8, 1), open_="10.00", high="12.50", low="9.40")]
        ),
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: service.execute_trade_plan(plan.trade_plan_id),
                range(2),
            )
        )

    assert results[0] == results[1]
    assert (
        storage.get_simulated_execution_by_trade_plan_id(plan.trade_plan_id)
        == results[0]
    )
    assert storage.list(SimulatedExecution) == [results[0]]


def _storage_with_ready_trade_plan() -> tuple[InMemoryStorage, TradePlan]:
    storage = InMemoryStorage()
    evidence = make_evidence()
    experiment = make_experiment(evidence.evidence_id)
    watchlist = make_watchlist_item()
    session = make_research_session(as_of=datetime(2026, 8, 1, tzinfo=UTC))
    decision = make_decision(
        experiment.experiment_id,
        evidence.evidence_id,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
    ).model_copy(
        update={
            "symbol": "600519",
            "research_session_id": session.research_session_id,
            "direction": DecisionDirection.BULLISH,
            "target_range": (12.0, 13.0),
            "entry_conditions": ("10.00",),
            "stop_loss": 9.5,
            "invalidation_conditions": ("close below 9.50",),
            "position_suggestion": 0.25,
            "horizon": "3d",
            "valid_until": datetime(2026, 8, 4, tzinfo=UTC),
            "planned_settlement_at": datetime(2026, 8, 4, tzinfo=UTC),
        }
    )
    for entity in (evidence, experiment, watchlist, session, decision):
        storage.save(entity)
    lifecycle = ResearchLifecycleService(storage)
    plan = TradePlanService(lifecycle).create_from_decision(decision.decision_id)
    _advance_to_trade_plan_ready(lifecycle, session.research_session_id)
    return storage, plan


def _advance_to_trade_plan_ready(
    lifecycle: ResearchLifecycleService,
    session_id: str,
) -> None:
    for state in (
        ResearchSessionStatus.EVIDENCE_READY,
        ResearchSessionStatus.HYPOTHESIS_READY,
        ResearchSessionStatus.SKILLS_RUNNING,
        ResearchSessionStatus.DISCUSSION_READY,
        ResearchSessionStatus.RISK_REVIEW,
        ResearchSessionStatus.DECISION_READY,
        ResearchSessionStatus.TRADE_PLAN_READY,
    ):
        lifecycle.transition(
            session_id,
            state,
            reason=f"test fixture {state.value}",
            allow_future_state=True,
        )


def _bar(
    trade_date: date,
    *,
    open_: str,
    high: str,
    low: str,
    close: str = "10.00",
) -> MarketBar:
    return MarketBar(
        symbol="600519",
        market="CN_A",
        trade_date=trade_date,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("1000"),
        amount=Decimal("10000"),
        adjustment=Adjustment.NONE,
        source="akshare.stock_zh_a_hist",
        fetched_at=fixed_now() + timedelta(days=1),
    )
