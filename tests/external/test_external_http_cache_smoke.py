from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.mark.external_news
def test_real_rss_requests_cache_smoke(tmp_path: Path) -> None:
    if os.getenv("AIOS_RUN_EXTERNAL_NEWS_TESTS") != "1":
        pytest.skip("set AIOS_RUN_EXTERNAL_NEWS_TESTS=1 to run external news smoke")

    from aios.integrations.http_client import HTTPClientConfig
    from aios.integrations.rss.adapter import FeedparserRSSAdapter, UrllibRSSHTTPClient

    client = UrllibRSSHTTPClient(
        http_config=HTTPClientConfig(
            cache_enabled=True,
            cache_name=tmp_path / "rss-http-cache",
            expire_after_seconds=300,
        )
    )
    adapter = FeedparserRSSAdapter(http_client=client)

    first = adapter.fetch(
        feed_url="https://feeds.bbci.co.uk/news/business/rss.xml",
        source_id="bbc-business",
        persist_dir=Path("results/brain001/cache/rss"),
    )
    second = adapter.fetch(
        feed_url="https://feeds.bbci.co.uk/news/business/rss.xml",
        source_id="bbc-business",
        persist_dir=Path("results/brain001/cache/rss"),
    )

    assert first.response_from_cache is False
    assert second.response_from_cache is True
    assert first.raw_response_path is not None
    assert first.raw_response_path.exists()
    assert second.raw_response_path is not None
    assert second.raw_response_path.exists()


@pytest.mark.external_news
def test_real_webpage_requests_cache_smoke(tmp_path: Path) -> None:
    if os.getenv("AIOS_RUN_EXTERNAL_NEWS_TESTS") != "1":
        pytest.skip("set AIOS_RUN_EXTERNAL_NEWS_TESTS=1 to run external news smoke")

    from aios.integrations.http_client import HTTPClientConfig
    from aios.integrations.webpage.adapter import (
        TrafilaturaWebpageAdapter,
        UrllibWebpageHTTPClient,
    )

    client = UrllibWebpageHTTPClient(
        http_config=HTTPClientConfig(
            cache_enabled=True,
            cache_name=tmp_path / "webpage-http-cache",
            expire_after_seconds=300,
        )
    )
    adapter = TrafilaturaWebpageAdapter(http_client=client)

    first = adapter.fetch(
        page_url="https://www.bbc.co.uk/news/articles/ckg4xj8j5vjo",
        source_id="bbc-business",
        persist_dir=Path("results/brain001/cache/webpage"),
    )
    second = adapter.fetch(
        page_url="https://www.bbc.co.uk/news/articles/ckg4xj8j5vjo",
        source_id="bbc-business",
        persist_dir=Path("results/brain001/cache/webpage"),
    )

    assert first.response_from_cache is False
    assert second.response_from_cache is True
    assert first.raw_response_path is not None
    assert first.raw_response_path.exists()
    assert second.raw_response_path is not None
    assert second.raw_response_path.exists()
