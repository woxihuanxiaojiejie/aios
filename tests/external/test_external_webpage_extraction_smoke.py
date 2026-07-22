from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.mark.external_news
def test_real_bbc_business_trafilatura_webpage_smoke() -> None:
    if os.getenv("AIOS_RUN_EXTERNAL_NEWS_TESTS") != "1":
        pytest.skip("set AIOS_RUN_EXTERNAL_NEWS_TESTS=1 to run external news smoke")

    from aios.integrations.webpage.adapter import TrafilaturaWebpageAdapter

    result = TrafilaturaWebpageAdapter().fetch(
        page_url="https://www.bbc.co.uk/news/articles/ckg4xj8j5vjo",
        source_id="bbc-business",
        persist_dir=Path("results/brain001/webpage"),
    )

    assert result.provider_name == "trafilatura"
    assert result.raw_response_path is not None
    assert result.raw_response_path.exists()
    assert result.pre_normalized_path is not None
    assert result.pre_normalized_path.exists()
    assert result.title
    assert result.extracted_text
    assert result.source_trace["provider_name"] == "trafilatura"
