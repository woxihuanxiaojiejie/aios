from __future__ import annotations

from typing import Any


class AKShareClient:
    def stock_zh_a_hist(
        self,
        *,
        symbol: str,
        period: str,
        start_date: str,
        end_date: str,
        adjust: str,
    ) -> Any:
        import akshare as ak

        return ak.stock_zh_a_hist(
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )

    def stock_zh_a_disclosure_report_cninfo(
        self,
        *,
        symbol: str,
        market: str,
        category: str,
        start_date: str,
        end_date: str,
    ) -> Any:
        import akshare as ak

        return ak.stock_zh_a_disclosure_report_cninfo(
            symbol=symbol,
            market=market,
            category=category,
            start_date=start_date,
            end_date=end_date,
        )
