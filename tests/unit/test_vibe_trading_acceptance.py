from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest


@pytest.mark.skipif(
    os.getenv("AIOS_RUN_VIBE_TRADING_ACCEPTANCE") != "1",
    reason="set AIOS_RUN_VIBE_TRADING_ACCEPTANCE=1 to run real Vibe-Trading CLI",
)
def test_real_vibe_trading_cli_acceptance() -> None:
    from aios.vibe_trading.adapter import VibeTradingAdapter

    result = VibeTradingAdapter().analyze(
        symbol="600519",
        market="CN",
        as_of=datetime(2026, 7, 21, 10, 0, tzinfo=UTC),
        horizon_days=3,
        workflow="investment_committee",
        provider=os.getenv("AIOS_VIBE_TRADING_PROVIDER", "deepseek"),
        model=os.getenv("AIOS_VIBE_TRADING_DEEP_THINK_MODEL", "deepseek/deepseek-chat"),
    )

    assert result.vibe_run_id
    assert result.workflow == "investment_committee"
