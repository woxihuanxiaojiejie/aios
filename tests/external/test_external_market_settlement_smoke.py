from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta

import pytest

from aios.adapters.market_data import Adjustment
from aios.adapters.market_evidence import market_bar_to_evidence
from aios.application.decision_settlement import DecisionSettlementService
from aios.integrations.baostock.adapter import BaoStockMarketDataAdapter
from aios.kernel.decision import Decision
from aios.kernel.enums import Action, EvaluationFinalResult, OutcomeStatus
from aios.kernel.experiment import Experiment
from aios.storage.memory import InMemoryStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService


@pytest.mark.external_market
def test_real_baostock_market_settlement_smoke() -> None:
    if os.getenv("AIOS_RUN_EXTERNAL_MARKET_TESTS") != "1":
        pytest.skip("set AIOS_RUN_EXTERNAL_MARKET_TESTS=1 to run external market smoke")

    storage = InMemoryStorage()
    lifecycle = DecisionLifecycleService(storage)
    adapter = BaoStockMarketDataAdapter()
    bars = adapter.fetch_daily_bars(
        "000001.SZ",
        date(2026, 7, 1),
        date(2026, 7, 10),
        adjustment=Adjustment.NONE,
    )
    evidence_ids: list[str] = []
    for bar in bars[:3]:
        evidence = lifecycle.register_evidence(
            market_bar_to_evidence(bar, reliability=0.9)
        )
        evidence_ids.append(evidence.evidence_id)

    decision_created_at = datetime(2026, 7, 1, 9, 30, tzinfo=UTC)
    experiment = lifecycle.start_experiment(
        Experiment(
            name="external-market-settlement-smoke",
            model="manual-no-llm",
            prompt_version="decision-v1",
            agent_config_version="manual-smoke",
            dataset_snapshot="baostock-2026-07-01-2026-07-10",
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
            horizon="3d",
            confidence=0.6,
            expected_return=0.0,
            max_expected_loss=0.1,
            evidence_ids=evidence_ids,
            reasoning_summary="manual historical smoke decision without LLM",
            created_at=decision_created_at,
            valid_until=decision_created_at + timedelta(days=3),
        )
    )

    result = DecisionSettlementService(
        lifecycle=lifecycle,
        market_data_adapter=adapter,
    ).settle(
        decision_id=decision.decision_id,
        as_of=datetime(2026, 7, 20, tzinfo=UTC),
    )

    assert result.outcome.status is OutcomeStatus.SETTLED
    assert result.outcome.entry_price is not None
    assert result.outcome.entry_price > 0
    assert result.outcome.exit_price is not None
    assert result.outcome.exit_price > 0
    assert result.outcome.realized_return is not None
    assert DecimalRange("-0.5", "0.5").contains(result.outcome.realized_return)
    assert result.evaluation.final_result in {
        EvaluationFinalResult.PASS,
        EvaluationFinalResult.FAIL,
        EvaluationFinalResult.INCONCLUSIVE,
    }
    assert lifecycle.get_decision_outcome(decision.decision_id) == result.outcome
    assert (
        lifecycle.get_decision_evaluation(
            decision.decision_id,
            result.evaluation.evaluation_rules_version,
        )
        == result.evaluation
    )


class DecimalRange:
    def __init__(self, lower: str, upper: str) -> None:
        from decimal import Decimal

        self.lower = Decimal(lower)
        self.upper = Decimal(upper)

    def contains(self, value: object) -> bool:
        from decimal import Decimal

        if not isinstance(value, Decimal):
            return False
        return self.lower <= value <= self.upper
