from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from tests.market_helpers import akshare_row, market_bar

from aios.adapters.market_data import Adjustment, MarketBar
from aios.integrations.akshare.errors import (
    InvalidMarketDataError,
    MissingMarketDataFieldError,
    UnsupportedMarketSymbolError,
)
from aios.integrations.akshare.mapper import (
    akshare_adjustment,
    akshare_symbol,
    market_bar_content_hash,
    market_bar_to_evidence,
    row_to_market_bar,
)


def test_symbol_conversion_for_supported_a_share_markets() -> None:
    assert akshare_symbol("000001.SZ") == "000001"
    assert akshare_symbol("600000.SH") == "600000"


@pytest.mark.parametrize("symbol", ["430001.BJ", "00700.HK", "AAPL.US", "000001"])
def test_symbol_conversion_rejects_unsupported_markets(symbol: str) -> None:
    with pytest.raises(UnsupportedMarketSymbolError):
        akshare_symbol(symbol)


def test_adjustment_mapping() -> None:
    assert akshare_adjustment(Adjustment.NONE) == ""
    assert akshare_adjustment(Adjustment.QFQ) == "qfq"
    assert akshare_adjustment(Adjustment.HFQ) == "hfq"


def test_chinese_columns_decimal_and_utc_mapping() -> None:
    fetched_at = datetime(2026, 7, 1, 8, 0, tzinfo=UTC)
    bar = row_to_market_bar(
        akshare_row(),
        symbol="000001.SZ",
        adjustment=Adjustment.QFQ,
        fetched_at=fetched_at,
    )

    assert bar.trade_date == date(2026, 7, 1)
    assert bar.open == Decimal("10.10")
    assert bar.high == Decimal("10.80")
    assert bar.low == Decimal("10.00")
    assert bar.close == Decimal("10.50")
    assert bar.volume == Decimal("1000")
    assert bar.amount == Decimal("10500.50")
    assert bar.fetched_at.tzinfo is UTC


def test_missing_column_fails() -> None:
    row = akshare_row()
    del row["成交量"]

    with pytest.raises(MissingMarketDataFieldError):
        row_to_market_bar(
            row,
            symbol="000001.SZ",
            adjustment=Adjustment.QFQ,
            fetched_at=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        )


def test_market_bar_validates_ohlc_and_volume() -> None:
    with pytest.raises(ValueError, match="high"):
        MarketBar(
            **{
                **market_bar().model_dump(),
                "high": Decimal("10.00"),
            }
        )

    with pytest.raises(ValueError, match="volume"):
        MarketBar(
            **{
                **market_bar().model_dump(),
                "volume": Decimal("-1"),
            }
        )


def test_invalid_decimal_fails() -> None:
    with pytest.raises(InvalidMarketDataError):
        row_to_market_bar(
            akshare_row(开盘="bad"),
            symbol="000001.SZ",
            adjustment=Adjustment.QFQ,
            fetched_at=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        )


def test_content_hash_is_stable_and_changes_with_content() -> None:
    bar = market_bar()
    same = market_bar()
    changed = market_bar(close=Decimal("10.51"))

    assert market_bar_content_hash(bar) == market_bar_content_hash(same)
    assert market_bar_content_hash(bar) != market_bar_content_hash(changed)


def test_market_bar_to_evidence_metadata_and_time_semantics() -> None:
    bar = market_bar()
    evidence = market_bar_to_evidence(bar, reliability=0.95)

    assert evidence.evidence_type == "market_daily_bar"
    assert evidence.source == "akshare.stock_zh_a_hist"
    assert evidence.symbols == ("000001.SZ",)
    assert evidence.reliability == 0.95
    assert evidence.published_at.isoformat() == "2026-07-01T07:00:00+00:00"
    assert evidence.available_at == bar.fetched_at
    assert evidence.metadata["market_bar"]["close"] == "10.50"
    assert evidence.metadata["availability_semantics"] == "retrieval_time"
    assert evidence.metadata["historical_point_in_time_guarantee"] is False
