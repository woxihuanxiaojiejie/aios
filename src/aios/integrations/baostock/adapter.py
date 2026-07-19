from __future__ import annotations

from datetime import UTC, date, datetime

from aios.adapters.market_data import Adjustment, MarketBar
from aios.adapters.market_errors import (
    EmptyMarketDataError,
    InvalidMarketDataError,
    MarketDataDateRangeError,
    MissingMarketDataFieldError,
    UnsupportedMarketSymbolError,
    UpstreamMarketDataError,
)
from aios.integrations.baostock.client import BaoStockClient
from aios.integrations.baostock.mapper import (
    baostock_adjustflag,
    baostock_symbol,
    row_to_market_bar,
)


class BaoStockMarketDataAdapter:
    def __init__(self, client: BaoStockClient | None = None) -> None:
        self._client = client or BaoStockClient()

    def fetch_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjustment: Adjustment,
    ) -> list[MarketBar]:
        if start_date > end_date:
            msg = "start_date must not be later than end_date"
            raise MarketDataDateRangeError(msg)

        fetched_at = datetime.now(UTC)
        try:
            rows = self._client.query_daily_bars(
                code=baostock_symbol(symbol),
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                adjustflag=baostock_adjustflag(adjustment),
            )
        except (
            EmptyMarketDataError,
            MissingMarketDataFieldError,
            InvalidMarketDataError,
            UnsupportedMarketSymbolError,
            UpstreamMarketDataError,
        ):
            raise
        except Exception as exc:
            msg = "BaoStock market data request failed"
            raise UpstreamMarketDataError(msg) from exc

        if not rows:
            msg = "BaoStock returned no market data"
            raise EmptyMarketDataError(msg)
        return [
            row_to_market_bar(
                row,
                adjustment=adjustment,
                fetched_at=fetched_at,
            )
            for row in rows
        ]
