from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from aios.adapters.market_data import Adjustment, MarketBar
from aios.adapters.market_evidence import market_bar_to_evidence
from aios.application.decision_settlement import DecisionSettlementService
from aios.kernel.decision import Decision
from aios.kernel.enums import Action, Outcome
from aios.kernel.experiment import Experiment
from aios.kernel.review import Review
from aios.storage.postgres.storage import PostgresStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService


class DeterministicMarketDataAdapter:
    def __init__(self, bars: list[MarketBar]) -> None:
        self.bars = bars
        self.calls = 0

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: Adjustment,
    ) -> list[MarketBar]:
        self.calls += 1
        return [
            bar
            for bar in self.bars
            if (
                bar.symbol == symbol
                and start_date <= bar.trade_date <= end_date
                and bar.adjustment is adjustment
            )
        ]


def baostock_bar(trade_date: date, close: str) -> MarketBar:
    return MarketBar(
        symbol="000001.SZ",
        market="CN_A",
        trade_date=trade_date,
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=Decimal("1000"),
        amount=Decimal("10000"),
        adjustment=Adjustment.NONE,
        source="baostock-deterministic-stub",
        fetched_at=datetime(2026, 7, 20, 8, 0, tzinfo=UTC),
    )


def test_postgres_settlement_creates_review_and_persists_after_rebuild(
    migrated_postgres_url: str,
) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    lifecycle = DecisionLifecycleService(storage)
    bars = [
        baostock_bar(date(2026, 7, 1), "10.00"),
        baostock_bar(date(2026, 7, 2), "10.30"),
    ]
    evidence_ids = [
        lifecycle.register_evidence(
            market_bar_to_evidence(bar, reliability=0.9)
        ).evidence_id
        for bar in bars
    ]
    decision_created_at = datetime(2026, 7, 1, 9, 30, tzinfo=UTC)
    experiment = lifecycle.start_experiment(
        Experiment(
            name="postgres-settlement-review",
            model="manual-no-llm",
            prompt_version="decision-v1",
            agent_config_version="manual-integration",
            dataset_snapshot="baostock-deterministic-stub",
            evidence_ids=evidence_ids,
            parameters={"temperature": 0},
            started_at=decision_created_at - timedelta(minutes=10),
            finished_at=decision_created_at - timedelta(minutes=1),
            created_at=decision_created_at - timedelta(minutes=10),
        )
    )
    decision = lifecycle.create_decision(
        Decision(
            experiment_id=experiment.experiment_id,
            symbol="000001.SZ",
            action=Action.BUY,
            horizon="1d",
            confidence=0.7,
            expected_return=0.02,
            max_expected_loss=0.05,
            evidence_ids=evidence_ids,
            reasoning_summary="manual deterministic integration decision",
            created_at=decision_created_at,
            valid_until=decision_created_at + timedelta(days=1),
        )
    )
    adapter = DeterministicMarketDataAdapter(bars)

    result = DecisionSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=adapter,
    ).settle(
        decision_id=decision.decision_id,
        as_of=datetime(2026, 7, 20, tzinfo=UTC),
    )

    assert adapter.calls == 1
    assert result.review.actual_return == result.outcome.realized_return
    assert result.review.outcome is Outcome.PROFIT
    fresh_storage = PostgresStorage(migrated_postgres_url)
    assert fresh_storage.get(Review, result.review.review_id) == result.review
    assert (
        fresh_storage.get_review_by_decision_id(decision.decision_id) == result.review
    )
