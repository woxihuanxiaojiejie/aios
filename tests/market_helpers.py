from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from aios.adapters.market_data import Adjustment, MarketBar


class FakeDataFrame:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.columns = list(rows[0].keys()) if rows else []
        self.empty = not rows

    def iterrows(self) -> list[tuple[int, dict[str, Any]]]:
        return list(enumerate(self._rows))


class FakeAKShareClient:
    def __init__(
        self,
        frame: FakeDataFrame | None = None,
        error: Exception | None = None,
    ) -> None:
        self.frame = frame or FakeDataFrame([akshare_row()])
        self.error = error
        self.calls: list[dict[str, str]] = []

    def stock_zh_a_hist(
        self,
        *,
        symbol: str,
        period: str,
        start_date: str,
        end_date: str,
        adjust: str,
    ) -> FakeDataFrame:
        self.calls.append(
            {
                "symbol": symbol,
                "period": period,
                "start_date": start_date,
                "end_date": end_date,
                "adjust": adjust,
            }
        )
        if self.error is not None:
            raise self.error
        return self.frame


def akshare_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "日期": "2026-07-01",
        "开盘": "10.10",
        "收盘": "10.50",
        "最高": "10.80",
        "最低": "10.00",
        "成交量": "1000",
        "成交额": "10500.50",
    }
    row.update(overrides)
    return row


def market_bar(
    *,
    trade_date: date = date(2026, 7, 1),
    close: Decimal = Decimal("10.50"),
    fetched_at: datetime = datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
) -> MarketBar:
    return MarketBar(
        symbol="000001.SZ",
        market="CN_A",
        trade_date=trade_date,
        open=Decimal("10.10"),
        high=Decimal("10.80"),
        low=Decimal("10.00"),
        close=close,
        volume=Decimal("1000"),
        amount=Decimal("10500.50"),
        adjustment=Adjustment.QFQ,
        source="akshare.stock_zh_a_hist",
        fetched_at=fetched_at,
    )


def tomorrow_before_close() -> datetime:
    return datetime.now(UTC) + timedelta(days=1)
