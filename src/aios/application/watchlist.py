from __future__ import annotations

from datetime import datetime, time

from aios.adapters.storage import Storage
from aios.kernel.base import utc_now
from aios.kernel.enums import WatchlistStatus
from aios.kernel.errors import (
    DuplicateEntityError,
    InvalidStateTransitionError,
)
from aios.kernel.watchlist import WatchlistItem


class _Unset:
    pass


_UNSET = _Unset()


class WatchlistService:
    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def add_item(
        self,
        *,
        symbol: str,
        market: str,
        note: str | None = None,
        auto_research_enabled: bool = False,
        research_horizon_days: int = 3,
        schedule_time: time = time(15, 0),
        schedule_timezone: str = "Asia/Shanghai",
        next_run_at: datetime | None = None,
    ) -> WatchlistItem:
        candidate = WatchlistItem(
            symbol=symbol,
            market=market,
            note=note,
            auto_research_enabled=auto_research_enabled,
            research_horizon_days=research_horizon_days,
            schedule_time=schedule_time,
            schedule_timezone=schedule_timezone,
            next_run_at=next_run_at,
        )
        self._ensure_no_active_duplicate(candidate.market, candidate.symbol)
        self._storage.save(candidate)
        return candidate

    def get_item(self, item_id: str) -> WatchlistItem:
        return self._storage.get(WatchlistItem, item_id)

    def list_items(
        self,
        *,
        status: WatchlistStatus | None = WatchlistStatus.ACTIVE,
        market: str | None = None,
        symbol: str | None = None,
    ) -> list[WatchlistItem]:
        normalized_market = _normalize_optional(market)
        normalized_symbol = _normalize_optional(symbol)
        return self._storage.list_watchlist_items(
            status=status,
            market=normalized_market,
            symbol=normalized_symbol,
        )

    def update_note(self, item_id: str, *, note: str | None) -> WatchlistItem:
        return self.update_item(item_id, note=note)

    def update_item(
        self,
        item_id: str,
        *,
        note: str | None | object = _UNSET,
        auto_research_enabled: bool | object = _UNSET,
        research_horizon_days: int | object = _UNSET,
        schedule_time: time | object = _UNSET,
        schedule_timezone: str | object = _UNSET,
        next_run_at: datetime | None | object = _UNSET,
        last_run_at: datetime | None | object = _UNSET,
    ) -> WatchlistItem:
        item = self.get_item(item_id)
        updates: dict[str, object] = {"updated_at": utc_now()}
        for key, value in {
            "note": note,
            "auto_research_enabled": auto_research_enabled,
            "research_horizon_days": research_horizon_days,
            "schedule_time": schedule_time,
            "schedule_timezone": schedule_timezone,
            "next_run_at": next_run_at,
            "last_run_at": last_run_at,
        }.items():
            if value is not _UNSET:
                updates[key] = value
        replacement = WatchlistItem(
            **{
                **item.model_dump(),
                **updates,
            }
        )
        self._storage.replace(replacement)
        return replacement

    def archive_item(self, item_id: str) -> WatchlistItem:
        item = self.get_item(item_id)
        if item.status is WatchlistStatus.ARCHIVED:
            msg = f"WatchlistItem {item_id} is already archived"
            raise InvalidStateTransitionError(msg)
        now = utc_now()
        replacement = WatchlistItem(
            **{
                **item.model_dump(),
                "status": WatchlistStatus.ARCHIVED,
                "updated_at": now,
                "archived_at": now,
            }
        )
        self._storage.replace(replacement)
        return replacement

    def restore_item(self, item_id: str) -> WatchlistItem:
        item = self.get_item(item_id)
        if item.status is WatchlistStatus.ACTIVE:
            msg = f"WatchlistItem {item_id} is already active"
            raise InvalidStateTransitionError(msg)
        self._ensure_no_active_duplicate(item.market, item.symbol)
        replacement = WatchlistItem(
            **{
                **item.model_dump(),
                "status": WatchlistStatus.ACTIVE,
                "updated_at": utc_now(),
                "archived_at": None,
            }
        )
        self._storage.replace(replacement)
        return replacement

    def _ensure_no_active_duplicate(self, market: str, symbol: str) -> None:
        existing = self._storage.find_active_watchlist_item(market, symbol)
        if existing is None:
            return
        msg = f"Active WatchlistItem for {market}:{symbol} already exists"
        raise DuplicateEntityError(msg)


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None
