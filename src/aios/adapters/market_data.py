from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Adjustment(StrEnum):
    NONE = "none"
    QFQ = "qfq"
    HFQ = "hfq"


class MarketBar(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(min_length=1)
    market: Literal["CN_A"]
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    amount: Decimal | None = None
    adjustment: Adjustment
    source: str
    fetched_at: datetime

    @field_validator("fetched_at")
    @classmethod
    def validate_fetched_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "fetched_at must include timezone"
            raise ValueError(msg)
        return value.astimezone(UTC)

    @field_validator("volume")
    @classmethod
    def validate_volume(cls, value: Decimal) -> Decimal:
        if value < 0:
            msg = "volume must not be negative"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_ohlc(self) -> MarketBar:
        if self.high < max(self.open, self.close, self.low):
            msg = "high must not be lower than open, close, or low"
            raise ValueError(msg)
        if self.low > min(self.open, self.close, self.high):
            msg = "low must not be higher than open, close, or high"
            raise ValueError(msg)
        return self


class MarketDataAdapter(Protocol):
    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: Adjustment,
    ) -> list[MarketBar]:
        """Fetch normalized daily market bars."""
