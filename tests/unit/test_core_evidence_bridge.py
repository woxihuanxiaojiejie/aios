from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from aios.integrations.evidence import Evidence as BrainEvidence
from aios.integrations.provider_records import RSSIntakeRecord
from aios.kernel.evidence import Evidence
from aios.storage.memory import InMemoryStorage

COLLECTED_AT = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)


def legacy_brain_evidence(*, fingerprint: str = "a" * 64) -> BrainEvidence:
    return BrainEvidence.from_provider_record(
        RSSIntakeRecord(
            source="source-a",
            source_type="rss",
            source_url="https://example.test/feed.xml",
            source_identifier=f"article-{uuid4()}",
            published_at=COLLECTED_AT,
            collected_at=COLLECTED_AT,
            raw_artifact_path=Path("results/raw.xml"),
            title="Policy title",
            summary="Policy summary",
            content="Original policy content",
            fingerprint=fingerprint,
        ),
        metadata={
            "symbols": ["600519"],
            "markets": ["CN"],
            "sectors": ["liquor"],
            "freshness": "fresh",
        },
    )


def test_core_evidence_accepts_legacy_fields_without_breaking_old_creation() -> None:
    old_style = Evidence(
        evidence_type="news",
        source="legacy",
        symbols=("600519",),
        published_at=COLLECTED_AT,
        available_at=COLLECTED_AT,
        summary="old style still works",
        reliability=0.8,
        content_hash="old-hash",
    )
    rich = Evidence(
        evidence_type="policy",
        source="source-a",
        symbols=("600519",),
        published_at=COLLECTED_AT,
        available_at=COLLECTED_AT,
        summary="Policy summary",
        reliability=0.9,
        content_hash="rich-hash",
        title="Policy title",
        raw_content="Original policy content",
        raw_response={"payload": {"title": "Policy title"}},
        source_type="rss",
        source_identifier="article-1",
        source_url="https://example.test/article/1",
        collected_at=COLLECTED_AT,
        entities={"symbols": ["600519"], "markets": ["CN"]},
        fingerprint="f" * 64,
        credibility=0.91,
        freshness="fresh",
        processing_status="parsed",
        parse_error=None,
        legacy_brain_evidence_id=str(uuid4()),
    )

    assert old_style.title is None
    assert old_style.processing_status == "parsed"
    assert rich.title == "Policy title"
    assert rich.raw_content == "Original policy content"
    assert rich.legacy_brain_evidence_id is not None


def test_legacy_bridge_creates_and_reuses_core_evidence() -> None:
    from aios.application.evidence_bridge import CoreEvidenceBridge

    storage = InMemoryStorage()
    bridge = CoreEvidenceBridge(storage)
    legacy = legacy_brain_evidence()

    created = bridge.ensure_core_evidence(legacy, default_symbol="600519")
    replay = bridge.ensure_core_evidence(legacy, default_symbol="600519")

    assert created.evidence_id == replay.evidence_id
    assert len(storage.list(Evidence)) == 1
    assert created.legacy_brain_evidence_id == str(legacy.evidence_id)
    assert created.title == legacy.title
    assert created.raw_content == legacy.content
    assert created.source_type == legacy.source_type
    assert created.fingerprint == legacy.fingerprint


def test_legacy_bridge_recovers_from_unique_conflict() -> None:
    from aios.application.evidence_bridge import CoreEvidenceBridge

    class RacingStorage(InMemoryStorage):
        def __init__(self, existing: Evidence) -> None:
            super().__init__()
            self._existing = existing
            self._raised = False

        def save(self, entity):
            if (
                isinstance(entity, Evidence)
                and entity.legacy_brain_evidence_id
                == self._existing.legacy_brain_evidence_id
                and not self._raised
            ):
                self._raised = True
                super().save(self._existing)
                raise IntegrityError("insert", {}, Exception("unique conflict"))
            return super().save(entity)

    legacy = legacy_brain_evidence()
    existing = CoreEvidenceBridge(InMemoryStorage()).build_core_evidence(
        legacy,
        default_symbol="600519",
    )
    storage = RacingStorage(existing)

    recovered = CoreEvidenceBridge(storage).ensure_core_evidence(
        legacy,
        default_symbol="600519",
    )

    assert recovered.evidence_id == existing.evidence_id
    assert len(storage.list(Evidence)) == 1
