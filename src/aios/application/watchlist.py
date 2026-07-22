from __future__ import annotations

from aios.adapters.storage import Storage
from aios.kernel.base import utc_now
from aios.kernel.enums import WatchlistStatus
from aios.kernel.errors import (
    DuplicateEntityError,
    InvalidStateTransitionError,
)
from aios.kernel.watchlist import WatchlistItem


class WatchlistService:
    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def add_item(
        self,
        *,
        symbol: str,
        market: str,
        note: str | None = None,
    ) -> WatchlistItem:
        candidate = WatchlistItem(symbol=symbol, market=market, note=note)
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
        item = self.get_item(item_id)
        replacement = WatchlistItem(
            **{
                **item.model_dump(),
                "note": note,
                "updated_at": utc_now(),
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
