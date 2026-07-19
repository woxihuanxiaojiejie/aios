from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from tests.market_helpers import baostock_row

from aios.adapters.market_data import Adjustment
from aios.adapters.market_evidence import market_bar_content_hash
from aios.integrations.baostock.errors import (
    InvalidMarketDataError,
    MissingMarketDataFieldError,
    UnsupportedMarketSymbolError,
)
from aios.integrations.baostock.mapper import (
    baostock_adjustflag,
    baostock_symbol,
    row_to_market_bar,
    standard_symbol,
)


def test_baostock_symbol_maps_sz_and_sh() -> None:
    assert baostock_symbol("000001.SZ") == "sz.000001"
    assert baostock_symbol("600000.SH") == "sh.600000"


def test_baostock_symbol_rejects_unsupported_market() -> None:
    with pytest.raises(UnsupportedMarketSymbolError):
        baostock_symbol("00700.HK")


def test_standard_symbol_restores_aios_symbol() -> None:
    assert standard_symbol("sz.000001") == "000001.SZ"
    assert standard_symbol("sh.600000") == "600000.SH"


def test_baostock_adjustflag_mapping() -> None:
    assert baostock_adjustflag(Adjustment.NONE) == "3"
    assert baostock_adjustflag(Adjustment.QFQ) == "2"
    assert baostock_adjustflag(Adjustment.HFQ) == "1"


def test_baostock_row_maps_strings_to_market_bar() -> None:
    fetched_at = datetime(2026, 7, 1, 8, 0, tzinfo=UTC)

    bar = row_to_market_bar(
        baostock_row(),
        adjustment=Adjustment.QFQ,
        fetched_at=fetched_at,
    )

    assert bar.symbol == "000001.SZ"
    assert bar.open == Decimal("10.10")
    assert bar.high == Decimal("10.80")
    assert bar.low == Decimal("10.00")
    assert bar.close == Decimal("10.50")
    assert bar.volume == Decimal("1000")
    assert bar.amount == Decimal("10500.50")
    assert bar.fetched_at.tzinfo == UTC


def test_baostock_empty_amount_maps_to_none() -> None:
    bar = row_to_market_bar(
        baostock_row(amount=""),
        adjustment=Adjustment.NONE,
        fetched_at=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
    )

    assert bar.amount is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("open", "not-a-price"),
        ("volume", "-1"),
        ("high", "9.00"),
    ],
)
def test_baostock_invalid_market_data_fails(field: str, value: str) -> None:
    with pytest.raises(InvalidMarketDataError):
        row_to_market_bar(
            baostock_row(**{field: value}),
            adjustment=Adjustment.QFQ,
            fetched_at=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        )


def test_baostock_missing_required_field_fails() -> None:
    row = baostock_row()
    del row["close"]

    with pytest.raises(MissingMarketDataFieldError):
        row_to_market_bar(
            row,
            adjustment=Adjustment.QFQ,
            fetched_at=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        )


def test_baostock_content_hash_is_stable() -> None:
    fetched_at = datetime(2026, 7, 1, 8, 0, tzinfo=UTC)
    first = row_to_market_bar(
        baostock_row(),
        adjustment=Adjustment.QFQ,
        fetched_at=fetched_at,
    )
    second = row_to_market_bar(
        baostock_row(),
        adjustment=Adjustment.QFQ,
        fetched_at=fetched_at,
    )
    changed = row_to_market_bar(
        baostock_row(close="10.60"),
        adjustment=Adjustment.QFQ,
        fetched_at=fetched_at,
    )

    assert market_bar_content_hash(first) == market_bar_content_hash(second)
    assert market_bar_content_hash(first) != market_bar_content_hash(changed)
