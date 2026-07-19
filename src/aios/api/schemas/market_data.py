from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from aios.adapters.market_data import Adjustment, MarketBar


class MarketDataImportRequest(BaseModel):
    symbol: str
    start_date: date
    end_date: date
    adjustment: Adjustment


class MarketBarResponse(BaseModel):
    symbol: str
    market: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    amount: Decimal | None
    adjustment: Adjustment
    source: str
    fetched_at: datetime


class MarketBarPreviewResponse(BaseModel):
    items: list[MarketBarResponse]
    count: int


class MarketDataImportResponse(BaseModel):
    symbol: str
    requested: int
    created: int
    existing: int
    evidence_ids: list[str]


def market_bar_response(bar: MarketBar) -> MarketBarResponse:
    return MarketBarResponse.model_validate(bar.model_dump())
