from __future__ import annotations

from collections.abc import Callable
from typing import cast

from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from aios.kernel.base import KernelModel
from aios.kernel.errors import (
    DuplicateEntityError,
    MissingEntityError,
    StorageOperationError,
)
from aios.kernel.review import Review
from aios.kernel.settlement import DecisionEvaluation, DecisionOutcome
from aios.storage.postgres.database import make_engine, make_session_factory
from aios.storage.postgres.mapper import (
    id_column_for_model,
    model_for_entity_type,
    model_to_entity,
    to_model,
)
from aios.storage.postgres.models import (
    DecisionEvaluationRecord,
    DecisionOutcomeRecord,
    ReviewRecord,
)


class PostgresStorage:
    def __init__(
        self,
        database_url: str | None = None,
        *,
        engine: Engine | None = None,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        self._database_url = database_url
        if session_factory is not None:
            self._engine = engine
            self._session_factory = session_factory
            return
        self._engine = engine or make_engine(database_url)
        self._session_factory = make_session_factory(self._engine)

    def save(self, entity: KernelModel) -> None:
        model = to_model(entity)
        model_type = type(model)
        session = self._session_factory()
        try:
            if session.get(model_type, entity.entity_id) is not None:
                msg = (
                    f"{type(entity).__name__} with id {entity.entity_id} already exists"
                )
                raise DuplicateEntityError(msg)
            session.add(model)
            session.commit()
        except DuplicateEntityError:
            session.rollback()
            raise
        except IntegrityError as exc:
            session.rollback()
            msg = f"failed to save {type(entity).__name__} with id {entity.entity_id}"
            raise StorageOperationError(msg) from exc
        except SQLAlchemyError as exc:
            session.rollback()
            msg = f"failed to save {type(entity).__name__} with id {entity.entity_id}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def replace(self, entity: KernelModel) -> None:
        model = to_model(entity)
        model_type = type(model)
        session = self._session_factory()
        try:
            if session.get(model_type, entity.entity_id) is None:
                msg = (
                    f"{type(entity).__name__} with id {entity.entity_id} does not exist"
                )
                raise MissingEntityError(msg)
            session.merge(model)
            session.commit()
        except MissingEntityError:
            session.rollback()
            raise
        except IntegrityError as exc:
            session.rollback()
            msg = (
                f"failed to replace {type(entity).__name__} with id {entity.entity_id}"
            )
            raise StorageOperationError(msg) from exc
        except SQLAlchemyError as exc:
            session.rollback()
            msg = (
                f"failed to replace {type(entity).__name__} with id {entity.entity_id}"
            )
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def get[EntityT: KernelModel](
        self, entity_type: type[EntityT], entity_id: str
    ) -> EntityT:
        model_type = model_for_entity_type(entity_type)
        session = self._session_factory()
        try:
            model = session.get(model_type, entity_id)
            if model is None:
                msg = f"{entity_type.__name__} with id {entity_id} does not exist"
                raise MissingEntityError(msg)
            return cast("EntityT", model_to_entity(model))
        except MissingEntityError:
            raise
        except SQLAlchemyError as exc:
            msg = f"failed to get {entity_type.__name__} with id {entity_id}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def list[EntityT: KernelModel](self, entity_type: type[EntityT]) -> list[EntityT]:
        model_type = model_for_entity_type(entity_type)
        id_column = id_column_for_model(model_type)
        statement = select(model_type).order_by(model_type.created_at, id_column)
        session = self._session_factory()
        try:
            return [
                cast("EntityT", model_to_entity(model))
                for model in session.scalars(statement).all()
            ]
        except SQLAlchemyError as exc:
            msg = f"failed to list {entity_type.__name__}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def exists[EntityT: KernelModel](
        self, entity_type: type[EntityT], entity_id: str
    ) -> bool:
        model_type = model_for_entity_type(entity_type)
        session = self._session_factory()
        try:
            return session.get(model_type, entity_id) is not None
        except SQLAlchemyError as exc:
            msg = f"failed to check {entity_type.__name__} with id {entity_id}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def get_decision_outcome_by_decision_id(
        self,
        decision_id: str,
    ) -> DecisionOutcome | None:
        session = self._session_factory()
        try:
            statement = select(DecisionOutcomeRecord).where(
                DecisionOutcomeRecord.decision_id == decision_id
            )
            model = session.scalars(statement).one_or_none()
            if model is None:
                return None
            return cast("DecisionOutcome", model_to_entity(model))
        except SQLAlchemyError as exc:
            msg = f"failed to get DecisionOutcome for decision {decision_id}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def get_decision_evaluation_by_decision_id(
        self,
        decision_id: str,
        evaluation_rules_version: str,
    ) -> DecisionEvaluation | None:
        session = self._session_factory()
        try:
            statement = select(DecisionEvaluationRecord).where(
                DecisionEvaluationRecord.decision_id == decision_id,
                DecisionEvaluationRecord.evaluation_rules_version
                == evaluation_rules_version,
            )
            model = session.scalars(statement).one_or_none()
            if model is None:
                return None
            return cast("DecisionEvaluation", model_to_entity(model))
        except SQLAlchemyError as exc:
            msg = f"failed to get DecisionEvaluation for decision {decision_id}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def get_review_by_decision_id(self, decision_id: str) -> Review | None:
        session = self._session_factory()
        try:
            statement = select(ReviewRecord).where(
                ReviewRecord.decision_id == decision_id
            )
            model = session.scalars(statement).one_or_none()
            if model is None:
                return None
            return cast("Review", model_to_entity(model))
        except SQLAlchemyError as exc:
            msg = f"failed to get Review for decision {decision_id}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()

    @property
    def database_url(self) -> str | None:
        return self._database_url
