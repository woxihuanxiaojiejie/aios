from __future__ import annotations

from datetime import datetime, time

from pydantic import Field

from aios.api.schemas.common import ApiSchema
from aios.kernel.enums import WatchlistStatus
from aios.kernel.watchlist import WatchlistItem


class WatchlistCreateRequest(ApiSchema):
    symbol: str = Field(min_length=1, max_length=64)
    market: str = Field(min_length=1, max_length=64)
    note: str | None = Field(default=None, max_length=500)
    auto_research_enabled: bool = False
    research_horizon_days: int = Field(default=3)
    schedule_time: time = Field(default=time(15, 0))
    schedule_timezone: str = Field(default="Asia/Shanghai", min_length=1, max_length=64)
    next_run_at: datetime | None = None


class WatchlistUpdateRequest(ApiSchema):
    note: str | None = Field(default=None, max_length=500)
    auto_research_enabled: bool | None = None
    research_horizon_days: int | None = None
    schedule_time: time | None = None
    schedule_timezone: str | None = Field(default=None, min_length=1, max_length=64)
    next_run_at: datetime | None = None


class WatchlistItemResponse(ApiSchema):
    watchlist_item_id: str
    symbol: str
    market: str
    note: str | None
    status: WatchlistStatus
    auto_research_enabled: bool
    research_horizon_days: int
    schedule_time: time
    schedule_timezone: str
    next_run_at: datetime | None
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


def watchlist_item_response(item: WatchlistItem) -> WatchlistItemResponse:
    return WatchlistItemResponse.model_validate(item.model_dump())
