from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import DeclarativeBase

from aios.kernel.base import KernelModel, ensure_utc
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    Action,
    ApprovalStatus,
    DecisionStatus,
    ExperimentStatus,
    LearningType,
    Outcome,
)
from aios.kernel.errors import UnsupportedEntityError
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.review import Review
from aios.storage.postgres.models import (
    DecisionRecord,
    EvidenceRecord,
    ExperimentRecord,
    LearningRecord,
    ReviewRecord,
)

type Record = (
    EvidenceRecord | ExperimentRecord | DecisionRecord | ReviewRecord | LearningRecord
)


def to_model(entity: KernelModel) -> Record:
    if isinstance(entity, Evidence):
        return EvidenceRecord(
            evidence_id=entity.evidence_id,
            evidence_type=entity.evidence_type,
            source=entity.source,
            symbols=list(entity.symbols),
            published_at=entity.published_at,
            available_at=entity.available_at,
            summary=entity.summary,
            reliability=entity.reliability,
            content_hash=entity.content_hash,
            metadata_json=entity.metadata,
            created_at=entity.created_at,
        )
    if isinstance(entity, Experiment):
        return ExperimentRecord(
            experiment_id=entity.experiment_id,
            name=entity.name,
            model=entity.model,
            prompt_version=entity.prompt_version,
            agent_config_version=entity.agent_config_version,
            dataset_snapshot=entity.dataset_snapshot,
            evidence_ids=list(entity.evidence_ids),
            parameters=entity.parameters,
            status=entity.status.value,
            started_at=entity.started_at,
            finished_at=entity.finished_at,
            created_at=entity.created_at,
        )
    if isinstance(entity, Decision):
        return DecisionRecord(
            decision_id=entity.decision_id,
            experiment_id=entity.experiment_id,
            symbol=entity.symbol,
            action=entity.action.value,
            horizon=entity.horizon,
            confidence=entity.confidence,
            expected_return=entity.expected_return,
            max_expected_loss=entity.max_expected_loss,
            evidence_ids=list(entity.evidence_ids),
            reasoning_summary=entity.reasoning_summary,
            status=entity.status.value,
            created_at=entity.created_at,
            valid_until=entity.valid_until,
        )
    if isinstance(entity, Review):
        return ReviewRecord(
            review_id=entity.review_id,
            decision_id=entity.decision_id,
            actual_return=entity.actual_return,
            direction_correct=entity.direction_correct,
            risk_limit_breached=entity.risk_limit_breached,
            outcome=entity.outcome.value,
            cause_tags=list(entity.cause_tags),
            review_summary=entity.review_summary,
            created_at=entity.created_at,
        )
    if isinstance(entity, Learning):
        return LearningRecord(
            learning_id=entity.learning_id,
            review_id=entity.review_id,
            learning_type=entity.learning_type.value,
            target=entity.target,
            before=entity.before,
            after=entity.after,
            reason=entity.reason,
            approval_status=entity.approval_status.value,
            created_at=entity.created_at,
        )
    msg = f"{type(entity).__name__} is not supported by PostgreSQL mapper"
    raise UnsupportedEntityError(msg)


def model_to_entity(model: DeclarativeBase) -> KernelModel:
    if isinstance(model, EvidenceRecord):
        return Evidence(
            evidence_id=model.evidence_id,
            evidence_type=model.evidence_type,
            source=model.source,
            symbols=tuple(model.symbols),
            published_at=_utc(model.published_at),
            available_at=_utc(model.available_at),
            summary=model.summary,
            reliability=model.reliability,
            content_hash=model.content_hash,
            metadata=model.metadata_json,
            created_at=_utc(model.created_at),
        )
    if isinstance(model, ExperimentRecord):
        return Experiment(
            experiment_id=model.experiment_id,
            name=model.name,
            model=model.model,
            prompt_version=model.prompt_version,
            agent_config_version=model.agent_config_version,
            dataset_snapshot=model.dataset_snapshot,
            evidence_ids=tuple(model.evidence_ids),
            parameters=model.parameters,
            status=ExperimentStatus(model.status),
            started_at=_utc(model.started_at),
            finished_at=_utc(model.finished_at) if model.finished_at else None,
            created_at=_utc(model.created_at),
        )
    if isinstance(model, DecisionRecord):
        return Decision(
            decision_id=model.decision_id,
            experiment_id=model.experiment_id,
            symbol=model.symbol,
            action=Action(model.action),
            horizon=model.horizon,
            confidence=model.confidence,
            expected_return=model.expected_return,
            max_expected_loss=model.max_expected_loss,
            evidence_ids=tuple(model.evidence_ids),
            reasoning_summary=model.reasoning_summary,
            status=DecisionStatus(model.status),
            created_at=_utc(model.created_at),
            valid_until=_utc(model.valid_until),
        )
    if isinstance(model, ReviewRecord):
        return Review(
            review_id=model.review_id,
            decision_id=model.decision_id,
            actual_return=model.actual_return,
            direction_correct=model.direction_correct,
            risk_limit_breached=model.risk_limit_breached,
            outcome=Outcome(model.outcome),
            cause_tags=tuple(model.cause_tags),
            review_summary=model.review_summary,
            created_at=_utc(model.created_at),
        )
    if isinstance(model, LearningRecord):
        return Learning(
            learning_id=model.learning_id,
            review_id=model.review_id,
            learning_type=LearningType(model.learning_type),
            target=model.target,
            before=model.before,
            after=model.after,
            reason=model.reason,
            approval_status=ApprovalStatus(model.approval_status),
            created_at=_utc(model.created_at),
        )
    msg = f"{type(model).__name__} is not supported by PostgreSQL mapper"
    raise UnsupportedEntityError(msg)


def model_for_entity_type(entity_type: type[KernelModel]) -> type[Record]:
    if entity_type is Evidence:
        return EvidenceRecord
    if entity_type is Experiment:
        return ExperimentRecord
    if entity_type is Decision:
        return DecisionRecord
    if entity_type is Review:
        return ReviewRecord
    if entity_type is Learning:
        return LearningRecord
    msg = f"{entity_type.__name__} is not supported by PostgreSQL mapper"
    raise UnsupportedEntityError(msg)


def id_column_for_model(model_type: type[Record]) -> Any:
    if model_type is EvidenceRecord:
        return EvidenceRecord.evidence_id
    if model_type is ExperimentRecord:
        return ExperimentRecord.experiment_id
    if model_type is DecisionRecord:
        return DecisionRecord.decision_id
    if model_type is ReviewRecord:
        return ReviewRecord.review_id
    if model_type is LearningRecord:
        return LearningRecord.learning_id
    msg = f"{model_type.__name__} is not supported by PostgreSQL mapper"
    raise UnsupportedEntityError(msg)


def _utc(value: datetime) -> datetime:
    return ensure_utc(value)
