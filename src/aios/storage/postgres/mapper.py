from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy.orm import DeclarativeBase

from aios.kernel.base import KernelModel, ensure_utc
from aios.kernel.brain002 import (
    AnalysisTask,
    SkillDefinition,
    SkillExecution,
    SkillResult,
    TokenUsage,
)
from aios.kernel.brain003 import (
    ConflictReview,
    CounterArgument,
    DiscussionExecution,
    DiscussionResult,
    EvidenceReview,
    RevisionSuggestion,
)
from aios.kernel.brain004 import (
    DecisionExecution,
    DecisionResult,
    DirectionRejection,
    ReferencedReason,
    RiskNote,
)
from aios.kernel.debate import (
    DebateRecord,
    DebateStatement,
    DecisionAssemblyRecord,
    DecisionProposal,
    RiskReview,
)
from aios.kernel.decision import Decision
from aios.kernel.enums import (
    Action,
    AgentReportStatus,
    AgentRole,
    ApprovalStatus,
    DebateStance,
    DebateStatus,
    DecisionDirection,
    DecisionStatus,
    DirectionalResult,
    EvaluationFinalResult,
    ExperimentStatus,
    HypothesisStatus,
    LearningType,
    Outcome,
    OutcomeStatus,
    ResearchConclusion,
    ResearchSessionStatus,
    ReturnResult,
    RiskResult,
    RiskVerdict,
    SkillDirection,
    SkillExecutionStatus,
    SkillStatus,
    WatchlistStatus,
)
from aios.kernel.errors import UnsupportedEntityError
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.research import ResearchScope, ResearchSession
from aios.kernel.research_records import AgentReport, Hypothesis
from aios.kernel.research_run import ResearchRun, ResearchRunStage, ResearchRunStatus
from aios.kernel.review import Review
from aios.kernel.settlement import (
    DecisionEvaluation,
    DecisionOutcome,
    ResearchSettlementRecord,
)
from aios.kernel.watchlist import WatchlistItem
from aios.storage.postgres.models import (
    AgentReportEvidenceRecord,
    AgentReportRecord,
    AnalysisTaskRecord,
    DebateRecordModel,
    DebateStatementRecord,
    DecisionAssemblyRecordModel,
    DecisionEvaluationRecord,
    DecisionExecutionRecord,
    DecisionOutcomeRecord,
    DecisionProposalRecord,
    DecisionRecord,
    DecisionResultRecord,
    DiscussionExecutionRecord,
    DiscussionResultRecord,
    EvidenceRecord,
    ExperimentRecord,
    HypothesisEvidenceRecord,
    HypothesisRecord,
    HypothesisReportRecord,
    LearningRecord,
    ResearchRunRecord,
    ResearchSessionEvidenceRecord,
    ResearchSessionRecord,
    ResearchSettlementRecordModel,
    ReviewRecord,
    RiskReviewRecord,
    SkillDefinitionRecord,
    SkillExecutionRecord,
    SkillResultRecord,
    WatchlistItemRecord,
)

type Record = (
    EvidenceRecord
    | ExperimentRecord
    | DecisionRecord
    | ReviewRecord
    | LearningRecord
    | DecisionOutcomeRecord
    | DecisionEvaluationRecord
    | DecisionExecutionRecord
    | DecisionResultRecord
    | ResearchSettlementRecordModel
    | WatchlistItemRecord
    | ResearchSessionRecord
    | AgentReportRecord
    | HypothesisRecord
    | DebateRecordModel
    | DebateStatementRecord
    | DecisionProposalRecord
    | RiskReviewRecord
    | DecisionAssemblyRecordModel
    | ResearchSettlementRecordModel
    | ResearchRunRecord
    | SkillDefinitionRecord
    | AnalysisTaskRecord
    | SkillExecutionRecord
    | SkillResultRecord
    | DiscussionExecutionRecord
    | DiscussionResultRecord
    | DecisionExecutionRecord
    | DecisionResultRecord
)


def to_model(entity: KernelModel) -> Record:
    if isinstance(entity, SkillDefinition):
        return SkillDefinitionRecord(
            definition_id=entity.definition_id,
            skill_id=entity.skill_id,
            name=entity.name,
            version=entity.version,
            description=entity.description,
            supported_markets=list(entity.supported_markets),
            supported_asset_types=list(entity.supported_asset_types),
            supported_horizons=list(entity.supported_horizons),
            required_evidence_types=list(entity.required_evidence_types),
            input_schema=entity.input_schema,
            output_schema=entity.output_schema,
            trigger_conditions=entity.trigger_conditions,
            dependencies=list(entity.dependencies),
            conflicts=list(entity.conflicts),
            status=entity.status.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
    if isinstance(entity, AnalysisTask):
        return AnalysisTaskRecord(
            task_id=entity.task_id,
            symbol=entity.symbol,
            market=entity.market,
            asset_type=entity.asset_type,
            horizon=entity.horizon,
            as_of=entity.as_of,
            evidence_ids=list(entity.evidence_ids),
            user_constraints=entity.user_constraints,
            requested_skill_ids=list(entity.requested_skill_ids),
            created_at=entity.created_at,
        )
    if isinstance(entity, SkillExecution):
        return SkillExecutionRecord(
            execution_id=entity.execution_id,
            task_id=entity.task_id,
            skill_id=entity.skill_id,
            skill_version=entity.skill_version,
            started_at=entity.started_at,
            finished_at=entity.finished_at,
            status=entity.status.value,
            provider=entity.provider,
            model=entity.model,
            prompt_version=entity.prompt_version,
            token_usage=entity.token_usage.model_dump(mode="json"),
            latency_ms=entity.latency_ms,
            retry_count=entity.retry_count,
            error=entity.error,
        )
    if isinstance(entity, SkillResult):
        return SkillResultRecord(
            result_id=entity.result_id,
            execution_id=entity.execution_id,
            skill_id=entity.skill_id,
            skill_version=entity.skill_version,
            conclusion=entity.conclusion,
            direction=entity.direction.value,
            confidence=entity.confidence,
            supporting_evidence_ids=list(entity.supporting_evidence_ids),
            contradicting_evidence_ids=list(entity.contradicting_evidence_ids),
            assumptions=list(entity.assumptions),
            risk_factors=list(entity.risk_factors),
            invalid_conditions=list(entity.invalid_conditions),
            missing_information=list(entity.missing_information),
            reasoning_summary=entity.reasoning_summary,
            raw_output=entity.raw_output,
            created_at=entity.created_at,
        )
    if isinstance(entity, DiscussionExecution):
        return DiscussionExecutionRecord(
            discussion_execution_id=entity.discussion_execution_id,
            task_id=entity.task_id,
            skill_result_ids=list(entity.skill_result_ids),
            started_at=entity.started_at,
            finished_at=entity.finished_at,
            status=entity.status.value,
            provider=entity.provider,
            model=entity.model,
            prompt_version=entity.prompt_version,
            token_usage=entity.token_usage.model_dump(mode="json"),
            latency_ms=entity.latency_ms,
            retry_count=entity.retry_count,
            raw_response=entity.raw_response,
            parsed_response=entity.parsed_response,
            error=entity.error,
            created_at=entity.created_at,
        )
    if isinstance(entity, DiscussionResult):
        return DiscussionResultRecord(
            discussion_result_id=entity.discussion_result_id,
            discussion_execution_id=entity.discussion_execution_id,
            task_id=entity.task_id,
            skill_result_ids=list(entity.skill_result_ids),
            conflicts=[item.model_dump(mode="json") for item in entity.conflicts],
            evidence_reviews=[
                item.model_dump(mode="json") for item in entity.evidence_reviews
            ],
            counter_arguments=[
                item.model_dump(mode="json") for item in entity.counter_arguments
            ],
            revision_suggestions=[
                item.model_dump(mode="json") for item in entity.revision_suggestions
            ],
            discussion_summary=entity.discussion_summary,
            discussion_confidence=entity.discussion_confidence,
            created_at=entity.created_at,
        )
    if isinstance(entity, DecisionExecution):
        return DecisionExecutionRecord(
            decision_execution_id=entity.decision_execution_id,
            task_id=entity.task_id,
            discussion_result_id=entity.discussion_result_id,
            skill_result_ids=list(entity.skill_result_ids),
            evidence_ids=list(entity.evidence_ids),
            started_at=entity.started_at,
            finished_at=entity.finished_at,
            status=entity.status.value,
            provider=entity.provider,
            model=entity.model,
            prompt_version=entity.prompt_version,
            token_usage=entity.token_usage.model_dump(mode="json"),
            latency_ms=entity.latency_ms,
            retry_count=entity.retry_count,
            raw_response=entity.raw_response,
            parsed_response=entity.parsed_response,
            error=entity.error,
            created_at=entity.created_at,
        )
    if isinstance(entity, DecisionResult):
        return DecisionResultRecord(
            decision_result_id=entity.decision_result_id,
            decision_execution_id=entity.decision_execution_id,
            task_id=entity.task_id,
            discussion_result_id=entity.discussion_result_id,
            skill_result_ids=list(entity.skill_result_ids),
            direction=entity.direction.value,
            confidence=entity.confidence,
            action=entity.action.value,
            reasoning=[item.model_dump(mode="json") for item in entity.reasoning],
            supporting_skills=list(entity.supporting_skills),
            opposing_skills=list(entity.opposing_skills),
            discussion_refs=list(entity.discussion_refs),
            evidence_refs=list(entity.evidence_refs),
            risks=[item.model_dump(mode="json") for item in entity.risks],
            rejected_directions=[
                item.model_dump(mode="json") for item in entity.rejected_directions
            ],
            decision_summary=entity.decision_summary,
            created_at=entity.created_at,
        )
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
    if isinstance(entity, ResearchSettlementRecord):
        return ResearchSettlementRecordModel(
            research_settlement_id=entity.research_settlement_id,
            assembly_id=entity.assembly_id,
            research_session_id=entity.research_session_id,
            debate_id=entity.debate_id,
            proposal_id=entity.proposal_id,
            risk_review_id=entity.risk_review_id,
            decision_id=entity.decision_id,
            outcome_id=entity.outcome_id,
            evaluation_id=entity.evaluation_id,
            review_id=entity.review_id,
            learning_ids=list(entity.learning_ids),
            evidence_ids=list(entity.evidence_ids),
            report_ids=list(entity.report_ids),
            hypothesis_ids=list(entity.hypothesis_ids),
            settled_at=entity.settled_at,
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
    if isinstance(entity, WatchlistItem):
        return WatchlistItemRecord(
            watchlist_item_id=entity.watchlist_item_id,
            symbol=entity.symbol,
            market=entity.market,
            note=entity.note,
            status=entity.status.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            archived_at=entity.archived_at,
        )
    if isinstance(entity, ResearchSession):
        return ResearchSessionRecord(
            research_session_id=entity.research_session_id,
            watchlist_item_id=entity.scope.watchlist_item_id,
            symbol=entity.scope.symbol,
            market=entity.scope.market,
            watchlist_note_snapshot=entity.scope.watchlist_note_snapshot,
            horizon_days=entity.scope.horizon_days,
            as_of=entity.scope.as_of,
            valid_until=entity.scope.valid_until,
            status=entity.status.value,
            experiment_id=entity.experiment_id,
            cancelled_at=entity.cancelled_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            evidence_links=[
                ResearchSessionEvidenceRecord(
                    research_session_id=entity.research_session_id,
                    evidence_id=evidence_id,
                    position=position,
                )
                for position, evidence_id in enumerate(entity.evidence_ids)
            ],
        )
    if isinstance(entity, AgentReport):
        return AgentReportRecord(
            report_id=entity.report_id,
            research_session_id=entity.research_session_id,
            role=entity.role.value,
            summary=entity.summary,
            stance=entity.stance,
            confidence=entity.confidence,
            source=entity.source,
            raw_reference=entity.raw_reference,
            status=entity.status.value,
            archived_at=entity.archived_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            evidence_links=[
                AgentReportEvidenceRecord(
                    report_id=entity.report_id,
                    evidence_id=evidence_id,
                    position=position,
                )
                for position, evidence_id in enumerate(entity.evidence_ids)
            ],
        )
    if isinstance(entity, Hypothesis):
        return HypothesisRecord(
            hypothesis_id=entity.hypothesis_id,
            research_session_id=entity.research_session_id,
            statement=entity.statement,
            rationale=entity.rationale,
            direction=entity.direction,
            horizon_days=entity.horizon_days,
            confidence=entity.confidence,
            status=entity.status.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            report_links=[
                HypothesisReportRecord(
                    hypothesis_id=entity.hypothesis_id,
                    report_id=report_id,
                    position=position,
                )
                for position, report_id in enumerate(entity.supporting_report_ids)
            ],
            evidence_links=[
                HypothesisEvidenceRecord(
                    hypothesis_id=entity.hypothesis_id,
                    evidence_id=evidence_id,
                    position=position,
                )
                for position, evidence_id in enumerate(entity.supporting_evidence_ids)
            ],
        )
    if isinstance(entity, DebateRecord):
        return DebateRecordModel(
            debate_id=entity.debate_id,
            research_session_id=entity.research_session_id,
            report_ids=list(entity.report_ids),
            hypothesis_ids=list(entity.hypothesis_ids),
            status=entity.status.value,
            final_decision_id=entity.final_decision_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
    if isinstance(entity, DebateStatement):
        return DebateStatementRecord(
            statement_id=entity.statement_id,
            debate_id=entity.debate_id,
            agent_report_id=entity.agent_report_id,
            hypothesis_id=entity.hypothesis_id,
            stance=entity.stance.value,
            reasoning=entity.reasoning,
            evidence_ids=list(entity.evidence_ids),
            confidence_before=entity.confidence_before,
            confidence_after=entity.confidence_after,
            created_at=entity.created_at,
        )
    if isinstance(entity, DecisionProposal):
        return DecisionProposalRecord(
            proposal_id=entity.proposal_id,
            debate_id=entity.debate_id,
            conclusion=entity.conclusion.value,
            confidence=entity.confidence,
            thesis=entity.thesis,
            supporting_hypothesis_ids=list(entity.supporting_hypothesis_ids),
            rejected_hypothesis_ids=list(entity.rejected_hypothesis_ids),
            evidence_ids=list(entity.evidence_ids),
            risk_notes=list(entity.risk_notes),
            created_at=entity.created_at,
        )
    if isinstance(entity, RiskReview):
        return RiskReviewRecord(
            risk_review_id=entity.risk_review_id,
            proposal_id=entity.proposal_id,
            verdict=entity.verdict.value,
            final_conclusion=entity.final_conclusion.value,
            final_confidence=entity.final_confidence,
            reasons=list(entity.reasons),
            created_at=entity.created_at,
        )
    if isinstance(entity, DecisionAssemblyRecord):
        return DecisionAssemblyRecordModel(
            assembly_id=entity.assembly_id,
            research_session_id=entity.research_session_id,
            debate_id=entity.debate_id,
            proposal_id=entity.proposal_id,
            risk_review_id=entity.risk_review_id,
            decision_id=entity.decision_id,
            conclusion=entity.conclusion.value,
            report_ids=list(entity.report_ids),
            hypothesis_ids=list(entity.hypothesis_ids),
            evidence_ids=list(entity.evidence_ids),
            created_at=entity.created_at,
        )
    if isinstance(entity, ResearchRun):
        return ResearchRunRecord(
            run_id=entity.run_id,
            research_session_id=entity.research_session_id,
            watchlist_item_id=entity.watchlist_item_id,
            current_stage=entity.current_stage,
            status=entity.status,
            vibe_run_id=entity.vibe_run_id,
            workflow=entity.workflow,
            input_params=entity.input_params,
            raw_output_reference=entity.raw_output_reference,
            error=entity.error,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
    msg = f"{type(entity).__name__} is not supported by PostgreSQL mapper"
    raise UnsupportedEntityError(msg)


def model_to_entity(model: DeclarativeBase) -> KernelModel:
    if isinstance(model, SkillDefinitionRecord):
        return SkillDefinition(
            definition_id=model.definition_id,
            skill_id=model.skill_id,
            name=model.name,
            version=model.version,
            description=model.description,
            supported_markets=tuple(model.supported_markets),
            supported_asset_types=tuple(model.supported_asset_types),
            supported_horizons=tuple(model.supported_horizons),
            required_evidence_types=tuple(model.required_evidence_types),
            input_schema=model.input_schema,
            output_schema=model.output_schema,
            trigger_conditions=model.trigger_conditions,
            dependencies=tuple(model.dependencies),
            conflicts=tuple(model.conflicts),
            status=SkillStatus(model.status),
            created_at=_utc(model.created_at),
            updated_at=_utc(model.updated_at),
        )
    if isinstance(model, AnalysisTaskRecord):
        return AnalysisTask(
            task_id=model.task_id,
            symbol=model.symbol,
            market=model.market,
            asset_type=model.asset_type,
            horizon=model.horizon,
            as_of=_utc(model.as_of),
            evidence_ids=tuple(model.evidence_ids),
            user_constraints=model.user_constraints,
            requested_skill_ids=tuple(model.requested_skill_ids),
            created_at=_utc(model.created_at),
        )
    if isinstance(model, SkillExecutionRecord):
        return SkillExecution(
            execution_id=model.execution_id,
            task_id=model.task_id,
            skill_id=model.skill_id,
            skill_version=model.skill_version,
            started_at=_utc(model.started_at),
            finished_at=_utc(model.finished_at) if model.finished_at else None,
            status=SkillExecutionStatus(model.status),
            provider=model.provider,
            model=model.model,
            prompt_version=model.prompt_version,
            token_usage=TokenUsage.model_validate(model.token_usage),
            latency_ms=model.latency_ms,
            retry_count=model.retry_count,
            error=model.error,
        )
    if isinstance(model, SkillResultRecord):
        return SkillResult(
            result_id=model.result_id,
            execution_id=model.execution_id,
            skill_id=model.skill_id,
            skill_version=model.skill_version,
            conclusion=model.conclusion,
            direction=SkillDirection(model.direction),
            confidence=model.confidence,
            supporting_evidence_ids=tuple(model.supporting_evidence_ids),
            contradicting_evidence_ids=tuple(model.contradicting_evidence_ids),
            assumptions=tuple(model.assumptions),
            risk_factors=tuple(model.risk_factors),
            invalid_conditions=tuple(model.invalid_conditions),
            missing_information=tuple(model.missing_information),
            reasoning_summary=model.reasoning_summary,
            raw_output=model.raw_output,
            created_at=_utc(model.created_at),
        )
    if isinstance(model, DiscussionExecutionRecord):
        return DiscussionExecution(
            discussion_execution_id=model.discussion_execution_id,
            task_id=model.task_id,
            skill_result_ids=tuple(model.skill_result_ids),
            started_at=_utc(model.started_at),
            finished_at=_utc(model.finished_at) if model.finished_at else None,
            status=SkillExecutionStatus(model.status),
            provider=model.provider,
            model=model.model,
            prompt_version=model.prompt_version,
            token_usage=TokenUsage.model_validate(model.token_usage),
            latency_ms=model.latency_ms,
            retry_count=model.retry_count,
            raw_response=model.raw_response,
            parsed_response=model.parsed_response,
            error=model.error,
            created_at=_utc(model.created_at),
        )
    if isinstance(model, DiscussionResultRecord):
        return DiscussionResult(
            discussion_result_id=model.discussion_result_id,
            discussion_execution_id=model.discussion_execution_id,
            task_id=model.task_id,
            skill_result_ids=tuple(model.skill_result_ids),
            conflicts=tuple(
                ConflictReview.model_validate(item) for item in model.conflicts
            ),
            evidence_reviews=tuple(
                EvidenceReview.model_validate(item) for item in model.evidence_reviews
            ),
            counter_arguments=tuple(
                CounterArgument.model_validate(item) for item in model.counter_arguments
            ),
            revision_suggestions=tuple(
                RevisionSuggestion.model_validate(item)
                for item in model.revision_suggestions
            ),
            discussion_summary=model.discussion_summary,
            discussion_confidence=model.discussion_confidence,
            created_at=_utc(model.created_at),
        )
    if isinstance(model, DecisionExecutionRecord):
        return DecisionExecution(
            decision_execution_id=model.decision_execution_id,
            task_id=model.task_id,
            discussion_result_id=model.discussion_result_id,
            skill_result_ids=tuple(model.skill_result_ids),
            evidence_ids=tuple(model.evidence_ids),
            started_at=_utc(model.started_at),
            finished_at=_utc(model.finished_at) if model.finished_at else None,
            status=SkillExecutionStatus(model.status),
            provider=model.provider,
            model=model.model,
            prompt_version=model.prompt_version,
            token_usage=TokenUsage.model_validate(model.token_usage),
            latency_ms=model.latency_ms,
            retry_count=model.retry_count,
            raw_response=model.raw_response,
            parsed_response=model.parsed_response,
            error=model.error,
            created_at=_utc(model.created_at),
        )
    if isinstance(model, DecisionResultRecord):
        return DecisionResult(
            decision_result_id=model.decision_result_id,
            decision_execution_id=model.decision_execution_id,
            task_id=model.task_id,
            discussion_result_id=model.discussion_result_id,
            skill_result_ids=tuple(model.skill_result_ids),
            direction=DecisionDirection(model.direction),
            confidence=model.confidence,
            action=Action(model.action),
            reasoning=tuple(
                ReferencedReason.model_validate(item) for item in model.reasoning
            ),
            supporting_skills=tuple(model.supporting_skills),
            opposing_skills=tuple(model.opposing_skills),
            discussion_refs=tuple(model.discussion_refs),
            evidence_refs=tuple(model.evidence_refs),
            risks=tuple(RiskNote.model_validate(item) for item in model.risks),
            rejected_directions=tuple(
                DirectionRejection.model_validate(item)
                for item in model.rejected_directions
            ),
            decision_summary=model.decision_summary,
            created_at=_utc(model.created_at),
        )
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
    if isinstance(model, ResearchSettlementRecordModel):
        return ResearchSettlementRecord(
            research_settlement_id=model.research_settlement_id,
            assembly_id=model.assembly_id,
            research_session_id=model.research_session_id,
            debate_id=model.debate_id,
            proposal_id=model.proposal_id,
            risk_review_id=model.risk_review_id,
            decision_id=model.decision_id,
            outcome_id=model.outcome_id,
            evaluation_id=model.evaluation_id,
            review_id=model.review_id,
            learning_ids=tuple(model.learning_ids),
            evidence_ids=tuple(model.evidence_ids),
            report_ids=tuple(model.report_ids),
            hypothesis_ids=tuple(model.hypothesis_ids),
            settled_at=_utc(model.settled_at),
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
    if isinstance(model, WatchlistItemRecord):
        return WatchlistItem(
            watchlist_item_id=model.watchlist_item_id,
            symbol=model.symbol,
            market=model.market,
            note=model.note,
            status=WatchlistStatus(model.status),
            created_at=_utc(model.created_at),
            updated_at=_utc(model.updated_at),
            archived_at=_utc(model.archived_at) if model.archived_at else None,
        )
    if isinstance(model, ResearchSessionRecord):
        return ResearchSession(
            research_session_id=model.research_session_id,
            scope=ResearchScope(
                watchlist_item_id=model.watchlist_item_id,
                symbol=model.symbol,
                market=model.market,
                watchlist_note_snapshot=model.watchlist_note_snapshot,
                horizon_days=model.horizon_days,
                as_of=_utc(model.as_of),
                valid_until=_utc(model.valid_until),
            ),
            status=ResearchSessionStatus(model.status),
            evidence_ids=tuple(link.evidence_id for link in model.evidence_links),
            experiment_id=model.experiment_id,
            cancelled_at=_utc(model.cancelled_at) if model.cancelled_at else None,
            created_at=_utc(model.created_at),
            updated_at=_utc(model.updated_at),
        )
    if isinstance(model, AgentReportRecord):
        return AgentReport(
            report_id=model.report_id,
            research_session_id=model.research_session_id,
            role=AgentRole(model.role),
            summary=model.summary,
            stance=model.stance,
            confidence=model.confidence,
            evidence_ids=tuple(link.evidence_id for link in model.evidence_links),
            source=model.source,
            raw_reference=model.raw_reference,
            status=AgentReportStatus(model.status),
            archived_at=_utc(model.archived_at) if model.archived_at else None,
            created_at=_utc(model.created_at),
            updated_at=_utc(model.updated_at),
        )
    if isinstance(model, HypothesisRecord):
        return Hypothesis(
            hypothesis_id=model.hypothesis_id,
            research_session_id=model.research_session_id,
            statement=model.statement,
            rationale=model.rationale,
            direction=model.direction,
            horizon_days=model.horizon_days,
            confidence=model.confidence,
            supporting_report_ids=tuple(link.report_id for link in model.report_links),
            supporting_evidence_ids=tuple(
                link.evidence_id for link in model.evidence_links
            ),
            status=HypothesisStatus(model.status),
            created_at=_utc(model.created_at),
            updated_at=_utc(model.updated_at),
        )
    if isinstance(model, DebateRecordModel):
        return DebateRecord(
            debate_id=model.debate_id,
            research_session_id=model.research_session_id,
            report_ids=tuple(model.report_ids),
            hypothesis_ids=tuple(model.hypothesis_ids),
            status=DebateStatus(model.status),
            final_decision_id=model.final_decision_id,
            created_at=_utc(model.created_at),
            updated_at=_utc(model.updated_at),
        )
    if isinstance(model, DebateStatementRecord):
        return DebateStatement(
            statement_id=model.statement_id,
            debate_id=model.debate_id,
            agent_report_id=model.agent_report_id,
            hypothesis_id=model.hypothesis_id,
            stance=DebateStance(model.stance),
            reasoning=model.reasoning,
            evidence_ids=tuple(model.evidence_ids),
            confidence_before=model.confidence_before,
            confidence_after=model.confidence_after,
            created_at=_utc(model.created_at),
        )
    if isinstance(model, DecisionProposalRecord):
        return DecisionProposal(
            proposal_id=model.proposal_id,
            debate_id=model.debate_id,
            conclusion=ResearchConclusion(model.conclusion),
            confidence=model.confidence,
            thesis=model.thesis,
            supporting_hypothesis_ids=tuple(model.supporting_hypothesis_ids),
            rejected_hypothesis_ids=tuple(model.rejected_hypothesis_ids),
            evidence_ids=tuple(model.evidence_ids),
            risk_notes=tuple(model.risk_notes),
            created_at=_utc(model.created_at),
        )
    if isinstance(model, RiskReviewRecord):
        return RiskReview(
            risk_review_id=model.risk_review_id,
            proposal_id=model.proposal_id,
            verdict=RiskVerdict(model.verdict),
            final_conclusion=ResearchConclusion(model.final_conclusion),
            final_confidence=model.final_confidence,
            reasons=tuple(model.reasons),
            created_at=_utc(model.created_at),
        )
    if isinstance(model, DecisionAssemblyRecordModel):
        return DecisionAssemblyRecord(
            assembly_id=model.assembly_id,
            research_session_id=model.research_session_id,
            debate_id=model.debate_id,
            proposal_id=model.proposal_id,
            risk_review_id=model.risk_review_id,
            decision_id=model.decision_id,
            conclusion=ResearchConclusion(model.conclusion),
            report_ids=tuple(model.report_ids),
            hypothesis_ids=tuple(model.hypothesis_ids),
            evidence_ids=tuple(model.evidence_ids),
            created_at=_utc(model.created_at),
        )
    if isinstance(model, ResearchRunRecord):
        return ResearchRun(
            run_id=model.run_id,
            research_session_id=model.research_session_id,
            watchlist_item_id=model.watchlist_item_id,
            current_stage=cast("ResearchRunStage", model.current_stage),
            status=cast("ResearchRunStatus", model.status),
            vibe_run_id=model.vibe_run_id,
            workflow=model.workflow,
            input_params=model.input_params,
            raw_output_reference=model.raw_output_reference,
            error=model.error,
            created_at=_utc(model.created_at),
            updated_at=_utc(model.updated_at),
        )
    msg = f"{type(model).__name__} is not supported by PostgreSQL mapper"
    raise UnsupportedEntityError(msg)


def model_for_entity_type(entity_type: type[KernelModel]) -> type[Record]:
    if entity_type is SkillDefinition:
        return SkillDefinitionRecord
    if entity_type is AnalysisTask:
        return AnalysisTaskRecord
    if entity_type is SkillExecution:
        return SkillExecutionRecord
    if entity_type is SkillResult:
        return SkillResultRecord
    if entity_type is DiscussionExecution:
        return DiscussionExecutionRecord
    if entity_type is DiscussionResult:
        return DiscussionResultRecord
    if entity_type is DecisionExecution:
        return DecisionExecutionRecord
    if entity_type is DecisionResult:
        return DecisionResultRecord
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
    if entity_type is ResearchSettlementRecord:
        return ResearchSettlementRecordModel
    if entity_type is Review:
        return ReviewRecord
    if entity_type is Learning:
        return LearningRecord
    if entity_type is WatchlistItem:
        return WatchlistItemRecord
    if entity_type is ResearchSession:
        return ResearchSessionRecord
    if entity_type is AgentReport:
        return AgentReportRecord
    if entity_type is Hypothesis:
        return HypothesisRecord
    if entity_type is DebateRecord:
        return DebateRecordModel
    if entity_type is DebateStatement:
        return DebateStatementRecord
    if entity_type is DecisionProposal:
        return DecisionProposalRecord
    if entity_type is RiskReview:
        return RiskReviewRecord
    if entity_type is DecisionAssemblyRecord:
        return DecisionAssemblyRecordModel
    if entity_type is ResearchRun:
        return ResearchRunRecord
    msg = f"{entity_type.__name__} is not supported by PostgreSQL mapper"
    raise UnsupportedEntityError(msg)


def id_column_for_model(model_type: type[Record]) -> Any:
    if model_type is SkillDefinitionRecord:
        return SkillDefinitionRecord.definition_id
    if model_type is AnalysisTaskRecord:
        return AnalysisTaskRecord.task_id
    if model_type is SkillExecutionRecord:
        return SkillExecutionRecord.execution_id
    if model_type is SkillResultRecord:
        return SkillResultRecord.result_id
    if model_type is DiscussionExecutionRecord:
        return DiscussionExecutionRecord.discussion_execution_id
    if model_type is DiscussionResultRecord:
        return DiscussionResultRecord.discussion_result_id
    if model_type is DecisionExecutionRecord:
        return DecisionExecutionRecord.decision_execution_id
    if model_type is DecisionResultRecord:
        return DecisionResultRecord.decision_result_id
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
    if model_type is ResearchSettlementRecordModel:
        return ResearchSettlementRecordModel.research_settlement_id
    if model_type is ReviewRecord:
        return ReviewRecord.review_id
    if model_type is LearningRecord:
        return LearningRecord.learning_id
    if model_type is WatchlistItemRecord:
        return WatchlistItemRecord.watchlist_item_id
    if model_type is ResearchSessionRecord:
        return ResearchSessionRecord.research_session_id
    if model_type is AgentReportRecord:
        return AgentReportRecord.report_id
    if model_type is HypothesisRecord:
        return HypothesisRecord.hypothesis_id
    if model_type is DebateRecordModel:
        return DebateRecordModel.debate_id
    if model_type is DebateStatementRecord:
        return DebateStatementRecord.statement_id
    if model_type is DecisionProposalRecord:
        return DecisionProposalRecord.proposal_id
    if model_type is RiskReviewRecord:
        return RiskReviewRecord.risk_review_id
    if model_type is DecisionAssemblyRecordModel:
        return DecisionAssemblyRecordModel.assembly_id
    if model_type is ResearchRunRecord:
        return ResearchRunRecord.run_id
    msg = f"{model_type.__name__} is not supported by PostgreSQL mapper"
    raise UnsupportedEntityError(msg)


def _utc(value: datetime) -> datetime:
    return ensure_utc(value)
