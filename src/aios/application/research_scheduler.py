from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Protocol

from aios.adapters.storage import Storage
from aios.application.research_runtime import ResearchRuntimeResult
from aios.application.watchlist import WatchlistService
from aios.kernel.base import utc_now
from aios.kernel.enums import WatchlistStatus
from aios.kernel.research_run import ResearchRun
from aios.kernel.watchlist import WatchlistItem


class TradingCalendar(Protocol):
    def is_research_time(
        self,
        *,
        as_of: datetime,
        schedule_time: time,
        timezone_name: str,
    ) -> bool:
        """Return whether research may run at this instant."""

    def next_research_at(
        self,
        *,
        after: datetime,
        schedule_time: time,
        timezone_name: str,
    ) -> datetime:
        """Return the next valid research timestamp."""


class ResearchRuntime(Protocol):
    def run_watchlist_item(
        self,
        *,
        watchlist_item_id: str,
        horizon_days: int,
        as_of: datetime,
        workflow: str,
        provider: str,
        model: str,
    ) -> ResearchRuntimeResult:
        """Run research and optional simulated execution for one WatchlistItem."""


@dataclass(frozen=True)
class ResearchSchedulerError:
    watchlist_item_id: str
    symbol: str
    error_type: str
    error_message: str


@dataclass(frozen=True)
class ResearchSchedulerResult:
    runs: tuple[ResearchRun, ...]
    errors: tuple[ResearchSchedulerError, ...]


class ResearchSchedulerService:
    def __init__(
        self,
        *,
        storage: Storage,
        runtime: ResearchRuntime,
        trading_calendar: TradingCalendar,
        workflow: str,
        provider: str,
        model: str,
    ) -> None:
        self._storage = storage
        self._runtime = runtime
        self._trading_calendar = trading_calendar
        self._workflow = workflow
        self._provider = provider
        self._model = model

    def run_due_once(self, *, as_of: datetime) -> ResearchSchedulerResult:
        runs: list[ResearchRun] = []
        errors: list[ResearchSchedulerError] = []
        for item in self._due_items(as_of):
            if not self._trading_calendar.is_research_time(
                as_of=as_of,
                schedule_time=item.schedule_time,
                timezone_name=item.schedule_timezone,
            ):
                self._advance_next_run(item, as_of)
                continue
            try:
                result = self._runtime.run_watchlist_item(
                    watchlist_item_id=item.watchlist_item_id,
                    horizon_days=item.research_horizon_days,
                    as_of=as_of,
                    workflow=self._workflow,
                    provider=self._provider,
                    model=self._model,
                )
                runs.append(result.run)
                self._mark_success(item, as_of)
            except Exception as exc:
                now = utc_now()
                failed_run = ResearchRun(
                    watchlist_item_id=item.watchlist_item_id,
                    symbol=item.symbol,
                    research_window_key=self._research_window_key(item, as_of),
                    current_stage="failed",
                    status="failed",
                    workflow=self._workflow,
                    input_params={
                        "horizon_days": item.research_horizon_days,
                        "as_of": as_of.isoformat(),
                        "workflow": self._workflow,
                        "provider": self._provider,
                        "model": self._model,
                        "symbol": item.symbol,
                        "market": item.market,
                    },
                    failed_stage="research_runtime",
                    error_type=type(exc).__name__,
                    error=str(exc),
                    finished_at=now,
                    created_at=now,
                    updated_at=now,
                )
                self._storage.save(failed_run)
                errors.append(
                    ResearchSchedulerError(
                        watchlist_item_id=item.watchlist_item_id,
                        symbol=item.symbol,
                        error_type=type(exc).__name__,
                        error_message=str(exc),
                    )
                )
        return ResearchSchedulerResult(runs=tuple(runs), errors=tuple(errors))

    def _due_items(self, as_of: datetime) -> list[WatchlistItem]:
        return [
            item
            for item in self._storage.list_watchlist_items(
                status=WatchlistStatus.ACTIVE
            )
            if item.auto_research_enabled
            and item.next_run_at is not None
            and item.next_run_at <= as_of
        ]

    def _mark_success(self, item: WatchlistItem, as_of: datetime) -> None:
        WatchlistService(self._storage).update_item(
            item.watchlist_item_id,
            last_run_at=as_of,
            next_run_at=self._next_run(item, as_of),
        )

    def _advance_next_run(self, item: WatchlistItem, as_of: datetime) -> None:
        WatchlistService(self._storage).update_item(
            item.watchlist_item_id,
            next_run_at=self._next_run(item, as_of),
        )

    def _next_run(self, item: WatchlistItem, as_of: datetime) -> datetime:
        return self._trading_calendar.next_research_at(
            after=as_of,
            schedule_time=item.schedule_time,
            timezone_name=item.schedule_timezone,
        )

    def _research_window_key(self, item: WatchlistItem, as_of: datetime) -> str:
        return (
            f"{item.market}:{item.symbol}:"
            f"{item.research_horizon_days}:{as_of.isoformat()}"
        )
