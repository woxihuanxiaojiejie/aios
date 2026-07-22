from __future__ import annotations

from datetime import datetime

from pydantic import Field

from aios.api.schemas.common import ApiSchema
from aios.kernel.enums import WatchlistStatus
from aios.kernel.watchlist import WatchlistItem


class WatchlistCreateRequest(ApiSchema):
    symbol: str = Field(min_length=1, max_length=64)
    market: str = Field(min_length=1, max_length=64)
    note: str | None = Field(default=None, max_length=500)


class WatchlistUpdateRequest(ApiSchema):
    note: str | None = Field(default=None, max_length=500)


class WatchlistItemResponse(ApiSchema):
    watchlist_item_id: str
    symbol: str
    market: str
    note: str | None
    status: WatchlistStatus
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


def watchlist_item_response(item: WatchlistItem) -> WatchlistItemResponse:
    return WatchlistItemResponse.model_validate(item.model_dump())
