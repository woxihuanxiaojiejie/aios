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
    DirectionalResult,
    EvaluationFinalResult,
    ExperimentStatus,
    LearningType,
    Outcome,
    OutcomeStatus,
    ReturnResult,
    RiskResult,
)
from aios.kernel.errors import UnsupportedEntityError
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.review import Review
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.storage.postgres.models import (
    DecisionEvaluationRecord,
    DecisionOutcomeRecord,
    DecisionRecord,
    EvidenceRecord,
    ExperimentRecord,
    LearningRecord,
    ReviewRecord,
)

type Record = (
    EvidenceRecord
    | ExperimentRecord
    | DecisionRecord
    | ReviewRecord
    | LearningRecord
    | DecisionOutcomeRecord
    | DecisionEvaluationRecord
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
    if isinstance(entity, DecisionOutcome):
        return DecisionOutcomeRecord(
            outcome_id=entity.outcome_id,
            decision_id=entity.decision_id,
            experiment_id=entity.experiment_id,
            symbol=entity.symbol,
            horizon=entity.horizon,
            horizon_semantics=entity.horizon_semantics,
            observation_started_at=entity.observation_started_at,
            observation_ended_at=entity.observation_ended_at,
            entry_price=entity.entry_price,
            exit_price=entity.exit_price,
            realized_return=entity.realized_return,
            maximum_adverse_excursion=entity.maximum_adverse_excursion,
            maximum_favorable_excursion=entity.maximum_favorable_excursion,
            market_data_source=entity.market_data_source,
            market_data_snapshot=entity.market_data_snapshot,
            settled_at=entity.settled_at,
            status=entity.status.value,
            created_at=entity.created_at,
        )
    if isinstance(entity, DecisionEvaluation):
        return DecisionEvaluationRecord(
            evaluation_id=entity.evaluation_id,
            decision_id=entity.decision_id,
            outcome_id=entity.outcome_id,
            experiment_id=entity.experiment_id,
            directional_result=entity.directional_result.value,
            return_result=entity.return_result.value,
            risk_result=entity.risk_result.value,
            final_result=entity.final_result.value,
            evaluation_rules_version=entity.evaluation_rules_version,
            evaluated_at=entity.evaluated_at,
            explanation=entity.explanation,
            created_at=entity.created_at,
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
    if isinstance(model, DecisionOutcomeRecord):
        return DecisionOutcome(
            outcome_id=model.outcome_id,
            decision_id=model.decision_id,
            experiment_id=model.experiment_id,
            symbol=model.symbol,
            horizon=model.horizon,
            horizon_semantics=model.horizon_semantics,
            observation_started_at=_utc(model.observation_started_at),
            observation_ended_at=_utc(model.observation_ended_at),
            entry_price=model.entry_price,
            exit_price=model.exit_price,
            realized_return=model.realized_return,
            maximum_adverse_excursion=model.maximum_adverse_excursion,
            maximum_favorable_excursion=model.maximum_favorable_excursion,
            market_data_source=model.market_data_source,
            market_data_snapshot=model.market_data_snapshot,
            settled_at=_utc(model.settled_at),
            status=OutcomeStatus(model.status),
            created_at=_utc(model.created_at),
        )
    if isinstance(model, DecisionEvaluationRecord):
        return DecisionEvaluation(
            evaluation_id=model.evaluation_id,
            decision_id=model.decision_id,
            outcome_id=model.outcome_id,
            experiment_id=model.experiment_id,
            directional_result=DirectionalResult(model.directional_result),
            return_result=ReturnResult(model.return_result),
            risk_result=RiskResult(model.risk_result),
            final_result=EvaluationFinalResult(model.final_result),
            evaluation_rules_version=model.evaluation_rules_version,
            evaluated_at=_utc(model.evaluated_at),
            explanation=model.explanation,
            created_at=_utc(model.created_at),
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
    if entity_type is DecisionOutcome:
        return DecisionOutcomeRecord
    if entity_type is DecisionEvaluation:
        return DecisionEvaluationRecord
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
    if model_type is DecisionOutcomeRecord:
        return DecisionOutcomeRecord.outcome_id
    if model_type is DecisionEvaluationRecord:
        return DecisionEvaluationRecord.evaluation_id
    if model_type is ReviewRecord:
        return ReviewRecord.review_id
    if model_type is LearningRecord:
        return LearningRecord.learning_id
    msg = f"{model_type.__name__} is not supported by PostgreSQL mapper"
    raise UnsupportedEntityError(msg)


def _utc(value: datetime) -> datetime:
    return ensure_utc(value)
