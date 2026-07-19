from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from aios.application.decision_generation import LLMGenerationRecord
from aios.kernel.base import ensure_utc
from aios.kernel.errors import DuplicateEntityError, StorageOperationError
from aios.storage.postgres.database import make_engine, make_session_factory
from aios.storage.postgres.models import LLMGenerationRecordModel


class LLMGenerationRecordStore:
    def __init__(self, database_url: str | None = None) -> None:
        self._engine = make_engine(database_url)
        self._session_factory = make_session_factory(self._engine)

    def save_generation_record(self, record: LLMGenerationRecord) -> None:
        session = self._session_factory()
        try:
            if session.get(LLMGenerationRecordModel, record.decision_id) is not None:
                msg = f"LLM generation record for {record.decision_id} already exists"
                raise DuplicateEntityError(msg)
            session.add(_to_model(record))
            session.commit()
        except DuplicateEntityError:
            session.rollback()
            raise
        except (IntegrityError, SQLAlchemyError) as exc:
            session.rollback()
            msg = f"failed to save LLM generation record for {record.decision_id}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def get_by_decision_id(self, decision_id: str) -> LLMGenerationRecord | None:
        session = self._session_factory()
        try:
            model = session.get(LLMGenerationRecordModel, decision_id)
            return _to_record(model) if model is not None else None
        finally:
            session.close()

    def list_for_experiment(self, experiment_id: str) -> list[LLMGenerationRecord]:
        session = self._session_factory()
        try:
            statement = (
                select(LLMGenerationRecordModel)
                .where(LLMGenerationRecordModel.experiment_id == experiment_id)
                .order_by(
                    LLMGenerationRecordModel.created_at,
                    LLMGenerationRecordModel.decision_id,
                )
            )
            return [_to_record(model) for model in session.scalars(statement).all()]
        finally:
            session.close()

    def dispose(self) -> None:
        self._engine.dispose()


def _to_model(record: LLMGenerationRecord) -> LLMGenerationRecordModel:
    return LLMGenerationRecordModel(
        decision_id=record.decision_id,
        experiment_id=record.experiment_id,
        provider=record.provider,
        model=record.model,
        prompt_version=record.prompt_version,
        prompt_hash=record.prompt_hash,
        evidence_snapshot_hash=record.evidence_snapshot_hash,
        temperature=record.temperature,
        prompt_tokens=record.prompt_tokens,
        completion_tokens=record.completion_tokens,
        total_tokens=record.total_tokens,
        latency_ms=record.latency_ms,
        created_at=record.created_at,
    )


def _to_record(model: LLMGenerationRecordModel) -> LLMGenerationRecord:
    return LLMGenerationRecord(
        decision_id=model.decision_id,
        experiment_id=model.experiment_id,
        provider=model.provider,
        model=model.model,
        prompt_version=model.prompt_version,
        prompt_hash=model.prompt_hash,
        evidence_snapshot_hash=model.evidence_snapshot_hash,
        temperature=model.temperature,
        prompt_tokens=model.prompt_tokens,
        completion_tokens=model.completion_tokens,
        total_tokens=model.total_tokens,
        latency_ms=model.latency_ms,
        created_at=ensure_utc(model.created_at),
    )
