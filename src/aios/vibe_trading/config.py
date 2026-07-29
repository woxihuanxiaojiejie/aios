"""AIOS-side configuration bridge for Vibe-Trading.

Reads Vibe-Trading parameters from AIOS environment variables with useful
defaults for local development.

This module does *not* load any Vibe-Trading classes at module scope so that
the adapter stays importable even when the optional dependency is absent.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_ENV_PREFIX = "AIOS_VIBE_TRADING_"


def vibe_trading_config_from_env(
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build AIOS-side config for Vibe-Trading adapter boundaries.

    Every value is sourced from AIOS-controlled env vars (or the explicit
    ``overrides`` dict) so that callers never need to hard-code provider
    credentials or non-default tuning parameters.
    """
    overrides = overrides or {}

    def _env(name: str, default: str) -> str:
        return os.environ.get(f"{_ENV_PREFIX}{name}", default)

    results_dir = overrides.get(
        "results_dir", Path(_env("RESULTS_DIR", "./results/vibe_trading"))
    )

    return {
        "results_dir": (
            Path(results_dir) if not isinstance(results_dir, Path) else results_dir
        ),
        "llm_provider": overrides.get("llm_provider", _env("PROVIDER", "deepseek")),
        "deep_think_llm": overrides.get(
            "deep_think_llm",
            _env("DEEP_THINK_MODEL", "deepseek/deepseek-chat"),
        ),
        "quick_think_llm": overrides.get(
            "quick_think_llm",
            _env("QUICK_THINK_MODEL", "deepseek/deepseek-chat"),
        ),
        "max_debate_rounds": int(
            overrides.get("max_debate_rounds", _env("MAX_DEBATE_ROUNDS", "2"))
        ),
        "max_risk_discuss_rounds": int(
            overrides.get(
                "max_risk_discuss_rounds",
                _env("MAX_RISK_DISCUSS_ROUNDS", "2"),
            )
        ),
        "max_recur_limit": int(
            overrides.get("max_recur_limit", _env("MAX_RECUR_LIMIT", "50"))
        ),
    }
