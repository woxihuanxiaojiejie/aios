from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest


def _evidence(
    *,
    source: str,
    collected_at: datetime,
    published_at: datetime | None = None,
    fingerprint: str | None = None,
):
    from aios.integrations.evidence import Evidence
    from aios.integrations.provider_records import RSSIntakeRecord

    record = RSSIntakeRecord(
        source=source,
        source_type="rss",
        source_url=f"https://{source}.test/feed.xml",
        source_identifier=f"article-{uuid4()}",
        published_at=published_at,
        collected_at=collected_at,
        raw_artifact_path=Path("results/raw.xml"),
        title=f"Title from {source}",
        content=f"Content from {source}",
        fingerprint=fingerprint or uuid4().hex + uuid4().hex,
    )
    return Evidence.from_provider_record(record)


def test_evidence_repository_persists_and_queries_without_external_calls(
    migrated_postgres_url: str,
) -> None:
    from aios.storage.postgres.evidence_repository import EvidenceRepository

    repository = EvidenceRepository(migrated_postgres_url)
    first_collected = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)
    second_collected = first_collected + timedelta(hours=1)
    first = _evidence(
        source="source-a",
        collected_at=first_collected,
        published_at=first_collected - timedelta(minutes=30),
        fingerprint="a" * 64,
    )
    second = _evidence(
        source="source-b",
        collected_at=second_collected,
        published_at=second_collected - timedelta(minutes=30),
        fingerprint="b" * 64,
    )

    assert repository.create(first) == first
    repository.create(second)

    assert repository.get_by_id(first.evidence_id) == first
    assert repository.exists_by_fingerprint("a" * 64)
    assert not repository.exists_by_fingerprint("c" * 64)
    assert repository.list_by_source("source-a") == [first]
    assert repository.list_available_before(second_collected) == [first, second]
    assert repository.list_by_time_range(
        first_collected, second_collected, timestamp_field="collected_at"
    ) == [first, second]
    assert repository.list_by_time_range(
        first_collected - timedelta(hours=1),
        first_collected,
        timestamp_field="published_at",
    ) == [first]


def test_evidence_repository_rolls_back_failed_create(
    migrated_postgres_url: str,
) -> None:
    from aios.storage.postgres.evidence_repository import (
        EvidenceRepository,
        EvidenceRepositoryError,
    )

    repository = EvidenceRepository(migrated_postgres_url)
    evidence = _evidence(
        source="source-a",
        collected_at=datetime(2026, 7, 22, 10, 0, tzinfo=UTC),
    )
    repository.create(evidence)

    with pytest.raises(EvidenceRepositoryError):
        repository.create(evidence)

    assert repository.get_by_id(evidence.evidence_id) == evidence
    assert repository.list_by_source("source-a") == [evidence]
