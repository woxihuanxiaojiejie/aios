from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from aios.adapters.market_data import Adjustment, MarketBar
from aios.adapters.market_evidence import (
    market_bar_content_hash as market_bar_content_hash,
)
from aios.adapters.market_evidence import (
    market_bar_to_evidence as market_bar_to_evidence,
)
from aios.adapters.market_evidence import (
    market_close_utc as market_close_utc,
)
from aios.adapters.market_evidence import (
    normalized_market_bar as normalized_market_bar,
)
from aios.integrations.akshare.errors import (
    InvalidMarketDataError,
    MissingMarketDataFieldError,
    UnsupportedMarketSymbolError,
)

SOURCE = "akshare.stock_zh_a_hist"
REQUIRED_COLUMNS = ("日期", "开盘", "收盘", "最高", "最低", "成交量")


def akshare_symbol(symbol: str) -> str:
    if symbol.endswith(".SZ") or symbol.endswith(".SH"):
        code = symbol.split(".", maxsplit=1)[0]
        if len(code) == 6 and code.isdigit():
            return code
    msg = f"Only .SZ and .SH A-share symbols are supported: {symbol}"
    raise UnsupportedMarketSymbolError(msg)


def akshare_adjustment(adjustment: Adjustment) -> str:
    if adjustment is Adjustment.NONE:
        return ""
    return adjustment.value


def row_to_market_bar(
    row: dict[str, Any],
    *,
    symbol: str,
    adjustment: Adjustment,
    fetched_at: datetime,
) -> MarketBar:
    missing = [column for column in REQUIRED_COLUMNS if column not in row]
    if missing:
        msg = f"AKShare row is missing required fields: {', '.join(missing)}"
        raise MissingMarketDataFieldError(msg)
    try:
        return MarketBar(
            symbol=symbol,
            market="CN_A",
            trade_date=_parse_trade_date(row["日期"]),
            open=_decimal(row["开盘"]),
            high=_decimal(row["最高"]),
            low=_decimal(row["最低"]),
            close=_decimal(row["收盘"]),
            volume=_decimal(row["成交量"]),
            amount=_optional_decimal(row.get("成交额")),
            adjustment=adjustment,
            source=SOURCE,
            fetched_at=fetched_at,
        )
    except (InvalidOperation, TypeError, ValueError, ValidationError) as exc:
        msg = "AKShare row contains invalid market data"
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
