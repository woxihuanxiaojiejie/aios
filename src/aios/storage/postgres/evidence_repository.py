from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from aios.integrations.evidence import Evidence, ProviderRecord
from aios.storage.postgres.database import make_engine, make_session_factory
from aios.storage.postgres.models import BrainEvidenceRecord

TimestampField = Literal["published_at", "collected_at", "available_at"]


class EvidenceRepositoryError(RuntimeError):
    """Raised when BRAIN-001 evidence persistence fails."""


class EvidenceRepository:
    def __init__(
        self,
        database_url: str | None = None,
        *,
        engine: Engine | None = None,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        if session_factory is not None:
            self._session_factory = session_factory
            return
        self._session_factory = make_session_factory(
            engine or make_engine(database_url)
        )

    def create(self, evidence: Evidence) -> Evidence:
        model = BrainEvidenceRecord(
            evidence_id=str(evidence.evidence_id),
            source=evidence.source,
            source_type=evidence.source_type,
            source_identifier=evidence.source_identifier,
            source_url=evidence.source_url,
            title=evidence.title,
            summary=evidence.summary,
            content=evidence.content,
            published_at=evidence.published_at,
            collected_at=evidence.collected_at,
            available_at=evidence.available_at,
            fingerprint=evidence.fingerprint,
            raw_artifact_path=str(evidence.raw_artifact_path),
            provider_record_json=evidence.provider_record.model_dump(mode="json"),
            metadata_json=evidence.metadata,
        )
        session = self._session_factory()
        try:
            session.add(model)
            session.commit()
            return evidence
        except (IntegrityError, SQLAlchemyError) as exc:
            session.rollback()
            msg = f"failed to create Evidence {evidence.evidence_id}"
            raise EvidenceRepositoryError(msg) from exc
        finally:
            session.close()

    def get_by_id(self, evidence_id: UUID) -> Evidence | None:
        session = self._session_factory()
        try:
            model = session.get(BrainEvidenceRecord, str(evidence_id))
            return _to_evidence(model) if model is not None else None
        except SQLAlchemyError as exc:
            msg = f"failed to get Evidence {evidence_id}"
            raise EvidenceRepositoryError(msg) from exc
        finally:
            session.close()

    def exists_by_fingerprint(self, fingerprint: str) -> bool:
        session = self._session_factory()
        try:
            statement = select(BrainEvidenceRecord.evidence_id).where(
                BrainEvidenceRecord.fingerprint == fingerprint
            )
            return session.scalar(statement) is not None
        except SQLAlchemyError as exc:
            msg = "failed to check Evidence fingerprint"
            raise EvidenceRepositoryError(msg) from exc
        finally:
            session.close()

    def list_by_source(self, source: str) -> list[Evidence]:
        return self._list(BrainEvidenceRecord.source == source)

    def list_available_before(self, as_of: datetime) -> list[Evidence]:
        return self._list(BrainEvidenceRecord.available_at <= as_of)

    def list_by_time_range(
        self,
        start: datetime,
        end: datetime,
        *,
        timestamp_field: TimestampField = "collected_at",
    ) -> list[Evidence]:
        column = getattr(BrainEvidenceRecord, timestamp_field)
        return self._list(column >= start, column <= end)

    def _list(self, *conditions: ColumnElement[bool]) -> list[Evidence]:
        session = self._session_factory()
        try:
            statement = (
                select(BrainEvidenceRecord)
                .where(*conditions)
                .order_by(
                    BrainEvidenceRecord.collected_at,
                    BrainEvidenceRecord.evidence_id,
                )
            )
            return [_to_evidence(model) for model in session.scalars(statement).all()]
        except SQLAlchemyError as exc:
            msg = "failed to query Brain Evidence"
            raise EvidenceRepositoryError(msg) from exc
        finally:
            session.close()


def _to_evidence(model: BrainEvidenceRecord) -> Evidence:
    return Evidence(
        evidence_id=UUID(model.evidence_id),
        source=model.source,
        source_type=model.source_type,
        source_identifier=model.source_identifier,
        source_url=model.source_url,
        title=model.title,
        summary=model.summary,
        content=model.content,
        published_at=model.published_at,
        collected_at=model.collected_at,
        available_at=model.available_at,
        fingerprint=model.fingerprint,
        raw_artifact_path=Path(model.raw_artifact_path),
        provider_record=TypeAdapter(ProviderRecord).validate_python(
            model.provider_record_json
        ),
        metadata=model.metadata_json,
    )
