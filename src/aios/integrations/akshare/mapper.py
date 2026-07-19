from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from aios.adapters.market_data import Adjustment, MarketBar
from aios.integrations.akshare.errors import (
    InvalidMarketDataError,
    MissingMarketDataFieldError,
    UnsupportedMarketSymbolError,
)
from aios.kernel.evidence import Evidence

SOURCE = "akshare.stock_zh_a_hist"
CN_A_CLOSE = time(15, 0)
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
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


def market_bar_to_evidence(bar: MarketBar, *, reliability: float) -> Evidence:
    published_at = market_close_utc(bar.trade_date)
    if bar.trade_date > datetime.now(SHANGHAI_TZ).date():
        msg = "future market bars cannot be imported as Evidence"
        raise ValueError(msg)
    if bar.fetched_at < published_at:
        msg = "market bar is not yet available at fetched_at"
        raise ValueError(msg)

    content_hash = market_bar_content_hash(bar)
    return Evidence(
        evidence_type="market_daily_bar",
        source=SOURCE,
        symbols=(bar.symbol,),
        published_at=published_at,
        available_at=bar.fetched_at,
        summary=(
            f"{bar.market} {bar.symbol} {bar.trade_date.isoformat()} "
            f"close {bar.close} volume {bar.volume} adjustment {bar.adjustment.value}"
        ),
        reliability=reliability,
        content_hash=content_hash,
        metadata={
            "provider": "akshare",
            "source_function": SOURCE,
            "adjustment": bar.adjustment.value,
            "availability_semantics": "retrieval_time",
            "historical_point_in_time_guarantee": False,
            "market_bar": normalized_market_bar(bar),
            "raw_field_mapping": {
                "日期": "trade_date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
                "成交额": "amount",
            },
            "content_hash": content_hash,
        },
    )


def normalized_market_bar(bar: MarketBar) -> dict[str, str | None]:
    return {
        "symbol": bar.symbol,
        "market": bar.market,
        "trade_date": bar.trade_date.isoformat(),
        "open": str(bar.open),
        "high": str(bar.high),
        "low": str(bar.low),
        "close": str(bar.close),
        "volume": str(bar.volume),
        "amount": str(bar.amount) if bar.amount is not None else None,
        "adjustment": bar.adjustment.value,
        "source": bar.source,
        "fetched_at": bar.fetched_at.isoformat(),
    }


def market_bar_content_hash(bar: MarketBar) -> str:
    normalized = normalized_market_bar(bar)
    normalized.pop("fetched_at")
    payload = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def market_close_utc(trade_date: date) -> datetime:
    return datetime.combine(trade_date, CN_A_CLOSE, tzinfo=SHANGHAI_TZ).astimezone(UTC)


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
