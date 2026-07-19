from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from aios.adapters.market_data import Adjustment, MarketBar
from aios.integrations.akshare.client import AKShareClient
from aios.integrations.akshare.errors import (
    EmptyMarketDataError,
    MarketDataDateRangeError,
    MissingMarketDataFieldError,
    UnsupportedMarketSymbolError,
    UpstreamMarketDataError,
)
from aios.integrations.akshare.mapper import (
    akshare_adjustment,
    akshare_symbol,
    row_to_market_bar,
)


class AKShareMarketDataAdapter:
    def __init__(self, client: AKShareClient | None = None) -> None:
        self._client = client or AKShareClient()

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
            frame = self._client.stock_zh_a_hist(
                symbol=akshare_symbol(symbol),
                period="daily",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust=akshare_adjustment(adjustment),
            )
        except UpstreamMarketDataError:
            raise
        except (
            EmptyMarketDataError,
            MissingMarketDataFieldError,
            UnsupportedMarketSymbolError,
        ):
            raise
        except Exception as exc:
            msg = "AKShare market data request failed"
            raise UpstreamMarketDataError(msg) from exc

        if getattr(frame, "empty", False):
            msg = "AKShare returned no market data"
            raise EmptyMarketDataError(msg)

        self._require_columns(frame)
        return [
            row_to_market_bar(
                dict(row),
                symbol=symbol,
                adjustment=adjustment,
                fetched_at=fetched_at,
            )
            for _index, row in frame.iterrows()
        ]

    def _require_columns(self, frame: Any) -> None:
        columns = set(getattr(frame, "columns", []))
        required = {"日期", "开盘", "收盘", "最高", "最低", "成交量"}
        missing = sorted(required - columns)
        if missing:
            msg = f"AKShare response is missing required fields: {', '.join(missing)}"
            raise MissingMarketDataFieldError(msg)
