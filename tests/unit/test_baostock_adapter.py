from __future__ import annotations

from datetime import date

import pytest
from tests.market_helpers import FakeBaoStockClient, baostock_row

from aios.adapters.market_data import Adjustment
from aios.integrations.baostock.adapter import BaoStockMarketDataAdapter
from aios.integrations.baostock.errors import (
    EmptyMarketDataError,
    InvalidMarketDataError,
    MissingMarketDataFieldError,
    UpstreamMarketDataError,
)


def test_baostock_adapter_maps_multiple_rows() -> None:
    client = FakeBaoStockClient(
        [
            baostock_row(date="2026-07-01"),
            baostock_row(date="2026-07-02", close="10.60"),
        ]
    )

    bars = BaoStockMarketDataAdapter(client).fetch_daily_bars(
        "000001.SZ",
        date(2026, 7, 1),
        date(2026, 7, 2),
        Adjustment.QFQ,
    )

    assert [bar.trade_date.isoformat() for bar in bars] == [
        "2026-07-01",
        "2026-07-02",
    ]
    assert client.calls == [
        {
            "code": "sz.000001",
            "start_date": "2026-07-01",
            "end_date": "2026-07-02",
            "adjustflag": "2",
        }
    ]


def test_baostock_adapter_passes_none_adjustment() -> None:
    client = FakeBaoStockClient()

    BaoStockMarketDataAdapter(client).fetch_daily_bars(
        "600000.SH",
        date(2026, 7, 1),
        date(2026, 7, 1),
        Adjustment.NONE,
    )

    assert client.calls[0]["code"] == "sh.600000"
    assert client.calls[0]["adjustflag"] == "3"


def test_baostock_adapter_empty_data_fails() -> None:
    with pytest.raises(EmptyMarketDataError):
        BaoStockMarketDataAdapter(FakeBaoStockClient(rows=[])).fetch_daily_bars(
            "000001.SZ",
            date(2026, 7, 1),
            date(2026, 7, 1),
            Adjustment.NONE,
        )


def test_baostock_adapter_missing_field_fails() -> None:
    row = baostock_row()
    del row["open"]

    with pytest.raises(MissingMarketDataFieldError):
        BaoStockMarketDataAdapter(FakeBaoStockClient([row])).fetch_daily_bars(
            "000001.SZ",
            date(2026, 7, 1),
            date(2026, 7, 1),
            Adjustment.NONE,
        )


def test_baostock_adapter_invalid_field_fails() -> None:
    with pytest.raises(InvalidMarketDataError):
        BaoStockMarketDataAdapter(
            FakeBaoStockClient([baostock_row(close="bad")])
        ).fetch_daily_bars(
            "000001.SZ",
            date(2026, 7, 1),
            date(2026, 7, 1),
            Adjustment.NONE,
        )


def test_baostock_adapter_upstream_error_is_sanitized() -> None:
    with pytest.raises(UpstreamMarketDataError, match="BaoStock"):
        BaoStockMarketDataAdapter(
            FakeBaoStockClient(error=RuntimeError("internal endpoint details"))
        ).fetch_daily_bars(
            "000001.SZ",
            date(2026, 7, 1),
            date(2026, 7, 1),
            Adjustment.NONE,
        )
