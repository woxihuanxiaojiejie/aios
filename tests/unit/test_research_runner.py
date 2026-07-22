from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from aios.adapters.market_data import Adjustment, MarketBar
from aios.application.research_runner import ResearchRunner
from aios.application.watchlist import WatchlistService
from aios.kernel.debate import (
    DebateRecord,
    DecisionAssemblyRecord,
    DecisionProposal,
    RiskReview,
)
from aios.kernel.evidence import Evidence
from aios.kernel.research_records import AgentReport, Hypothesis
from aios.kernel.research_run import ResearchRun
from aios.storage.memory import InMemoryStorage
from aios.vibe_trading.output_mapper import VibeTradingRawResult
from aios.workflows.decision_lifecycle import DecisionLifecycleService

AS_OF = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


def test_research_runner_completes_auto_research_and_is_idempotent() -> None:
    storage = InMemoryStorage()
    watchlist = WatchlistService(storage).add_item(symbol="600519", market="CN")
    runner = ResearchRunner(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=FakeMarketDataAdapter(),
        vibe_trading_adapter=FakeVibeTradingAdapter(),
    )

    run = runner.run_research(
        watchlist_item_id=watchlist.watchlist_item_id,
        horizon_days=3,
        as_of=AS_OF,
        workflow="investment_committee",
        provider="fake",
        model="fake-model",
    )
    replay = runner.run_research(
        watchlist_item_id=watchlist.watchlist_item_id,
        horizon_days=3,
        as_of=AS_OF,
        workflow="investment_committee",
        provider="fake",
        model="fake-model",
    )

    assert run.status == "completed"
    assert replay.run_id == run.run_id
    assert len(storage.list(ResearchRun)) == 1
    assert len(storage.list(Evidence)) == 1
    assert len(storage.list(AgentReport)) == 2
    assert len(storage.list(Hypothesis)) == 2
    assert len(storage.list(DebateRecord)) == 1
    assert len(storage.list(DecisionProposal)) == 1
    assert len(storage.list(RiskReview)) == 1
    assert len(storage.list(DecisionAssemblyRecord)) == 1


def test_research_runner_rejects_unmappable_vibe_output_without_reports() -> None:
    storage = InMemoryStorage()
    watchlist = WatchlistService(storage).add_item(symbol="600519", market="CN")
    runner = ResearchRunner(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=FakeMarketDataAdapter(),
        vibe_trading_adapter=FakeVibeTradingAdapter(analyst_reports={}),
    )

    with pytest.raises(Exception, match="no mappable analyst reports"):
        runner.run_research(
            watchlist_item_id=watchlist.watchlist_item_id,
            horizon_days=3,
            as_of=AS_OF,
            workflow="investment_committee",
            provider="fake",
            model="fake-model",
        )

    run = storage.list(ResearchRun)[0]
    assert run.status == "failed"
    assert storage.list(AgentReport) == []


def test_research_runner_resume_after_vibe_failure() -> None:
    storage = InMemoryStorage()
    watchlist = WatchlistService(storage).add_item(symbol="600519", market="CN")
    vibe = FakeVibeTradingAdapter(fail_once=True)
    runner = ResearchRunner(
        lifecycle=DecisionLifecycleService(storage),
        market_data_adapter=FakeMarketDataAdapter(),
        vibe_trading_adapter=vibe,
    )

    with pytest.raises(RuntimeError, match="temporary Vibe failure"):
        runner.run_research(
            watchlist_item_id=watchlist.watchlist_item_id,
            horizon_days=3,
            as_of=AS_OF,
            workflow="investment_committee",
            provider="fake",
            model="fake-model",
        )

    failed = storage.list(ResearchRun)[0]
    assert failed.status == "failed"

    resumed = runner.resume_research(failed.run_id)

    assert resumed.status == "completed"
    assert len(storage.list(Evidence)) == 1
    assert len(storage.list(DecisionAssemblyRecord)) == 1


class FakeMarketDataAdapter:
    def fetch_daily_bars(
        self,
        symbol: str,
        start_date,
        end_date,
        adjustment: Adjustment,
    ) -> list[MarketBar]:
        return [
            MarketBar(
                symbol=symbol,
                market="CN_A",
                trade_date=end_date,
                open=Decimal("100"),
                high=Decimal("110"),
                low=Decimal("95"),
                close=Decimal("108"),
                volume=Decimal("10000"),
                amount=Decimal("1080000"),
                adjustment=adjustment,
                source="fixture",
                fetched_at=AS_OF,
            )
        ]


class FakeVibeTradingAdapter:
    def __init__(
        self,
        *,
        analyst_reports: dict[str, str] | None = None,
        fail_once: bool = False,
    ) -> None:
        self._analyst_reports = analyst_reports
        self._fail_once = fail_once

    def analyze(self, **kwargs) -> VibeTradingRawResult:
        if self._fail_once:
            self._fail_once = False
            raise RuntimeError("temporary Vibe failure")
        return VibeTradingRawResult(
            symbol=kwargs["symbol"],
            market=kwargs["market"],
            as_of=kwargs["as_of"],
            vibe_run_id="vibe_fixture_1",
            workflow=kwargs["workflow"],
            raw_output_reference="fixture://vibe/vibe_fixture_1.json",
            analyst_reports=self._analyst_reports
            if self._analyst_reports is not None
            else {
                "market": "技术面趋势向上。",
                "news": "新闻面没有重大负面事件。",
            },
            investment_debate={"judge_decision": "支持谨慎买入。"},
            trader_plan="结构化计划建议 buy。",
            risk_assessment={"risk_judge_decision": "风险可接受。"},
            final_decision={"signal": "buy", "confidence": 0.6},
            model_provider=kwargs["provider"],
            model_name=kwargs["model"],
            started_at=AS_OF,
            completed_at=AS_OF,
        )
