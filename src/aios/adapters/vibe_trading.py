from __future__ import annotations

from datetime import datetime
from typing import Protocol

from aios.vibe_trading.output_mapper import VibeTradingRawResult


class VibeTradingResearchAdapter(Protocol):
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
        """Run external Vibe-Trading research and return an auditable result."""
