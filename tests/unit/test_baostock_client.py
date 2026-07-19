from __future__ import annotations

import pytest
from tests.market_helpers import baostock_row

from aios.integrations.baostock.client import BaoStockClient
from aios.integrations.baostock.errors import (
    EmptyMarketDataError,
    UpstreamMarketDataError,
)


class FakeLoginResult:
    def __init__(self, error_code: str = "0", error_msg: str = "success") -> None:
        self.error_code = error_code
        self.error_msg = error_msg


class FakeQueryResult:
    def __init__(
        self,
        rows: list[dict[str, str]] | None = None,
        *,
        error_code: str = "0",
        error_msg: str = "success",
    ) -> None:
        self.rows = rows if rows is not None else [baostock_row()]
        self.error_code = error_code
        self.error_msg = error_msg
        self.fields = list(self.rows[0].keys()) if self.rows else []
        self._index = -1

    def next(self) -> bool:
        self._index += 1
        return self._index < len(self.rows)

    def get_row_data(self) -> list[str]:
        return [self.rows[self._index][field] for field in self.fields]


class FakeBaoStockModule:
    def __init__(
        self,
        *,
        login_result: FakeLoginResult | None = None,
        query_result: FakeQueryResult | None = None,
        query_error: Exception | None = None,
    ) -> None:
        self.login_result = login_result or FakeLoginResult()
        self.query_result = query_result or FakeQueryResult()
        self.query_error = query_error
        self.login_called = False
        self.logout_called = False
        self.calls: list[dict[str, str]] = []

    def login(self) -> FakeLoginResult:
        self.login_called = True
        return self.login_result

    def logout(self) -> None:
        self.logout_called = True

    def query_history_k_data_plus(
        self,
        code: str,
        fields: str,
        start_date: str,
        end_date: str,
        frequency: str,
        adjustflag: str,
    ) -> FakeQueryResult:
        self.calls.append(
            {
                "code": code,
                "fields": fields,
                "start_date": start_date,
                "end_date": end_date,
                "frequency": frequency,
                "adjustflag": adjustflag,
            }
        )
        if self.query_error is not None:
            raise self.query_error
        return self.query_result


def test_baostock_client_logs_in_queries_and_logs_out() -> None:
    module = FakeBaoStockModule()

    rows = BaoStockClient(module).query_daily_bars(
        code="sz.000001",
        start_date="2026-07-13",
        end_date="2026-07-17",
        adjustflag="2",
    )

    assert module.login_called is True
    assert module.logout_called is True
    assert rows == [baostock_row()]
    assert module.calls[0]["frequency"] == "d"
    assert module.calls[0]["adjustflag"] == "2"


def test_baostock_client_login_failure_raises_upstream_error() -> None:
    module = FakeBaoStockModule(login_result=FakeLoginResult("100", "login failed"))

    with pytest.raises(UpstreamMarketDataError):
        BaoStockClient(module).query_daily_bars(
            code="sz.000001",
            start_date="2026-07-13",
            end_date="2026-07-17",
            adjustflag="3",
        )

    assert module.logout_called is False


def test_baostock_client_query_error_code_raises_and_logs_out() -> None:
    module = FakeBaoStockModule(query_result=FakeQueryResult(error_code="1"))

    with pytest.raises(UpstreamMarketDataError):
        BaoStockClient(module).query_daily_bars(
            code="sz.000001",
            start_date="2026-07-13",
            end_date="2026-07-17",
            adjustflag="3",
        )

    assert module.logout_called is True


def test_baostock_client_query_exception_logs_out() -> None:
    module = FakeBaoStockModule(query_error=RuntimeError("socket exploded"))

    with pytest.raises(UpstreamMarketDataError):
        BaoStockClient(module).query_daily_bars(
            code="sz.000001",
            start_date="2026-07-13",
            end_date="2026-07-17",
            adjustflag="3",
        )

    assert module.logout_called is True


def test_baostock_client_empty_result_raises() -> None:
    module = FakeBaoStockModule(query_result=FakeQueryResult(rows=[]))

    with pytest.raises(EmptyMarketDataError):
        BaoStockClient(module).query_daily_bars(
            code="sz.000001",
            start_date="2026-07-13",
            end_date="2026-07-17",
            adjustflag="3",
        )
