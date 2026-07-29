from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest


@pytest.mark.external_market
def test_real_akshare_cninfo_announcements_smoke() -> None:
    if os.getenv("AIOS_RUN_EXTERNAL_MARKET_TESTS") != "1":
        pytest.skip("set AIOS_RUN_EXTERNAL_MARKET_TESTS=1 to run external market smoke")

    from aios.integrations.akshare.announcements import AKShareAnnouncementsAdapter

    result = AKShareAnnouncementsAdapter().fetch_cninfo_disclosures(
        symbol="000001",
        market="沪深京",
        category="公司治理",
        start_date=date(2023, 6, 19),
        end_date=date(2023, 12, 20),
        persist_dir=Path("results/brain001/announcements"),
    )

    assert result.items
    assert result.raw_response_path is not None
    assert result.raw_response_path.exists()
    assert result.pre_normalized_path is not None
    assert result.pre_normalized_path.exists()
    assert result.items[0].source_trace["provider_name"] == "akshare"
    assert result.items[0].published_at is not None
