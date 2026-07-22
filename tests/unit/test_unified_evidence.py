from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

COLLECTED_AT = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)


def test_rss_intake_converts_to_traceable_evidence() -> None:
    from aios.integrations.evidence import evidence_from_rss
    from aios.integrations.provider_records import RSSIntakeRecord

    record = RSSIntakeRecord(
        source="bbc-business",
        source_type="rss",
        source_url="https://example.test/feed.xml",
        source_identifier="https://example.test/article/1",
        published_at=datetime(2026, 7, 22, 9, 0, tzinfo=UTC),
        collected_at=COLLECTED_AT,
        raw_artifact_path=Path("results/raw.xml"),
        title="A market update",
        summary="A short summary",
        content="The original content.",
        fingerprint="a" * 64,
    )

    evidence = evidence_from_rss(record)

    assert isinstance(evidence.evidence_id, UUID)
    assert evidence.source == record.source
    assert evidence.source_type == "rss"
    assert evidence.source_identifier == record.source_identifier
    assert evidence.provider_record == record
    assert evidence.raw_artifact_path == record.raw_artifact_path
    assert evidence.available_at == COLLECTED_AT


def test_webpage_and_announcement_converters_preserve_provider_specific_fields() -> (
    None
):
    from aios.integrations.evidence import (
        evidence_from_announcement,
        evidence_from_webpage,
    )
    from aios.integrations.provider_records import (
        AnnouncementIntakeRecord,
        WebpageIntakeRecord,
    )

    webpage = WebpageIntakeRecord(
        source="news-site",
        source_type="webpage",
        source_url="https://example.test/article",
        collected_at=COLLECTED_AT,
        raw_artifact_path=Path("results/raw.html"),
        title="Web article",
        content="Web content",
        fingerprint="b" * 64,
    )
    announcement = AnnouncementIntakeRecord(
        source="akshare",
        source_type="announcement",
        source_identifier="000001",
        source_url="https://example.test/announcement",
        published_at=datetime(2026, 7, 21, tzinfo=UTC),
        collected_at=COLLECTED_AT,
        raw_artifact_path=Path("results/raw.json"),
        title="Company announcement",
        content="Announcement content",
        fingerprint="c" * 64,
    )

    webpage_evidence = evidence_from_webpage(webpage)
    announcement_evidence = evidence_from_announcement(announcement)

    assert webpage_evidence.source_type == "webpage"
    assert webpage_evidence.source_identifier == webpage.source_url
    assert webpage_evidence.published_at is None
    assert announcement_evidence.source_identifier == announcement.source_identifier
    assert announcement_evidence.source_url == announcement.source_url
    assert announcement_evidence.content == announcement.content


def test_evidence_rejects_naive_and_future_available_times() -> None:
    from aios.integrations.evidence import Evidence
    from aios.integrations.provider_records import RSSIntakeRecord

    record = RSSIntakeRecord(
        source="source",
        source_type="rss",
        source_url="https://example.test/feed.xml",
        collected_at=COLLECTED_AT,
        raw_artifact_path=Path("results/raw.xml"),
        title="Title",
        content="Content",
        fingerprint="d" * 64,
    )

    with pytest.raises(ValueError, match="available_at must not be earlier"):
        Evidence.from_provider_record(
            record,
            available_at=datetime(2026, 7, 22, 9, 59, tzinfo=UTC),
        )

    with pytest.raises(ValidationError, match="timezone-aware"):
        Evidence(
            source="source",
            source_type="rss",
            source_identifier="id",
            source_url="https://example.test/feed.xml",
            title="Title",
            content="Content",
            collected_at=datetime(2026, 7, 22, 10, 0),
            available_at=COLLECTED_AT,
            raw_artifact_path=Path("results/raw.xml"),
            fingerprint="d" * 64,
            provider_record=record,
        )


def test_evidence_ids_are_unique_even_when_fingerprints_match() -> None:
    from aios.integrations.evidence import evidence_from_rss
    from aios.integrations.provider_records import RSSIntakeRecord

    def make_record(source: str) -> RSSIntakeRecord:
        return RSSIntakeRecord(
            source=source,
            source_type="rss",
            source_url="https://example.test/feed.xml",
            source_identifier="article",
            collected_at=COLLECTED_AT,
            raw_artifact_path=Path("results/raw.xml"),
            title="Title",
            content="Same content",
            fingerprint="e" * 64,
        )

    first = evidence_from_rss(make_record("source-a"))
    second = evidence_from_rss(make_record("source-b"))

    assert first.fingerprint == second.fingerprint
    assert first.evidence_id != second.evidence_id


def test_evidence_metadata_cannot_duplicate_core_fields() -> None:
    from aios.integrations.evidence import evidence_from_rss
    from aios.integrations.provider_records import RSSIntakeRecord

    record = RSSIntakeRecord(
        source="source",
        source_type="rss",
        source_url="https://example.test/feed.xml",
        collected_at=COLLECTED_AT,
        raw_artifact_path=Path("results/raw.xml"),
        title="Title",
        content="Content",
        fingerprint="f" * 64,
    )

    with pytest.raises(ValueError, match="metadata may only contain"):
        evidence_from_rss(record, metadata={"content": "duplicated"})
