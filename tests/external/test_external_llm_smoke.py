from __future__ import annotations

import os
from datetime import UTC, date, datetime

import pytest
from dotenv import load_dotenv

from aios.adapters.market_data import Adjustment
from aios.adapters.market_evidence import market_bar_to_evidence
from aios.application.decision_generation import DecisionGenerationService
from aios.integrations.baostock.adapter import BaoStockMarketDataAdapter
from aios.integrations.litellm.adapter import LiteLLMAdapter
from aios.kernel.experiment import Experiment
from aios.storage.memory import InMemoryStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService

load_dotenv()


@pytest.mark.external_llm
def test_real_litellm_decision_generation_smoke() -> None:
    if os.getenv("AIOS_RUN_EXTERNAL_LLM_TESTS") != "1":
        pytest.skip("set AIOS_RUN_EXTERNAL_LLM_TESTS=1 to run external LLM smoke")
    model = os.getenv("AIOS_EXTERNAL_LLM_MODEL")
    if not model:
        pytest.skip("set AIOS_EXTERNAL_LLM_MODEL to run external LLM smoke")

    storage = InMemoryStorage()
    lifecycle = DecisionLifecycleService(storage)
    bars = BaoStockMarketDataAdapter().fetch_daily_bars(
        "000001.SZ",
        date(2026, 7, 13),
        date(2026, 7, 17),
        adjustment=Adjustment.NONE,
    )
    evidence_ids: list[str] = []
    for bar in bars[:3]:
        evidence = lifecycle.register_evidence(
            market_bar_to_evidence(bar, reliability=0.9)
        )
        evidence_ids.append(evidence.evidence_id)
    experiment = lifecycle.start_experiment(
        Experiment(
            name="external-llm-smoke",
            model=model,
            prompt_version="decision-v1",
            agent_config_version="manual-smoke",
            dataset_snapshot="baostock-2026-07-13-2026-07-17",
            evidence_ids=evidence_ids,
            parameters={"temperature": 0},
            started_at=datetime.now(UTC),
        )
    )
    result = DecisionGenerationService(
        lifecycle=lifecycle,
        llm_adapter=LiteLLMAdapter(),
    ).generate(
        experiment_id=experiment.experiment_id,
        symbol="000001.SZ",
        horizon="1d",
    )

    assert storage.get(type(result.decision), result.decision.decision_id)
    assert result.generation.latency_ms >= 0
