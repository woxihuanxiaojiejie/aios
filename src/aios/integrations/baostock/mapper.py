from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from aios.adapters.market_data import Adjustment, MarketBar
from aios.adapters.market_errors import (
    InvalidMarketDataError,
    MissingMarketDataFieldError,
    UnsupportedMarketSymbolError,
)
from aios.adapters.market_evidence import market_bar_content_hash

SOURCE = "baostock.query_history_k_data_plus"
REQUIRED_FIELDS = (
    "date",
    "code",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "adjustflag",
)


def baostock_symbol(symbol: str) -> str:
    if symbol.endswith(".SZ"):
        code = symbol.removesuffix(".SZ")
        if len(code) == 6 and code.isdigit():
            return f"sz.{code}"
    if symbol.endswith(".SH"):
        code = symbol.removesuffix(".SH")
        if len(code) == 6 and code.isdigit():
            return f"sh.{code}"
    msg = f"Only .SZ and .SH A-share symbols are supported: {symbol}"
    raise UnsupportedMarketSymbolError(msg)


def standard_symbol(code: str) -> str:
    if code.startswith("sz.") and len(code) == 9:
        return f"{code[3:]}.SZ"
    if code.startswith("sh.") and len(code) == 9:
        return f"{code[3:]}.SH"
    msg = f"Only BaoStock sz. and sh. A-share codes are supported: {code}"
    raise UnsupportedMarketSymbolError(msg)


def baostock_adjustflag(adjustment: Adjustment) -> str:
    return {
        Adjustment.HFQ: "1",
        Adjustment.QFQ: "2",
        Adjustment.NONE: "3",
    }[adjustment]


def row_to_market_bar(
    row: dict[str, Any],
    *,
    adjustment: Adjustment,
    fetched_at: datetime,
) -> MarketBar:
    missing = [field for field in REQUIRED_FIELDS if field not in row]
    if missing:
        msg = f"BaoStock row is missing required fields: {', '.join(missing)}"
        raise MissingMarketDataFieldError(msg)
    try:
        return MarketBar(
            symbol=standard_symbol(str(row["code"])),
            market="CN_A",
            trade_date=_parse_trade_date(row["date"]),
            open=_decimal(row["open"]),
            high=_decimal(row["high"]),
            low=_decimal(row["low"]),
            close=_decimal(row["close"]),
            volume=_decimal(row["volume"]),
            amount=_optional_decimal(row["amount"]),
            adjustment=adjustment,
            source=SOURCE,
            fetched_at=fetched_at,
        )
    except (
        InvalidOperation,
        TypeError,
        ValueError,
        ValidationError,
        UnsupportedMarketSymbolError,
    ) as exc:
        msg = "BaoStock row contains invalid market data"
        raise InvalidMarketDataError(msg) from exc


def _parse_trade_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None or str(value) == "":
        return None
    return _decimal(value)


__all__ = [
    "SOURCE",
    "baostock_adjustflag",
    "baostock_symbol",
    "market_bar_content_hash",
    "row_to_market_bar",
    "standard_symbol",
]
