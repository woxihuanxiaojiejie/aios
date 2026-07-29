from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError


def test_rss_pre_normalized_record_requires_intake_fields() -> None:
    from aios.integrations.provider_records import RSSIntakeRecord

    record = RSSIntakeRecord(
        source="bbc-business",
        source_type="rss",
        source_url="https://feeds.bbci.co.uk/news/business/rss.xml",
        published_at=datetime(2026, 7, 22, tzinfo=UTC),
        collected_at=datetime(2026, 7, 22, 10, 0, tzinfo=UTC),
        raw_artifact_path=Path("results/raw.xml"),
        title="Food prices have fallen",
        summary="Inflation summary",
        content="Inflation summary",
        fingerprint="a" * 64,
    )

    assert record.source_type == "rss"
    assert record.fingerprint == "a" * 64


def test_webpage_pre_normalized_record_rejects_missing_content() -> None:
    from aios.integrations.provider_records import WebpageIntakeRecord

    with pytest.raises(ValidationError):
        WebpageIntakeRecord(
            source="bbc-business",
            source_type="webpage",
            source_url="https://www.bbc.co.uk/news/articles/ckg4xj8j5vjo",
            published_at=None,
            collected_at=datetime(2026, 7, 22, 10, 0, tzinfo=UTC),
            raw_artifact_path=Path("results/raw.html"),
            title="Article",
            content="",
            fingerprint="b" * 64,
        )


def test_announcement_pre_normalized_record_allows_missing_summary() -> None:
    from aios.integrations.provider_records import AnnouncementIntakeRecord

    record = AnnouncementIntakeRecord(
        source="akshare",
        source_type="announcement",
        source_url="http://www.cninfo.com.cn/new/disclosure/detail",
        published_at=datetime(2023, 12, 9, tzinfo=UTC),
        collected_at=datetime(2026, 7, 22, 10, 30, tzinfo=UTC),
        raw_artifact_path=Path("results/raw.json"),
        title="独立董事审核意见",
        summary=None,
        content="独立董事审核意见",
        fingerprint="c" * 64,
        source_identifier="000001",
    )

    assert record.summary is None
    assert record.source_identifier == "000001"


def test_rss_adapter_does_not_emit_record_when_validation_fails(
    tmp_path: Path,
) -> None:
    from aios.integrations.rss.adapter import FeedparserRSSAdapter, RSSFeedParseError

    raw_xml = b"""
    <rss><channel><title>Broken</title>
    <item><title></title><description></description><link></link></item>
    </channel></rss>
    """

    with pytest.raises(RSSFeedParseError, match="invalid RSS intake record"):
        FeedparserRSSAdapter().parse_bytes(
            raw_xml,
            feed_url="https://example.test/rss.xml",
            source_id="broken",
            fetched_at=datetime(2026, 7, 22, 10, 0, tzinfo=UTC),
            persist_dir=tmp_path,
        )

    assert list(tmp_path.glob("*.xml"))
    assert not list(tmp_path.glob("*.intake.json"))
