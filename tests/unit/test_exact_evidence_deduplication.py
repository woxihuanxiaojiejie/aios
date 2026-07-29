from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from aios.integrations.evidence import Evidence
from aios.integrations.provider_records import (
    AnnouncementIntakeRecord,
    RSSIntakeRecord,
    WebpageIntakeRecord,
)

COLLECTED_AT = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)


def _rss(source: str, identifier: str, fingerprint: str) -> Evidence:
    return Evidence.from_provider_record(
        RSSIntakeRecord(
            source=source,
            source_type="rss",
            source_url="https://example.test/feed.xml",
            source_identifier=identifier,
            collected_at=COLLECTED_AT,
            raw_artifact_path=Path("results/rss.xml"),
            title="RSS title",
            content="RSS content",
            fingerprint=fingerprint,
        )
    )


def _webpage(source: str, url: str, fingerprint: str) -> Evidence:
    return Evidence.from_provider_record(
        WebpageIntakeRecord(
            source=source,
            source_type="webpage",
            source_url=url,
            collected_at=COLLECTED_AT,
            raw_artifact_path=Path("results/page.html"),
            title="Web title",
            content="Web content",
            fingerprint=fingerprint,
        )
    )


def _announcement(source: str, identifier: str, fingerprint: str) -> Evidence:
    return Evidence.from_provider_record(
        AnnouncementIntakeRecord(
            source=source,
            source_type="announcement",
            source_url="https://example.test/announcement",
            source_identifier=identifier,
            published_at=COLLECTED_AT,
            collected_at=COLLECTED_AT,
            raw_artifact_path=Path("results/announcement.json"),
            title="Announcement title",
            content="Announcement content",
            fingerprint=fingerprint,
        )
    )


def test_same_source_identifier_is_reported_without_discarding_candidate() -> None:
    from aios.integrations.evidence_deduplication import check_exact_duplicate

    existing = _rss("source-a", "article-1", "a" * 64)
    candidate = _rss("source-a", "article-1", "a" * 64)

    result = check_exact_duplicate(candidate, [existing])

    assert result.duplicate_type == "same_source_identifier"
    assert result.matched_evidence_id == existing.evidence_id
    assert result.matched_fingerprint == existing.fingerprint
    assert result.rule_name == "same_source_same_identifier"
    assert result.is_duplicate_candidate is True
    assert result.preserve_candidate is True


def test_same_fingerprint_across_sources_is_an_exact_duplicate_candidate() -> None:
    from aios.integrations.evidence_deduplication import check_exact_duplicate

    existing = _webpage("source-a", "https://a.test/article", "b" * 64)
    candidate = _webpage("source-b", "https://b.test/article", "b" * 64)

    result = check_exact_duplicate(candidate, [existing])

    assert result.duplicate_type == "exact_duplicate_candidate"
    assert result.rule_name == "different_source_same_fingerprint"
    assert result.matched_evidence_id == existing.evidence_id


def test_same_source_different_identifier_is_not_silently_deleted() -> None:
    from aios.integrations.evidence_deduplication import check_exact_duplicate

    existing = _announcement("akshare", "announcement-1", "c" * 64)
    candidate = _announcement("akshare", "announcement-2", "c" * 64)

    result = check_exact_duplicate(candidate, [existing])

    assert result.duplicate_type == "exact_duplicate_candidate"
    assert result.rule_name == "same_source_different_identifier_same_fingerprint"
    assert result.matched_fingerprint == "c" * 64
    assert result.preserve_candidate is True


def test_changed_content_with_same_source_identifier_is_a_new_version() -> None:
    from aios.integrations.evidence_deduplication import check_exact_duplicate

    existing = _rss("source-a", "article-1", "d" * 64)
    candidate = _rss("source-a", "article-1", "e" * 64)

    result = check_exact_duplicate(candidate, [existing])

    assert result.duplicate_type == "source_identifier_revision"
    assert result.rule_name == "same_source_same_identifier_changed_fingerprint"
    assert result.is_duplicate_candidate is False
    assert result.preserve_candidate is True


def test_no_matching_rule_returns_an_explainable_empty_result() -> None:
    from aios.integrations.evidence_deduplication import check_exact_duplicate

    result = check_exact_duplicate(
        _rss("source-a", "article-1", "f" * 64),
        [_rss("source-b", "article-2", "e" * 64)],
    )

    assert result.duplicate_type is None
    assert result.matched_evidence_id is None
    assert result.matched_fingerprint is None
    assert result.rule_name is None
    assert result.is_duplicate_candidate is False
    assert result.preserve_candidate is True
