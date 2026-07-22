from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.mark.external_news
def test_real_rss_provider_rate_limit_smoke(tmp_path: Path) -> None:
    if os.getenv("AIOS_RUN_EXTERNAL_NEWS_TESTS") != "1":
        pytest.skip("set AIOS_RUN_EXTERNAL_NEWS_TESTS=1 to run external news smoke")

    from aios.integrations.http_client import HTTPClientConfig
    from aios.integrations.http_rate_limit import (
        ProviderRateLimitConfig,
        ProviderRateLimiter,
    )
    from aios.integrations.rss.adapter import FeedparserRSSAdapter, UrllibRSSHTTPClient

    limiter = ProviderRateLimiter(
        {
            "rss": ProviderRateLimitConfig(
                max_requests=10,
                window_seconds=1,
                wait_strategy="wait",
                timeout_seconds=1,
            )
        }
    )
    client = UrllibRSSHTTPClient(
        http_config=HTTPClientConfig(
            provider_name="rss",
            cache_enabled=True,
            cache_name=tmp_path / "rate-limit-cache",
            expire_after_seconds=300,
        ),
        rate_limiter=limiter,
    )
    result = FeedparserRSSAdapter(http_client=client).fetch(
        feed_url="https://feeds.bbci.co.uk/news/business/rss.xml",
        source_id="bbc-business",
        persist_dir=Path("results/brain001/rate_limit/rss"),
    )

    assert result.items
    assert result.raw_response_path is not None
    assert result.raw_response_path.exists()
