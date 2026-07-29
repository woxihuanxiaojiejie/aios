from __future__ import annotations

from datetime import datetime, time
from typing import ClassVar

from pydantic import Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.enums import WatchlistStatus


class WatchlistItem(KernelModel):
    id_field: ClassVar[str] = "watchlist_item_id"

    watchlist_item_id: str = Field(default_factory=lambda: new_id("wl_"))
    symbol: str = Field(min_length=1, max_length=64)
    market: str = Field(min_length=1, max_length=64)
    note: str | None = Field(default=None, max_length=500)
    status: WatchlistStatus = WatchlistStatus.ACTIVE
    auto_research_enabled: bool = False
    research_horizon_days: int = Field(default=3)
    schedule_time: time = Field(default=time(15, 0))
    schedule_timezone: str = Field(default="Asia/Shanghai", min_length=1, max_length=64)
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    archived_at: datetime | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            msg = "symbol must not be empty"
            raise ValueError(msg)
        return normalized

    @field_validator("market")
    @classmethod
    def normalize_market(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            msg = "market must not be empty"
            raise ValueError(msg)
        return normalized

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("schedule_timezone")
    @classmethod
    def normalize_timezone(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "schedule_timezone must not be empty"
            raise ValueError(msg)
        return normalized

    @field_validator("research_horizon_days")
    @classmethod
    def validate_horizon(cls, value: int) -> int:
        if value not in {1, 3, 7}:
            msg = "research_horizon_days must be one of 1, 3, or 7"
            raise ValueError(msg)
        return value

    @field_validator(
        "created_at",
        "updated_at",
        "archived_at",
        "next_run_at",
        "last_run_at",
    )
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @model_validator(mode="after")
    def validate_status_times(self) -> WatchlistItem:
        if self.updated_at < self.created_at:
            msg = "updated_at must not be earlier than created_at"
            raise ValueError(msg)
        if self.status is WatchlistStatus.ACTIVE and self.archived_at is not None:
            msg = "active WatchlistItem must not have archived_at"
            raise ValueError(msg)
        if self.status is WatchlistStatus.ARCHIVED and self.archived_at is None:
            msg = "archived WatchlistItem must have archived_at"
            raise ValueError(msg)
        return self
