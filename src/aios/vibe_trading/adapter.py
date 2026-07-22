"""Vibe-Trading adapter boundary for AIOS.

Vibe-Trading exposes stable CLI/MCP/API entry points. AIOS keeps this module
as a narrow optional boundary and does not import Vibe-Trading internals or
fabricate a direct agent runtime API.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from aios.vibe_trading.config import vibe_trading_config_from_env
from aios.vibe_trading.output_mapper import VibeTradingRawResult

VIBE_TRADING_PACKAGE = "vibe-trading-ai"


class VibeTradingConfigurationError(Exception):
    """Raised when Vibe-Trading integration configuration is invalid."""


class VibeTradingRuntimeError(Exception):
    """Raised when Vibe-Trading execution is requested without a stable bridge."""


class VibeTradingAdapter:
    """CLI bridge for the Vibe-Trading integration boundary.

    This adapter intentionally avoids importing ``../Vibe-Trading`` internals.
    It only accepts structured JSON matching ``VibeTradingRawResult``.
    """

    def __init__(
        self,
        *,
        config_overrides: dict[str, Any] | None = None,
    ) -> None:
        self._config_overrides = config_overrides or {}

    def analyze(
        self,
        *,
        symbol: str,
        market: str,
        as_of: datetime,
        horizon_days: int,
        workflow: str,
        provider: str,
        model: str,
    ) -> VibeTradingRawResult:
        """Run Vibe-Trading through its CLI and parse structured JSON output."""
        self._ensure_installed()
        trade_date = self._format_trade_date(as_of)
        config = vibe_trading_config_from_env(overrides=self._config_overrides)
        command = str(self._config_overrides.get("command", "vibe-trading"))
        timeout_seconds = int(self._config_overrides.get("timeout_seconds", 300))
        variables = json.dumps(
            {
                "ticker": symbol,
                "symbol": symbol,
                "market": market,
                "trade_date": trade_date,
                "horizon_days": horizon_days,
                "provider": provider,
                "model": model,
            },
            sort_keys=True,
        )
        try:
            completed = subprocess.run(
                [command, "--swarm-run", workflow, variables],
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            msg = f"Vibe-Trading timed out after {timeout_seconds}s"
            raise VibeTradingRuntimeError(msg) from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            msg = f"Vibe-Trading failed with exit code {completed.returncode}: {detail}"
            raise VibeTradingRuntimeError(msg)
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            msg = "Vibe-Trading CLI did not return structured JSON output"
            raise VibeTradingRuntimeError(msg) from exc
        result = VibeTradingRawResult.model_validate(payload)
        return result.model_copy(
            update={
                "workflow": workflow,
                "model_provider": provider,
                "model_name": model,
                "upstream_version": self._upstream_version(),
                "raw_output_reference": result.raw_output_reference
                or str(config["results_dir"]),
            }
        )

    @staticmethod
    def _ensure_installed() -> None:
        try:
            version(VIBE_TRADING_PACKAGE)
        except PackageNotFoundError as exc:
            msg = (
                "Vibe-Trading is not installed. "
                "Run `uv sync --extra vibe-trading` to install it."
            )
            raise VibeTradingConfigurationError(msg) from exc

    @staticmethod
    def _format_trade_date(as_of: datetime) -> str:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            msg = "as_of must be timezone-aware"
            raise VibeTradingConfigurationError(msg)
        return as_of.date().isoformat()

    @staticmethod
    def _upstream_version() -> str | None:
        try:
            return version(VIBE_TRADING_PACKAGE)
        except Exception:
            return None
