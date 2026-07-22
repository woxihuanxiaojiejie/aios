from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from aios.api.app import create_app
from aios.integrations.evidence import Evidence
from aios.integrations.provider_records import RSSIntakeRecord
from aios.storage.memory import InMemoryStorage


class FakeEvidenceRepository:
    def __init__(self, evidence: Evidence) -> None:
        self.evidence = evidence
        self.last_query: dict[str, Any] | None = None

    def get_by_id(self, evidence_id: object) -> Evidence | None:
        if evidence_id == self.evidence.evidence_id:
            return self.evidence
        return None

    def query(self, **kwargs: Any) -> tuple[list[Evidence], int]:
        self.last_query = kwargs
        return [self.evidence], 1


def _evidence() -> Evidence:
    collected_at = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)
    return Evidence.from_provider_record(
        RSSIntakeRecord(
            source="source-a",
            source_type="rss",
            source_url="https://example.test/feed.xml",
            source_identifier="article-1",
            published_at=collected_at,
            collected_at=collected_at,
            raw_artifact_path=Path("results/raw.xml"),
            title="Title",
            summary="Summary",
            content="Content",
            fingerprint="a" * 64,
        ),
        metadata={"feed_language": "en"},
    )


def test_brain_evidence_list_supports_filters_pagination_and_point_in_time() -> None:
    repository = FakeEvidenceRepository(_evidence())
    api = TestClient(
        create_app(storage=InMemoryStorage(), evidence_repository=repository)
    )

    response = api.get(
        "/api/v1/brain/evidence",
        params={
            "source": "source-a",
            "source_type": "rss",
            "published_from": "2026-07-01T00:00:00+00:00",
            "published_to": "2026-07-31T00:00:00+00:00",
            "collected_from": "2026-07-01T00:00:00+00:00",
            "collected_to": "2026-07-31T00:00:00+00:00",
            "as_of": "2026-07-23T00:00:00+00:00",
            "fingerprint": "a" * 64,
            "limit": 10,
            "offset": 2,
            "sort_by": "published_at",
            "sort_order": "desc",
        },
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["evidence_id"] == str(
        repository.evidence.evidence_id
    )
    assert response.json()["items"][0]["provider_record"] is None
    assert repository.last_query == {
        "source": "source-a",
        "source_type": "rss",
        "fingerprint": "a" * 64,
        "published_from": datetime(2026, 7, 1, tzinfo=UTC),
        "published_to": datetime(2026, 7, 31, tzinfo=UTC),
        "collected_from": datetime(2026, 7, 1, tzinfo=UTC),
        "collected_to": datetime(2026, 7, 31, tzinfo=UTC),
        "available_before": datetime(2026, 7, 23, tzinfo=UTC),
        "sort_by": "published_at",
        "sort_order": "desc",
        "limit": 10,
        "offset": 2,
    }


def test_brain_evidence_detail_can_include_trace_fields() -> None:
    repository = FakeEvidenceRepository(_evidence())
    api = TestClient(
        create_app(storage=InMemoryStorage(), evidence_repository=repository)
    )
    evidence_id = repository.evidence.evidence_id

    response = api.get(
        f"/api/v1/brain/evidence/{evidence_id}",
        params={
            "include_provider_record": "true",
            "include_metadata": "true",
            "include_raw_artifact_path": "true",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["provider_record"]["source_type"] == "rss"
    assert body["metadata"] == {"feed_language": "en"}
    assert body["raw_artifact_path"] == "results/raw.xml"


def test_brain_evidence_detail_returns_not_found_without_collecting() -> None:
    repository = FakeEvidenceRepository(_evidence())
    api = TestClient(
        create_app(storage=InMemoryStorage(), evidence_repository=repository)
    )

    response = api.get("/api/v1/brain/evidence/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
