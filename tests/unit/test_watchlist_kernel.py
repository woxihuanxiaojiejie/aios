from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from aios.application.watchlist import WatchlistService
from aios.kernel.errors import (
    DuplicateEntityError,
    InvalidStateTransitionError,
    MissingEntityError,
)
from aios.kernel.watchlist import WatchlistItem, WatchlistStatus
from aios.storage.memory import InMemoryStorage


def test_watchlist_item_normalizes_symbol_market_and_note() -> None:
    item = WatchlistItem(symbol=" 600519 ", market=" cn ", note="  observe ")

    assert item.watchlist_item_id.startswith("wl_")
    assert item.symbol == "600519"
    assert item.market == "CN"
    assert item.note == "observe"
    assert item.status is WatchlistStatus.ACTIVE
    assert item.archived_at is None
    assert item.created_at.tzinfo is UTC
    assert item.updated_at.tzinfo is UTC


def test_watchlist_item_rejects_empty_symbol_and_market() -> None:
    with pytest.raises(ValidationError):
        WatchlistItem(symbol=" ", market="CN")

    with pytest.raises(ValidationError):
        WatchlistItem(symbol="600519", market=" ")


def test_watchlist_item_validates_archived_at_semantics() -> None:
    archived_at = datetime(2026, 7, 22, 8, 0, tzinfo=UTC)
    archived = WatchlistItem(
        symbol="600519",
        market="CN",
        status=WatchlistStatus.ARCHIVED,
        archived_at=archived_at,
    )

    assert archived.archived_at == archived_at

    with pytest.raises(ValidationError, match="active WatchlistItem"):
        WatchlistItem(
            symbol="600519",
            market="CN",
            archived_at=archived_at,
        )

    with pytest.raises(ValidationError, match="archived WatchlistItem"):
        WatchlistItem(
            symbol="600519",
            market="CN",
            status=WatchlistStatus.ARCHIVED,
        )


def test_watchlist_service_add_update_archive_restore() -> None:
    service = WatchlistService(InMemoryStorage())

    item = service.add_item(symbol=" 600519 ", market=" cn ", note="  first ")
    assert item.symbol == "600519"
    assert item.market == "CN"
    assert item.note == "first"

    with pytest.raises(DuplicateEntityError):
        service.add_item(symbol="600519", market="CN")

    other_market = service.add_item(symbol="600519", market="HK")
    assert other_market.market == "HK"

    updated = service.update_note(item.watchlist_item_id, note="  new note ")
    assert updated.note == "new note"
    assert updated.symbol == item.symbol
    assert updated.market == item.market
    assert updated.created_at == item.created_at
    assert updated.updated_at >= item.updated_at

    with pytest.raises(MissingEntityError):
        service.update_note("wl_missing", note="x")

    archived = service.archive_item(item.watchlist_item_id)
    assert archived.status is WatchlistStatus.ARCHIVED
    assert archived.archived_at is not None
    assert service.get_item(item.watchlist_item_id) == archived
    assert service.list_items() == [other_market]
    assert service.list_items(status=WatchlistStatus.ARCHIVED) == [archived]

    with pytest.raises(InvalidStateTransitionError):
        service.archive_item(item.watchlist_item_id)

    restored = service.restore_item(item.watchlist_item_id)
    assert restored.status is WatchlistStatus.ACTIVE
    assert restored.archived_at is None
    assert set(service.list_items()) == {other_market, restored}

    with pytest.raises(InvalidStateTransitionError):
        service.restore_item(item.watchlist_item_id)


def test_watchlist_restore_conflicts_with_existing_active_item() -> None:
    service = WatchlistService(InMemoryStorage())
    first = service.add_item(symbol="600519", market="CN")
    archived = service.archive_item(first.watchlist_item_id)
    second = service.add_item(symbol="600519", market="CN")

    with pytest.raises(DuplicateEntityError):
        service.restore_item(archived.watchlist_item_id)

    assert service.get_item(second.watchlist_item_id).status is WatchlistStatus.ACTIVE


def test_watchlist_storage_filters_and_active_lookup() -> None:
    storage = InMemoryStorage()
    service = WatchlistService(storage)
    first = service.add_item(symbol="600519", market="CN")
    second = service.add_item(symbol="0700", market="HK")
    archived = service.archive_item(first.watchlist_item_id)

    assert storage.get(WatchlistItem, first.watchlist_item_id) == archived
    assert storage.find_active_watchlist_item("CN", "600519") is None
    assert storage.find_active_watchlist_item("HK", "0700") == second
    assert storage.list_watchlist_items() == [second]
    assert storage.list_watchlist_items(status=WatchlistStatus.ARCHIVED) == [archived]
    assert storage.list_watchlist_items(market="HK") == [second]
    assert storage.list_watchlist_items(symbol="0700") == [second]

    restored = service.restore_item(first.watchlist_item_id)
    assert restored in storage.list_watchlist_items(status=WatchlistStatus.ACTIVE)
