from __future__ import annotations

from typing import Any

from aios.adapters.market_errors import EmptyMarketDataError, UpstreamMarketDataError

FIELDS = (
    "date",
    "code",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "adjustflag",
)


class BaoStockClient:
    def __init__(self, module: Any | None = None) -> None:
        self._module = module

    def query_daily_bars(
        self,
        *,
        code: str,
        start_date: str,
        end_date: str,
        adjustflag: str,
    ) -> list[dict[str, str]]:
        module = self._module or self._import_baostock()
        login_result = module.login()
        if getattr(login_result, "error_code", "") != "0":
            msg = "BaoStock login failed"
            raise UpstreamMarketDataError(msg)

        try:
            result = module.query_history_k_data_plus(
                code,
                ",".join(FIELDS),
                start_date,
                end_date,
                frequency="d",
                adjustflag=adjustflag,
            )
            if getattr(result, "error_code", "") != "0":
                msg = "BaoStock query failed"
                raise UpstreamMarketDataError(msg)
            rows = self._rows_from_result(result)
            if not rows:
                msg = "BaoStock returned no market data"
                raise EmptyMarketDataError(msg)
            return rows
        except (EmptyMarketDataError, UpstreamMarketDataError):
            raise
        except Exception as exc:
            msg = "BaoStock market data request failed"
            raise UpstreamMarketDataError(msg) from exc
        finally:
            module.logout()

    def _rows_from_result(self, result: Any) -> list[dict[str, str]]:
        fields = list(getattr(result, "fields", []))
        rows: list[dict[str, str]] = []
        while result.next():
            rows.append(dict(zip(fields, result.get_row_data(), strict=True)))
        return rows

    def _import_baostock(self) -> Any:
        import baostock as bs  # type: ignore[import-untyped]

        return bs
