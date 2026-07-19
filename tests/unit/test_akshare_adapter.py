from __future__ import annotations

from datetime import date

import pytest
from tests.market_helpers import FakeAKShareClient, FakeDataFrame, akshare_row

from aios.adapters.market_data import Adjustment
from aios.integrations.akshare.adapter import AKShareMarketDataAdapter
from aios.integrations.akshare.errors import (
    EmptyMarketDataError,
    InvalidMarketDataError,
    MissingMarketDataFieldError,
    UpstreamMarketDataError,
)


def test_fetch_daily_bars_maps_normal_dataframe() -> None:
    client = FakeAKShareClient(FakeDataFrame([akshare_row()]))
    adapter = AKShareMarketDataAdapter(client=client)

    bars = adapter.fetch_daily_bars(
        "000001.SZ",
        date(2026, 7, 1),
        date(2026, 7, 18),
        Adjustment.QFQ,
    )

    assert len(bars) == 1
    assert bars[0].symbol == "000001.SZ"
    assert client.calls == [
        {
            "symbol": "000001",
            "period": "daily",
            "start_date": "20260701",
            "end_date": "20260718",
            "adjust": "qfq",
        }
    ]


def test_empty_dataframe_fails() -> None:
    adapter = AKShareMarketDataAdapter(client=FakeAKShareClient(FakeDataFrame([])))

    with pytest.raises(EmptyMarketDataError):
        adapter.fetch_daily_bars(
            "000001.SZ",
            date(2026, 7, 1),
            date(2026, 7, 18),
            Adjustment.NONE,
        )


def test_missing_columns_fail() -> None:
    adapter = AKShareMarketDataAdapter(
        client=FakeAKShareClient(FakeDataFrame([{"日期": "2026-07-01"}]))
    )

    with pytest.raises(MissingMarketDataFieldError):
        adapter.fetch_daily_bars(
            "000001.SZ",
            date(2026, 7, 1),
            date(2026, 7, 18),
            Adjustment.NONE,
        )


def test_invalid_row_fails() -> None:
    adapter = AKShareMarketDataAdapter(
        client=FakeAKShareClient(FakeDataFrame([akshare_row(最高="9.00")]))
    )

    with pytest.raises(InvalidMarketDataError):
        adapter.fetch_daily_bars(
            "000001.SZ",
            date(2026, 7, 1),
            date(2026, 7, 18),
            Adjustment.NONE,
        )


def test_upstream_exception_is_sanitized() -> None:
    adapter = AKShareMarketDataAdapter(
        client=FakeAKShareClient(error=RuntimeError("internal request traceback"))
    )

    with pytest.raises(UpstreamMarketDataError) as exc_info:
        adapter.fetch_daily_bars(
            "000001.SZ",
            date(2026, 7, 1),
            date(2026, 7, 18),
            Adjustment.NONE,
        )

    assert "traceback" not in str(exc_info.value).lower()
