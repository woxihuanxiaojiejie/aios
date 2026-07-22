"""Tests for the Vibe-Trading adapter boundary.

These tests do not run Vibe-Trading. AIOS only keeps a narrow optional boundary
until a stable Vibe-Trading MCP/API output contract is wired.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


@pytest.fixture
def sample_as_of() -> datetime:
    return datetime(2026, 7, 17, 8, 0, tzinfo=UTC)


def test_default_construction() -> None:
    from aios.vibe_trading.adapter import VibeTradingAdapter

    adapter = VibeTradingAdapter()
    assert adapter._config_overrides == {}


def test_with_overrides() -> None:
    from aios.vibe_trading.adapter import VibeTradingAdapter

    adapter = VibeTradingAdapter(config_overrides={"command": "vibe-trading"})
    assert adapter._config_overrides == {"command": "vibe-trading"}


def test_format_trade_date_utc(sample_as_of: datetime) -> None:
    from aios.vibe_trading.adapter import VibeTradingAdapter

    result = VibeTradingAdapter._format_trade_date(sample_as_of)
    assert result == "2026-07-17"


def test_format_trade_date_rejects_naive() -> None:
    from aios.vibe_trading.adapter import (
        VibeTradingAdapter,
        VibeTradingConfigurationError,
    )

    with pytest.raises(VibeTradingConfigurationError, match="timezone-aware"):
        VibeTradingAdapter._format_trade_date(datetime(2026, 7, 17, 8, 0))


def test_missing_package_raises_config_error() -> None:
    from importlib.metadata import PackageNotFoundError

    from aios.vibe_trading.adapter import (
        VIBE_TRADING_PACKAGE,
        VibeTradingAdapter,
        VibeTradingConfigurationError,
    )

    with (
        patch(
            "aios.vibe_trading.adapter.version",
            side_effect=PackageNotFoundError(VIBE_TRADING_PACKAGE),
        ),
        pytest.raises(VibeTradingConfigurationError, match="Vibe-Trading"),
    ):
        VibeTradingAdapter._ensure_installed()


def test_analyze_rejects_unstructured_cli_output(
    sample_as_of: datetime,
) -> None:
    from aios.vibe_trading.adapter import VibeTradingAdapter, VibeTradingRuntimeError

    adapter = VibeTradingAdapter()
    adapter._ensure_installed = lambda: None  # type: ignore[method-assign]

    with (
        patch(
            "aios.vibe_trading.adapter.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=["vibe-trading"],
                returncode=0,
                stdout="plain text",
                stderr="",
            ),
        ),
        pytest.raises(VibeTradingRuntimeError, match="structured JSON"),
    ):
        adapter.analyze(
            symbol="000001.SZ",
            market="CN_A",
            as_of=sample_as_of,
            horizon_days=3,
            workflow="investment_committee",
            provider="fake",
            model="fake-model",
        )


def test_adapter_does_not_import_kernel() -> None:
    source = (
        Path(__file__).parent.parent.parent
        / "src"
        / "aios"
        / "vibe_trading"
        / "adapter.py"
    ).read_text()
    assert "aios.kernel" not in source
    assert "aios.workflows" not in source


def test_config_defaults_without_env(monkeypatch: Any) -> None:
    from aios.vibe_trading.config import vibe_trading_config_from_env

    for var in (
        "AIOS_VIBE_TRADING_PROVIDER",
        "AIOS_VIBE_TRADING_DEEP_THINK_MODEL",
        "AIOS_VIBE_TRADING_QUICK_THINK_MODEL",
        "AIOS_VIBE_TRADING_MAX_DEBATE_ROUNDS",
        "AIOS_VIBE_TRADING_MAX_RISK_DISCUSS_ROUNDS",
        "AIOS_VIBE_TRADING_MAX_RECUR_LIMIT",
        "AIOS_VIBE_TRADING_RESULTS_DIR",
    ):
        monkeypatch.delenv(var, raising=False)

    kw = vibe_trading_config_from_env()

    assert kw["llm_provider"] == "deepseek"
    assert kw["deep_think_llm"] == "deepseek/deepseek-chat"
    assert kw["quick_think_llm"] == "deepseek/deepseek-chat"
    assert kw["max_debate_rounds"] == 2
    assert kw["max_risk_discuss_rounds"] == 2
    assert kw["max_recur_limit"] == 50
    assert isinstance(kw["results_dir"], Path)


def test_config_env_override(monkeypatch: Any) -> None:
    from aios.vibe_trading.config import vibe_trading_config_from_env

    monkeypatch.setenv("AIOS_VIBE_TRADING_PROVIDER", "openai")
    monkeypatch.setenv("AIOS_VIBE_TRADING_DEEP_THINK_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("AIOS_VIBE_TRADING_QUICK_THINK_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("AIOS_VIBE_TRADING_MAX_DEBATE_ROUNDS", "3")
    monkeypatch.setenv("AIOS_VIBE_TRADING_MAX_RISK_DISCUSS_ROUNDS", "3")
    monkeypatch.setenv("AIOS_VIBE_TRADING_MAX_RECUR_LIMIT", "100")

    kw = vibe_trading_config_from_env()

    assert kw["llm_provider"] == "openai"
    assert kw["deep_think_llm"] == "openai/gpt-4o-mini"
    assert kw["max_debate_rounds"] == 3
    assert kw["max_recur_limit"] == 100
