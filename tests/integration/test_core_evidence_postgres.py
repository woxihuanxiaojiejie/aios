from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from aios.kernel.errors import StorageOperationError
from aios.kernel.evidence import Evidence
from aios.storage.postgres.storage import PostgresStorage

NOW = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)


def rich_evidence(**overrides: object) -> Evidence:
    payload = {
        "evidence_type": "policy",
        "source": "source-a",
        "symbols": ("600519",),
        "published_at": NOW,
        "available_at": NOW,
        "summary": "Policy summary",
        "reliability": 0.9,
        "content_hash": f"hash-{uuid4()}",
        "title": "Policy title",
        "raw_content": "Original policy content",
        "raw_response": {"payload": {"title": "Policy title"}},
        "source_type": "rss",
        "source_identifier": "article-1",
        "source_url": "https://example.test/article/1",
        "collected_at": NOW,
        "entities": {"symbols": ["600519"], "markets": ["CN"]},
        "fingerprint": "f" * 64,
        "credibility": 0.91,
        "freshness": "fresh",
        "processing_status": "parsed",
        "parse_error": None,
        "legacy_brain_evidence_id": str(uuid4()),
    }
    payload.update(overrides)
    return Evidence(**payload)


def test_postgres_round_trips_core_evidence_new_fields(
    migrated_postgres_url: str,
) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    evidence = rich_evidence()

    storage.save(evidence)

    assert storage.get(Evidence, evidence.evidence_id) == evidence


def test_postgres_allows_multiple_null_legacy_brain_ids(
    migrated_postgres_url: str,
) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    first = rich_evidence(legacy_brain_evidence_id=None)
    second = rich_evidence(legacy_brain_evidence_id=None)

    storage.save(first)
    storage.save(second)

    assert len(storage.list(Evidence)) == 2


def test_postgres_enforces_unique_non_null_legacy_brain_id(
    migrated_postgres_url: str,
) -> None:
    storage = PostgresStorage(migrated_postgres_url)
    legacy_id = str(uuid4())
    first = rich_evidence(legacy_brain_evidence_id=legacy_id)
    second = rich_evidence(legacy_brain_evidence_id=legacy_id)

    storage.save(first)
    with pytest.raises(StorageOperationError):
        storage.save(second)
