from __future__ import annotations

import builtins
from collections.abc import Callable
from datetime import datetime
from typing import cast

from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from aios.kernel.base import KernelModel
from aios.kernel.debate import (
    DebateRecord,
    DebateStatement,
    DecisionAssemblyRecord,
    DecisionProposal,
    RiskReview,
)
from aios.kernel.enums import (
    AgentReportStatus,
    AgentRole,
    HypothesisStatus,
    ResearchSessionStatus,
    WatchlistStatus,
)
from aios.kernel.errors import (
    DuplicateEntityError,
    MissingEntityError,
    StorageOperationError,
)
from aios.kernel.research import ResearchSession
from aios.kernel.research_records import AgentReport, Hypothesis
from aios.kernel.research_run import ResearchRun
from aios.kernel.review import Review
from aios.kernel.settlement import (
    DecisionEvaluation,
    DecisionOutcome,
    ResearchSettlementRecord,
)
from aios.kernel.watchlist import WatchlistItem
from aios.storage.postgres.database import make_engine, make_session_factory
from aios.storage.postgres.mapper import (
    id_column_for_model,
    model_for_entity_type,
    model_to_entity,
    to_model,
)
from aios.storage.postgres.models import (
    AgentReportRecord,
    DebateRecordModel,
    DebateStatementRecord,
    DecisionAssemblyRecordModel,
    DecisionEvaluationRecord,
    DecisionOutcomeRecord,
    DecisionProposalRecord,
    HypothesisRecord,
    ResearchRunRecord,
    ResearchSessionRecord,
    ResearchSettlementRecordModel,
    ReviewRecord,
    RiskReviewRecord,
    WatchlistItemRecord,
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

    def list_watchlist_items(
        self,
        *,
        status: WatchlistStatus | None = WatchlistStatus.ACTIVE,
        market: str | None = None,
        symbol: str | None = None,
    ) -> builtins.list[WatchlistItem]:
        statement = select(WatchlistItemRecord)
        if status is not None:
            statement = statement.where(WatchlistItemRecord.status == status.value)
        if market is not None:
            statement = statement.where(WatchlistItemRecord.market == market)
        if symbol is not None:
            statement = statement.where(WatchlistItemRecord.symbol == symbol)
        statement = statement.order_by(
            WatchlistItemRecord.created_at,
            WatchlistItemRecord.watchlist_item_id,
        )
        session = self._session_factory()
        try:
            return [
                cast("WatchlistItem", model_to_entity(model))
                for model in session.scalars(statement).all()
            ]
        except SQLAlchemyError as exc:
            msg = "failed to list WatchlistItem"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def find_active_watchlist_item(
        self,
        market: str,
        symbol: str,
    ) -> WatchlistItem | None:
        session = self._session_factory()
        try:
            statement = select(WatchlistItemRecord).where(
                WatchlistItemRecord.market == market,
                WatchlistItemRecord.symbol == symbol,
                WatchlistItemRecord.status == WatchlistStatus.ACTIVE.value,
            )
            model = session.scalars(statement).one_or_none()
            if model is None:
                return None
            return cast("WatchlistItem", model_to_entity(model))
        except SQLAlchemyError as exc:
            msg = f"failed to get active WatchlistItem for {market}:{symbol}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def list_research_sessions(
        self,
        *,
        watchlist_item_id: str | None = None,
        symbol: str | None = None,
        market: str | None = None,
        status: ResearchSessionStatus | None = None,
        horizon_days: int | None = None,
    ) -> builtins.list[ResearchSession]:
        statement = select(ResearchSessionRecord)
        if watchlist_item_id is not None:
            statement = statement.where(
                ResearchSessionRecord.watchlist_item_id == watchlist_item_id
            )
        if symbol is not None:
            statement = statement.where(ResearchSessionRecord.symbol == symbol)
        if market is not None:
            statement = statement.where(ResearchSessionRecord.market == market)
        if status is not None:
            statement = statement.where(ResearchSessionRecord.status == status.value)
        if horizon_days is not None:
            statement = statement.where(
                ResearchSessionRecord.horizon_days == horizon_days
            )
        statement = statement.order_by(
            ResearchSessionRecord.created_at,
            ResearchSessionRecord.research_session_id,
        )
        session = self._session_factory()
        try:
            return [
                cast("ResearchSession", model_to_entity(model))
                for model in session.scalars(statement).unique().all()
            ]
        except SQLAlchemyError as exc:
            msg = "failed to list ResearchSession"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def find_active_research_session(
        self,
        watchlist_item_id: str,
        as_of: datetime,
        horizon_days: int,
    ) -> ResearchSession | None:
        session = self._session_factory()
        try:
            statement = select(ResearchSessionRecord).where(
                ResearchSessionRecord.watchlist_item_id == watchlist_item_id,
                ResearchSessionRecord.as_of == as_of,
                ResearchSessionRecord.horizon_days == horizon_days,
                ResearchSessionRecord.status != ResearchSessionStatus.CANCELLED.value,
            )
            model = session.scalars(statement).one_or_none()
            if model is None:
                return None
            return cast("ResearchSession", model_to_entity(model))
        except SQLAlchemyError as exc:
            msg = f"failed to get active ResearchSession for {watchlist_item_id}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def list_agent_reports(
        self,
        *,
        research_session_id: str | None = None,
        role: AgentRole | None = None,
        status: AgentReportStatus | None = None,
    ) -> builtins.list[AgentReport]:
        statement = select(AgentReportRecord)
        if research_session_id is not None:
            statement = statement.where(
                AgentReportRecord.research_session_id == research_session_id
            )
        if role is not None:
            statement = statement.where(AgentReportRecord.role == role.value)
        if status is not None:
            statement = statement.where(AgentReportRecord.status == status.value)
        statement = statement.order_by(
            AgentReportRecord.created_at,
            AgentReportRecord.report_id,
        )
        session = self._session_factory()
        try:
            return [
                cast("AgentReport", model_to_entity(model))
                for model in session.scalars(statement).unique().all()
            ]
        except SQLAlchemyError as exc:
            msg = "failed to list AgentReport"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def find_active_agent_report(
        self,
        research_session_id: str,
        role: AgentRole,
    ) -> AgentReport | None:
        session = self._session_factory()
        try:
            statement = select(AgentReportRecord).where(
                AgentReportRecord.research_session_id == research_session_id,
                AgentReportRecord.role == role.value,
                AgentReportRecord.status == AgentReportStatus.ACTIVE.value,
            )
            model = session.scalars(statement).one_or_none()
            if model is None:
                return None
            return cast("AgentReport", model_to_entity(model))
        except SQLAlchemyError as exc:
            msg = f"failed to get active AgentReport for {research_session_id}:{role}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def list_hypotheses(
        self,
        *,
        research_session_id: str | None = None,
        status: HypothesisStatus | None = None,
    ) -> builtins.list[Hypothesis]:
        statement = select(HypothesisRecord)
        if research_session_id is not None:
            statement = statement.where(
                HypothesisRecord.research_session_id == research_session_id
            )
        if status is not None:
            statement = statement.where(HypothesisRecord.status == status.value)
        statement = statement.order_by(
            HypothesisRecord.created_at,
            HypothesisRecord.hypothesis_id,
        )
        session = self._session_factory()
        try:
            return [
                cast("Hypothesis", model_to_entity(model))
                for model in session.scalars(statement).unique().all()
            ]
        except SQLAlchemyError as exc:
            msg = "failed to list Hypothesis"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def list_debates(
        self,
        *,
        research_session_id: str | None = None,
    ) -> builtins.list[DebateRecord]:
        statement = select(DebateRecordModel)
        if research_session_id is not None:
            statement = statement.where(
                DebateRecordModel.research_session_id == research_session_id
            )
        statement = statement.order_by(
            DebateRecordModel.created_at,
            DebateRecordModel.debate_id,
        )
        session = self._session_factory()
        try:
            return [
                cast("DebateRecord", model_to_entity(model))
                for model in session.scalars(statement).all()
            ]
        except SQLAlchemyError as exc:
            msg = "failed to list DebateRecord"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def get_debate_statement(
        self,
        debate_id: str,
        agent_report_id: str,
        hypothesis_id: str,
    ) -> DebateStatement | None:
        session = self._session_factory()
        try:
            statement = select(DebateStatementRecord).where(
                DebateStatementRecord.debate_id == debate_id,
                DebateStatementRecord.agent_report_id == agent_report_id,
                DebateStatementRecord.hypothesis_id == hypothesis_id,
            )
            model = session.scalars(statement).one_or_none()
            return cast("DebateStatement", model_to_entity(model)) if model else None
        except SQLAlchemyError as exc:
            msg = f"failed to get DebateStatement for {debate_id}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def get_decision_proposal_by_debate_id(
        self,
        debate_id: str,
    ) -> DecisionProposal | None:
        session = self._session_factory()
        try:
            statement = select(DecisionProposalRecord).where(
                DecisionProposalRecord.debate_id == debate_id
            )
            model = session.scalars(statement).one_or_none()
            return cast("DecisionProposal", model_to_entity(model)) if model else None
        except SQLAlchemyError as exc:
            msg = f"failed to get DecisionProposal for {debate_id}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def get_risk_review_by_proposal_id(self, proposal_id: str) -> RiskReview | None:
        session = self._session_factory()
        try:
            statement = select(RiskReviewRecord).where(
                RiskReviewRecord.proposal_id == proposal_id
            )
            model = session.scalars(statement).one_or_none()
            return cast("RiskReview", model_to_entity(model)) if model else None
        except SQLAlchemyError as exc:
            msg = f"failed to get RiskReview for {proposal_id}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def get_decision_assembly_by_proposal_id(
        self,
        proposal_id: str,
    ) -> DecisionAssemblyRecord | None:
        session = self._session_factory()
        try:
            statement = select(DecisionAssemblyRecordModel).where(
                DecisionAssemblyRecordModel.proposal_id == proposal_id
            )
            model = session.scalars(statement).one_or_none()
            return (
                cast("DecisionAssemblyRecord", model_to_entity(model))
                if model
                else None
            )
        except SQLAlchemyError as exc:
            msg = f"failed to get DecisionAssemblyRecord for {proposal_id}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def get_research_settlement_by_assembly_id(
        self,
        assembly_id: str,
    ) -> ResearchSettlementRecord | None:
        session = self._session_factory()
        try:
            statement = select(ResearchSettlementRecordModel).where(
                ResearchSettlementRecordModel.assembly_id == assembly_id
            )
            model = session.scalars(statement).one_or_none()
            return (
                cast("ResearchSettlementRecord", model_to_entity(model))
                if model
                else None
            )
        except SQLAlchemyError as exc:
            msg = f"failed to get ResearchSettlementRecord for {assembly_id}"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def list_research_runs(
        self,
        *,
        watchlist_item_id: str | None = None,
        status: str | None = None,
    ) -> builtins.list[ResearchRun]:
        session = self._session_factory()
        try:
            statement = select(ResearchRunRecord)
            if watchlist_item_id is not None:
                statement = statement.where(
                    ResearchRunRecord.watchlist_item_id == watchlist_item_id
                )
            if status is not None:
                statement = statement.where(ResearchRunRecord.status == status)
            statement = statement.order_by(ResearchRunRecord.created_at)
            return [
                cast("ResearchRun", model_to_entity(model))
                for model in session.scalars(statement)
            ]
        except SQLAlchemyError as exc:
            msg = "failed to list ResearchRun records"
            raise StorageOperationError(msg) from exc
        finally:
            session.close()

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()

    @property
    def database_url(self) -> str | None:
        return self._database_url
