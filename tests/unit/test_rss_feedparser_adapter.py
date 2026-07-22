from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent.parent / "fixtures" / "rss" / "bbc_business.xml"


def test_feedparser_rss_adapter_maps_real_feed_fixture(tmp_path: Path) -> None:
    from aios.integrations.rss.adapter import FeedparserRSSAdapter

    raw_xml = FIXTURE.read_bytes()
    fetched_at = datetime(2026, 7, 22, 9, 0, tzinfo=UTC)

    result = FeedparserRSSAdapter().parse_bytes(
        raw_xml,
        feed_url="https://feeds.bbci.co.uk/news/business/rss.xml",
        source_id="bbc-business",
        fetched_at=fetched_at,
        persist_dir=tmp_path,
    )

    assert result.provider_name == "feedparser"
    assert result.source_id == "bbc-business"
    assert result.feed_url == "https://feeds.bbci.co.uk/news/business/rss.xml"
    assert result.fetched_at == fetched_at
    assert result.raw_response_path is not None
    assert result.raw_response_path.read_bytes() == raw_xml
    assert result.pre_normalized_path is not None
    assert result.pre_normalized_path.exists()
    assert result.feed_title
    assert result.items

    item = result.items[0]
    assert item.source_id == "bbc-business"
    assert item.provider_name == "feedparser"
    assert item.feed_url == result.feed_url
    assert item.title
    assert item.url.startswith("https://")
    assert item.collected_at == fetched_at
    assert item.raw_content
    assert len(item.fingerprint) == 64
    assert item.raw_entry
    assert item.source_trace["provider_name"] == "feedparser"
    assert item.source_trace["feed_url"] == result.feed_url


def test_feedparser_rss_adapter_rejects_empty_feed_fixture() -> None:
    from aios.integrations.rss.adapter import FeedparserRSSAdapter, RSSFeedParseError

    with pytest.raises(RSSFeedParseError, match="no entries"):
        FeedparserRSSAdapter().parse_bytes(
            b"<rss><channel><title>Empty</title></channel></rss>",
            feed_url="https://example.test/rss.xml",
            source_id="empty",
            fetched_at=datetime(2026, 7, 22, 9, 0, tzinfo=UTC),
        )


def test_feedparser_rss_adapter_fetch_many_keeps_provider_failures_local() -> None:
    from aios.integrations.rss.adapter import FeedparserRSSAdapter

    class Client:
        def __init__(self) -> None:
            self.calls = 0

        def fetch(self, url: str) -> bytes:
            self.calls += 1
            if "bad" in url:
                raise OSError("connection refused")
            return FIXTURE.read_bytes()

    client = Client()
    batch = FeedparserRSSAdapter(http_client=client).fetch_many(
        [
            ("bbc-business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
            ("bad-source", "https://bad.example.test/rss.xml"),
        ],
        fetched_at=datetime(2026, 7, 22, 9, 0, tzinfo=UTC),
    )

    assert client.calls == 2
    assert len(batch.results) == 1
    assert batch.results[0].source_id == "bbc-business"
    assert len(batch.errors) == 1
    assert batch.errors[0].source_id == "bad-source"
    assert "connection refused" in batch.errors[0].message
