from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

FIXTURE = (
    Path(__file__).parent.parent / "fixtures" / "html" / "bbc_business_food_prices.html"
)
ARTICLE_URL = "https://www.bbc.co.uk/news/articles/ckg4xj8j5vjo"


def test_trafilatura_webpage_adapter_extracts_real_html_fixture(
    tmp_path: Path,
) -> None:
    from aios.integrations.webpage.adapter import TrafilaturaWebpageAdapter

    raw_html = FIXTURE.read_bytes()
    fetched_at = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)

    result = TrafilaturaWebpageAdapter().extract_bytes(
        raw_html,
        page_url=ARTICLE_URL,
        source_id="bbc-business",
        fetched_at=fetched_at,
        persist_dir=tmp_path,
    )

    assert result.provider_name == "trafilatura"
    assert result.source_id == "bbc-business"
    assert result.page_url == ARTICLE_URL
    assert result.fetched_at == fetched_at
    assert result.raw_response_path is not None
    assert result.raw_response_path.read_bytes() == raw_html
    assert result.pre_normalized_path is not None
    assert result.pre_normalized_path.exists()
    assert result.intake_record is not None
    assert result.title
    assert result.extracted_text
    assert len(result.fingerprint) == 64
    assert "inflation" in result.extracted_text.lower()
    assert result.source_trace["provider_name"] == "trafilatura"
    assert result.source_trace["page_url"] == ARTICLE_URL
    assert result.intake_record.source == "bbc-business"
    assert result.intake_record.source_type == "webpage"
    assert result.intake_record.source_url == ARTICLE_URL
    assert result.intake_record.raw_artifact_path == result.raw_response_path
    assert result.intake_record.fingerprint == result.fingerprint


def test_trafilatura_webpage_adapter_rejects_unextractable_html() -> None:
    from aios.integrations.webpage.adapter import (
        TrafilaturaExtractionError,
        TrafilaturaWebpageAdapter,
    )

    with pytest.raises(TrafilaturaExtractionError, match="could not extract"):
        TrafilaturaWebpageAdapter().extract_bytes(
            b"<html><head></head><body></body></html>",
            page_url="https://example.test/blank",
            source_id="blank",
            fetched_at=datetime(2026, 7, 22, 10, 0, tzinfo=UTC),
        )


def test_trafilatura_webpage_fetch_many_keeps_provider_failures_local() -> None:
    from aios.integrations.webpage.adapter import TrafilaturaWebpageAdapter

    class Client:
        def __init__(self) -> None:
            self.calls = 0

        def fetch(self, url: str) -> bytes:
            self.calls += 1
            if "bad" in url:
                raise OSError("connection refused")
            return FIXTURE.read_bytes()

    client = Client()
    batch = TrafilaturaWebpageAdapter(http_client=client).fetch_many(
        [
            ("bbc-business", ARTICLE_URL),
            ("bad-source", "https://bad.example.test/article"),
        ],
        fetched_at=datetime(2026, 7, 22, 10, 0, tzinfo=UTC),
    )

    assert client.calls == 2
    assert len(batch.results) == 1
    assert batch.results[0].source_id == "bbc-business"
    assert len(batch.errors) == 1
    assert batch.errors[0].source_id == "bad-source"
    assert "connection refused" in batch.errors[0].message
