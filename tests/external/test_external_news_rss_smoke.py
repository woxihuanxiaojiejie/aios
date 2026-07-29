from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.mark.external_news
def test_real_bbc_business_rss_feedparser_smoke() -> None:
    if os.getenv("AIOS_RUN_EXTERNAL_NEWS_TESTS") != "1":
        pytest.skip("set AIOS_RUN_EXTERNAL_NEWS_TESTS=1 to run external news smoke")

    from aios.integrations.rss.adapter import FeedparserRSSAdapter

    result = FeedparserRSSAdapter().fetch(
        feed_url="https://feeds.bbci.co.uk/news/business/rss.xml",
        source_id="bbc-business",
        persist_dir=Path("results/brain001/rss"),
    )

    assert result.provider_name == "feedparser"
    assert result.raw_response_path is not None
    assert result.raw_response_path.exists()
    assert result.pre_normalized_path is not None
    assert result.pre_normalized_path.exists()
    assert result.items
    assert result.items[0].source_trace["provider_name"] == "feedparser"
    assert result.items[0].published_at is not None
