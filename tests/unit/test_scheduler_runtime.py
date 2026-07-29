from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from tests.factories import (
    make_decision,
    make_evidence,
    make_experiment,
    make_research_session,
    make_watchlist_item,
)

from aios.adapters.market_data import Adjustment, MarketBar
from aios.application.research_lifecycle import ResearchLifecycleService
from aios.application.research_runtime import ResearchRuntimeResult
from aios.application.research_scheduler import ResearchSchedulerService
from aios.application.settlement_scheduler import SettlementSchedulerService
from aios.application.simulated_execution import SimulatedExecutionService
from aios.application.trade_plan import TradePlanService
from aios.application.watchlist import WatchlistService
from aios.kernel.enums import DecisionDirection, ResearchSessionStatus
from aios.kernel.execution import SimulatedExecution
from aios.kernel.research_run import ResearchRun
from aios.storage.memory import InMemoryStorage

AS_OF = datetime(2026, 8, 3, 15, 30, tzinfo=UTC)


@dataclass
class FakeTradingCalendar:
    trading: bool = True

    def is_research_time(
        self,
        *,
        as_of: datetime,
        schedule_time: time,
        timezone_name: str,
    ) -> bool:
        assert timezone_name == "Asia/Shanghai"
        return self.trading and as_of.time() >= schedule_time

    def next_research_at(
        self,
        *,
        after: datetime,
        schedule_time: time,
        timezone_name: str,
    ) -> datetime:
        return datetime.combine(after.date() + timedelta(days=1), schedule_time, UTC)


class FakeRuntime:
    def __init__(self, storage: InMemoryStorage) -> None:
        self.storage = storage
        self.calls: list[tuple[str, int, datetime, str, str, str]] = []

    def run_watchlist_item(
        self,
        *,
        watchlist_item_id: str,
        horizon_days: int,
        as_of: datetime,
        workflow: str,
        provider: str,
        model: str,
    ) -> ResearchRuntimeResult:
        self.calls.append(
            (watchlist_item_id, horizon_days, as_of, workflow, provider, model)
        )
        run = ResearchRun(
            watchlist_item_id=watchlist_item_id,
            workflow=workflow,
            input_params={
                "horizon_days": horizon_days,
                "as_of": as_of.isoformat(),
                "workflow": workflow,
                "provider": provider,
                "model": model,
                "symbol": "600519",
            },
            status="completed",
            current_stage="completed",
            symbol="600519",
            research_window_key=f"{watchlist_item_id}:3:{as_of.isoformat()}",
            finished_at=as_of,
        )
        self.storage.save(run)
        return ResearchRuntimeResult(run=run, trade_plan=None, execution=None)


class FailingRuntime:
    def run_watchlist_item(
        self,
        *,
        watchlist_item_id: str,
        horizon_days: int,
        as_of: datetime,
        workflow: str,
        provider: str,
        model: str,
    ) -> ResearchRuntimeResult:
        raise RuntimeError("provider timeout")


def test_research_due_scan_uses_watchlist_as_business_source() -> None:
    storage = InMemoryStorage()
    item = WatchlistService(storage).add_item(
        symbol="600519",
        market="CN",
        auto_research_enabled=True,
        research_horizon_days=3,
        schedule_time=time(15, 0),
        schedule_timezone="Asia/Shanghai",
        next_run_at=AS_OF - timedelta(minutes=1),
    )
    runtime = FakeRuntime(storage)

    result = ResearchSchedulerService(
        storage=storage,
        runtime=runtime,
        trading_calendar=FakeTradingCalendar(),
        workflow="brain",
        provider="fake",
        model="fake/model",
    ).run_due_once(as_of=AS_OF)

    updated = storage.get(type(item), item.watchlist_item_id)
    assert len(result.runs) == 1
    assert runtime.calls == [
        (item.watchlist_item_id, 3, AS_OF, "brain", "fake", "fake/model")
    ]
    assert updated.last_run_at == AS_OF
    assert updated.next_run_at == datetime(2026, 8, 4, 15, 0, tzinfo=UTC)
    assert updated.auto_research_enabled is True


def test_research_due_scan_skips_non_trading_day_without_runtime_error() -> None:
    storage = InMemoryStorage()
    item = WatchlistService(storage).add_item(
        symbol="600519",
        market="CN",
        auto_research_enabled=True,
        research_horizon_days=1,
        schedule_time=time(15, 0),
        schedule_timezone="Asia/Shanghai",
        next_run_at=AS_OF - timedelta(days=1),
    )
    runtime = FakeRuntime(storage)

    result = ResearchSchedulerService(
        storage=storage,
        runtime=runtime,
        trading_calendar=FakeTradingCalendar(trading=False),
        workflow="brain",
        provider="fake",
        model="fake/model",
    ).run_due_once(as_of=AS_OF)

    updated = storage.get(type(item), item.watchlist_item_id)
    assert result.runs == ()
    assert result.errors == ()
    assert runtime.calls == []
    assert updated.last_run_at is None
    assert updated.next_run_at == datetime(2026, 8, 4, 15, 0, tzinfo=UTC)


def test_research_due_scan_persists_runtime_error_as_failed_run() -> None:
    storage = InMemoryStorage()
    item = WatchlistService(storage).add_item(
        symbol="600519",
        market="CN",
        auto_research_enabled=True,
        research_horizon_days=3,
        schedule_time=time(15, 0),
        schedule_timezone="Asia/Shanghai",
        next_run_at=AS_OF - timedelta(minutes=1),
    )

    result = ResearchSchedulerService(
        storage=storage,
        runtime=FailingRuntime(),
        trading_calendar=FakeTradingCalendar(),
        workflow="brain",
        provider="fake",
        model="fake/model",
    ).run_due_once(as_of=AS_OF)

    runs = storage.list(ResearchRun)
    assert result.runs == ()
    assert len(result.errors) == 1
    assert len(runs) == 1
    assert runs[0].watchlist_item_id == item.watchlist_item_id
    assert runs[0].status == "failed"
    assert runs[0].failed_stage == "research_runtime"
    assert runs[0].error_type == "RuntimeError"
    assert runs[0].error == "provider timeout"
    assert runs[0].research_window_key == f"CN:600519:3:{AS_OF.isoformat()}"


def test_research_due_scan_does_not_repeat_failed_window() -> None:
    storage = InMemoryStorage()
    item = WatchlistService(storage).add_item(
        symbol="600519",
        market="CN",
        auto_research_enabled=True,
        research_horizon_days=3,
        schedule_time=time(15, 0),
        schedule_timezone="Asia/Shanghai",
        next_run_at=AS_OF - timedelta(minutes=1),
    )
    service = ResearchSchedulerService(
        storage=storage,
        runtime=FailingRuntime(),
        trading_calendar=FakeTradingCalendar(),
        workflow="brain",
        provider="fake",
        model="fake/model",
    )

    first = service.run_due_once(as_of=AS_OF)
    second = service.run_due_once(as_of=AS_OF)

    updated = storage.get(type(item), item.watchlist_item_id)
    runs = storage.list(ResearchRun)
    assert len(first.errors) == 1
    assert second.runs == ()
    assert second.errors == ()
    assert len(runs) == 1
    assert runs[0].research_window_key == f"CN:600519:3:{AS_OF.isoformat()}"
    assert updated.next_run_at == datetime(2026, 8, 4, 15, 0, tzinfo=UTC)


def test_settlement_due_scan_settles_simulated_executions_once() -> None:
    storage, execution, adapter = _waiting_settlement_execution()
    service = SettlementSchedulerService(
        storage=storage,
        market_data_adapter=adapter,
    )

    first = service.run_due_once(as_of=datetime(2026, 8, 5, tzinfo=UTC))
    second = service.run_due_once(as_of=datetime(2026, 8, 6, tzinfo=UTC))

    assert len(first.settled) == 1
    assert second.settled == ()
    assert first.settled[0].outcome.execution_id == execution.execution_id
    assert len(storage.list(type(first.settled[0].outcome))) == 1


def _waiting_settlement_execution() -> tuple[
    InMemoryStorage,
    SimulatedExecution,
    _StaticMarketDataAdapter,
]:
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
            session.research_session_id,
            state,
            reason=f"test fixture {state.value}",
            allow_future_state=True,
        )
    adapter = _StaticMarketDataAdapter(
        [
            _bar(date(2026, 8, 1), open_="10.00", high="12.50", low="9.40"),
            _bar(date(2026, 8, 4), open_="11.00", high="11.50", low="10.80"),
        ]
    )
    execution = SimulatedExecutionService(
        lifecycle=lifecycle,
        market_data_adapter=adapter,
    ).execute_trade_plan(plan.trade_plan_id)
    return storage, execution, adapter


class _StaticMarketDataAdapter:
    def __init__(self, bars: list[MarketBar]) -> None:
        self.bars = bars

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: Adjustment,
    ) -> list[MarketBar]:
        return [
            bar
            for bar in self.bars
            if bar.symbol == symbol and start_date <= bar.trade_date <= end_date
        ]


def _bar(trade_date: date, *, open_: str, high: str, low: str) -> MarketBar:
    from decimal import Decimal

    return MarketBar(
        symbol="600519",
        market="CN_A",
        trade_date=trade_date,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(open_),
        volume=Decimal("1000"),
        amount=Decimal("10000"),
        adjustment=Adjustment.NONE,
        source="akshare.stock_zh_a_hist",
        fetched_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
