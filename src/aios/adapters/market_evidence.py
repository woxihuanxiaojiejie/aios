from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from aios.adapters.market_data import Adjustment, MarketBar
from aios.kernel.evidence import Evidence

CN_A_CLOSE = time(15, 0)
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


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
        source=bar.source,
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
            **_provider_metadata(bar),
            "adjustment": bar.adjustment.value,
            "availability_semantics": "retrieval_time",
            "historical_point_in_time_guarantee": False,
            "market_bar": normalized_market_bar(bar),
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


def _provider_metadata(bar: MarketBar) -> dict[str, object]:
    if bar.source == "akshare.stock_zh_a_hist":
        return {
            "provider": "akshare",
            "source_function": bar.source,
            "raw_field_mapping": {
                "日期": "trade_date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
                "成交额": "amount",
            },
        }
    if bar.source == "baostock.query_history_k_data_plus":
        return {
            "provider": "baostock",
            "source_function": bar.source,
            "provider_adjustflag": _baostock_adjustflag(bar.adjustment),
            "raw_field_mapping": {
                "date": "trade_date",
                "code": "symbol",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
                "amount": "amount",
                "adjustflag": "provider_adjustflag",
            },
        }
    return {"provider": "unknown", "source_function": bar.source}


def _baostock_adjustflag(adjustment: Adjustment) -> str:
    return {
        Adjustment.HFQ: "1",
        Adjustment.QFQ: "2",
        Adjustment.NONE: "3",
    }[adjustment]
