from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

from aios.adapters.market_data import MarketDataAdapter
from aios.adapters.storage import Storage
from aios.application.research_settlement import (
    ResearchSettlementResult,
    ResearchSettlementService,
)
from aios.workflows.decision_lifecycle import DecisionLifecycleService


@dataclass(frozen=True)
class ResearchSettlementWorkerResult:
    settled: tuple[ResearchSettlementResult, ...]


class ResearchSettlementWorker:
    def __init__(
        self,
        *,
        storage: Storage,
        market_data_adapter: MarketDataAdapter,
    ) -> None:
        self._storage = storage
        self._market_data_adapter = market_data_adapter

    def run_once(
        self, *, as_of: datetime | None = None
    ) -> ResearchSettlementWorkerResult:
        settled = ResearchSettlementService(
            lifecycle=DecisionLifecycleService(self._storage),
            market_data_adapter=self._market_data_adapter,
        ).settle_due(as_of=as_of or datetime.now(UTC))
        return ResearchSettlementWorkerResult(settled=settled)

    async def run_forever(
        self,
        *,
        interval_seconds: float,
        stop_event: asyncio.Event,
    ) -> None:
        while not stop_event.is_set():
            await asyncio.to_thread(self.run_once)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            except TimeoutError:
                continue
