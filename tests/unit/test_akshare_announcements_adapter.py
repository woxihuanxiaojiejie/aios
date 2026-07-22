from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "akshare"
    / "announcements_cninfo_000001.json"
)


def test_akshare_announcements_adapter_maps_real_cninfo_fixture(
    tmp_path: Path,
) -> None:
    from aios.integrations.akshare.announcements import (
        AKShareAnnouncementsAdapter,
    )

    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    fetched_at = datetime(2026, 7, 22, 10, 30, tzinfo=UTC)

    result = AKShareAnnouncementsAdapter(client=Client(rows)).fetch_cninfo_disclosures(
        symbol="000001",
        market="沪深京",
        category="公司治理",
        start_date=date(2023, 6, 19),
        end_date=date(2023, 12, 20),
        fetched_at=fetched_at,
        persist_dir=tmp_path,
    )

    assert result.provider_name == "akshare"
    assert result.source_function == "stock_zh_a_disclosure_report_cninfo"
    assert result.fetched_at == fetched_at
    assert result.raw_response_path is not None
    assert result.raw_response_path.exists()
    assert result.pre_normalized_path is not None
    assert result.pre_normalized_path.exists()
    assert result.items

    item = result.items[0]
    assert item.symbol == "000001"
    assert item.short_name == "平安银行"
    assert item.title == "独立董事审核意见"
    assert item.published_at == datetime(2023, 12, 9, tzinfo=UTC)
    assert item.collected_at == fetched_at
    assert item.raw_row == rows[0]
    assert item.source_trace["provider_name"] == "akshare"
    assert item.source_trace["source_function"] == result.source_function
    assert item.source_trace["announcement_url"].startswith("http://www.cninfo.com.cn")


def test_akshare_announcements_fetch_many_keeps_provider_failures_local() -> None:
    from aios.integrations.akshare.announcements import AKShareAnnouncementsAdapter

    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    batch = AKShareAnnouncementsAdapter(client=Client(rows, fail_symbol="000002"))
    result = batch.fetch_many_cninfo_disclosures(
        [
            ("000001", "公司治理"),
            ("000002", "公司治理"),
        ],
        market="沪深京",
        start_date=date(2023, 6, 19),
        end_date=date(2023, 12, 20),
        fetched_at=datetime(2026, 7, 22, 10, 30, tzinfo=UTC),
    )

    assert len(result.results) == 1
    assert result.results[0].symbol == "000001"
    assert len(result.errors) == 1
    assert result.errors[0].symbol == "000002"
    assert "provider unavailable" in result.errors[0].message


class Client:
    def __init__(self, rows: list[dict[str, Any]], fail_symbol: str = "") -> None:
        self._rows = rows
        self._fail_symbol = fail_symbol

    def stock_zh_a_disclosure_report_cninfo(
        self,
        *,
        symbol: str,
        market: str,
        category: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        if symbol == self._fail_symbol:
            raise RuntimeError("provider unavailable")
        assert market == "沪深京"
        assert category == "公司治理"
        assert start_date == "20230619"
        assert end_date == "20231220"
        return self._rows
