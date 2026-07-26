from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class EvidenceRecord(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint(
            "reliability >= 0 and reliability <= 1", "ck_evidence_reliability"
        ),
        CheckConstraint("available_at >= published_at", "ck_evidence_available_at"),
        Index("ix_evidence_content_hash", "content_hash"),
        Index("ix_evidence_published_at", "published_at"),
    )

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    evidence_type: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    symbols: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    summary: Mapped[str] = mapped_column(String, nullable=False)
    reliability: Mapped[float] = mapped_column(Float, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class BrainEvidenceRecord(Base):
    __tablename__ = "brain_evidence"
    __table_args__ = (
        CheckConstraint(
            "available_at >= collected_at", "ck_brain_evidence_available_at"
        ),
        Index("ix_brain_evidence_fingerprint", "fingerprint"),
        Index("ix_brain_evidence_source", "source"),
        Index("ix_brain_evidence_source_type", "source_type"),
        Index("ix_brain_evidence_published_at", "published_at"),
        Index("ix_brain_evidence_collected_at", "collected_at"),
        Index("ix_brain_evidence_available_at", "available_at"),
    )

    evidence_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_identifier: Mapped[str | None] = mapped_column(String(1024))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str | None] = mapped_column(String)
    content: Mapped[str] = mapped_column(String, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_artifact_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    provider_record_json: Mapped[dict[str, Any]] = mapped_column(
        "provider_record", JSONB, nullable=False
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False
    )


class SkillDefinitionRecord(Base):
    __tablename__ = "skill_definitions"
    __table_args__ = (
        UniqueConstraint("skill_id", "version", name="uq_skill_definitions_version"),
        Index("ix_skill_definitions_skill_id", "skill_id"),
        Index("ix_skill_definitions_status", "status"),
        Index("ix_skill_definitions_created_at", "created_at"),
    )

    definition_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    skill_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    supported_markets: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    supported_asset_types: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    supported_horizons: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    required_evidence_types: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    trigger_conditions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    dependencies: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    conflicts: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AnalysisTaskRecord(Base):
    __tablename__ = "analysis_tasks"
    __table_args__ = (
        Index("ix_analysis_tasks_symbol", "symbol"),
        Index("ix_analysis_tasks_market", "market"),
        Index("ix_analysis_tasks_as_of", "as_of"),
        Index("ix_analysis_tasks_created_at", "created_at"),
    )

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    horizon: Mapped[str] = mapped_column(String(64), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    user_constraints: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    requested_skill_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class SkillExecutionRecord(Base):
    __tablename__ = "skill_executions"
    __table_args__ = (
        CheckConstraint(
            "finished_at is null or finished_at >= started_at",
            "ck_skill_executions_finished_at",
        ),
        CheckConstraint("latency_ms is null or latency_ms >= 0"),
        CheckConstraint("retry_count >= 0"),
        Index("ix_skill_executions_task_id", "task_id"),
        Index("ix_skill_executions_skill_id", "skill_id"),
        Index("ix_skill_executions_status", "status"),
        Index("ix_skill_executions_started_at", "started_at"),
    )

    execution_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    skill_id: Mapped[str] = mapped_column(String(128), nullable=False)
    skill_version: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(255))
    prompt_version: Mapped[str | None] = mapped_column(String(128))
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    error: Mapped[str | None] = mapped_column(String)


class SkillResultRecord(Base):
    __tablename__ = "skill_results"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 and confidence <= 1", "ck_skill_results_confidence"
        ),
        Index("ix_skill_results_execution_id", "execution_id"),
        Index("ix_skill_results_skill_id", "skill_id"),
        Index("ix_skill_results_direction", "direction"),
        Index("ix_skill_results_created_at", "created_at"),
    )

    result_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    execution_id: Mapped[str] = mapped_column(String(64), nullable=False)
    skill_id: Mapped[str] = mapped_column(String(128), nullable=False)
    skill_version: Mapped[str] = mapped_column(String(64), nullable=False)
    conclusion: Mapped[str] = mapped_column(String, nullable=False)
    direction: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    supporting_evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    contradicting_evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    assumptions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    risk_factors: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    invalid_conditions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    missing_information: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    reasoning_summary: Mapped[str] = mapped_column(String, nullable=False)
    raw_output: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DiscussionExecutionRecord(Base):
    __tablename__ = "discussion_executions"
    __table_args__ = (
        CheckConstraint(
            "finished_at is null or finished_at >= started_at",
            "ck_discussion_executions_finished_at",
        ),
        CheckConstraint("latency_ms is null or latency_ms >= 0"),
        CheckConstraint("retry_count >= 0"),
        Index("ix_discussion_executions_task_id", "task_id"),
        Index("ix_discussion_executions_status", "status"),
        Index("ix_discussion_executions_started_at", "started_at"),
        Index("ix_discussion_executions_created_at", "created_at"),
    )

    discussion_execution_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    skill_result_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(255))
    prompt_version: Mapped[str | None] = mapped_column(String(128))
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_response: Mapped[str | None] = mapped_column(String)
    parsed_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DiscussionResultRecord(Base):
    __tablename__ = "discussion_results"
    __table_args__ = (
        CheckConstraint(
            "discussion_confidence >= 0 and discussion_confidence <= 1",
            "ck_discussion_results_confidence",
        ),
        Index("ix_discussion_results_execution_id", "discussion_execution_id"),
        Index("ix_discussion_results_task_id", "task_id"),
        Index("ix_discussion_results_created_at", "created_at"),
    )

    discussion_result_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    discussion_execution_id: Mapped[str] = mapped_column(String(64), nullable=False)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    skill_result_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    conflicts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    evidence_reviews: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )
    counter_arguments: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )
    revision_suggestions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )
    discussion_summary: Mapped[str] = mapped_column(String, nullable=False)
    discussion_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ExperimentRecord(Base):
    __tablename__ = "experiments"
    __table_args__ = (
        CheckConstraint(
            "finished_at is null or finished_at >= started_at",
            "ck_experiments_finished_at",
        ),
        Index("ix_experiments_model", "model"),
        Index("ix_experiments_prompt_version", "prompt_version"),
        Index("ix_experiments_agent_config_version", "agent_config_version"),
    )

    experiment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_config_version: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DecisionRecord(Base):
    __tablename__ = "decisions"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 and confidence <= 1", "ck_decisions_confidence"
        ),
        CheckConstraint("valid_until > created_at", "ck_decisions_valid_until"),
        Index("ix_decisions_experiment_id", "experiment_id"),
        Index("ix_decisions_symbol", "symbol"),
        Index("ix_decisions_action", "action"),
    )

    decision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    experiment_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("experiments.experiment_id", ondelete="RESTRICT"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    horizon: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    expected_return: Mapped[float] = mapped_column(Float, nullable=False)
    max_expected_loss: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    reasoning_summary: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class LLMGenerationRecordModel(Base):
    __tablename__ = "llm_generation_records"
    __table_args__ = (
        Index("ix_llm_generation_records_experiment_id", "experiment_id"),
        Index("ix_llm_generation_records_created_at", "created_at"),
    )

    decision_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("decisions.decision_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    experiment_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("experiments.experiment_id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DecisionOutcomeRecord(Base):
    __tablename__ = "decision_outcomes"
    __table_args__ = (
        UniqueConstraint("decision_id", name="uq_decision_outcomes_decision_id"),
        Index("ix_decision_outcomes_experiment_id", "experiment_id"),
        Index("ix_decision_outcomes_status", "status"),
    )

    outcome_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("decisions.decision_id", ondelete="RESTRICT"),
        nullable=False,
    )
    experiment_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("experiments.experiment_id", ondelete="RESTRICT"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    horizon: Mapped[str] = mapped_column(String(64), nullable=False)
    horizon_semantics: Mapped[str] = mapped_column(String(64), nullable=False)
    observation_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    observation_ended_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    realized_return: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 12), nullable=True
    )
    maximum_adverse_excursion: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 12), nullable=True
    )
    maximum_favorable_excursion: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 12), nullable=True
    )
    market_data_source: Mapped[str] = mapped_column(String(255), nullable=False)
    market_data_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    settled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DecisionEvaluationRecord(Base):
    __tablename__ = "decision_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "decision_id",
            "evaluation_rules_version",
            name="uq_decision_evaluations_decision_rules",
        ),
        Index("ix_decision_evaluations_outcome_id", "outcome_id"),
        Index("ix_decision_evaluations_final_result", "final_result"),
    )

    evaluation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("decisions.decision_id", ondelete="RESTRICT"),
        nullable=False,
    )
    outcome_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("decision_outcomes.outcome_id", ondelete="RESTRICT"),
        nullable=False,
    )
    experiment_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("experiments.experiment_id", ondelete="RESTRICT"),
        nullable=False,
    )
    directional_result: Mapped[str] = mapped_column(String(64), nullable=False)
    return_result: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_result: Mapped[str] = mapped_column(String(64), nullable=False)
    final_result: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluation_rules_version: Mapped[str] = mapped_column(String(128), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    explanation: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ResearchSettlementRecordModel(Base):
    __tablename__ = "research_settlement_records"
    __table_args__ = (
        UniqueConstraint("assembly_id", name="uq_research_settlements_assembly_id"),
        Index("ix_research_settlements_research_session_id", "research_session_id"),
        Index("ix_research_settlements_decision_id", "decision_id"),
    )

    research_settlement_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    assembly_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("decision_assembly_records.assembly_id", ondelete="RESTRICT"),
        nullable=False,
    )
    research_session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("research_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    debate_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("debate_records.debate_id", ondelete="RESTRICT"),
        nullable=False,
    )
    proposal_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("decision_proposals.proposal_id", ondelete="RESTRICT"),
        nullable=False,
    )
    risk_review_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("risk_reviews.risk_review_id", ondelete="RESTRICT"),
        nullable=False,
    )
    decision_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("decisions.decision_id", ondelete="RESTRICT"),
        nullable=False,
    )
    outcome_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("decision_outcomes.outcome_id", ondelete="RESTRICT"),
        nullable=False,
    )
    evaluation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("decision_evaluations.evaluation_id", ondelete="RESTRICT"),
        nullable=False,
    )
    review_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("reviews.review_id", ondelete="RESTRICT"),
        nullable=False,
    )
    learning_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    report_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    hypothesis_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    settled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ReviewRecord(Base):
    __tablename__ = "reviews"
    __table_args__ = (Index("ix_reviews_outcome", "outcome"),)

    review_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("decisions.decision_id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    actual_return: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 12), nullable=True
    )
    direction_correct: Mapped[bool | None] = mapped_column(nullable=True)
    risk_limit_breached: Mapped[bool | None] = mapped_column(nullable=True)
    outcome: Mapped[str] = mapped_column(String(64), nullable=False)
    cause_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    review_summary: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class LearningRecord(Base):
    __tablename__ = "learnings"
    __table_args__ = (
        Index("ix_learnings_learning_type", "learning_type"),
        Index("ix_learnings_approval_status", "approval_status"),
    )

    learning_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    review_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("reviews.review_id", ondelete="RESTRICT"),
        nullable=False,
    )
    learning_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    before: Mapped[Any] = mapped_column(JSONB, nullable=False)
    after: Mapped[Any] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    approval_status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class WatchlistItemRecord(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        CheckConstraint("status in ('active', 'archived')", "ck_watchlist_status"),
        CheckConstraint(
            "(status = 'active' and archived_at is null) or "
            "(status = 'archived' and archived_at is not null)",
            "ck_watchlist_archived_at",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            "ck_watchlist_updated_at",
        ),
        Index("ix_watchlist_items_status", "status"),
        Index("ix_watchlist_items_market_symbol", "market", "symbol"),
        Index(
            "uq_watchlist_active_symbol_market",
            "market",
            "symbol",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    watchlist_item_id: Mapped[str] = mapped_column("id", String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ResearchSessionRecord(Base):
    __tablename__ = "research_sessions"
    __table_args__ = (
        CheckConstraint(
            "horizon_days in (1, 3, 7)",
            "ck_research_sessions_horizon",
        ),
        CheckConstraint(
            "status in ('created', 'evidence_ready', 'cancelled')",
            "ck_research_sessions_status",
        ),
        CheckConstraint(
            "valid_until > as_of",
            "ck_research_sessions_valid_until",
        ),
        CheckConstraint(
            "(status = 'cancelled' and cancelled_at is not null) or "
            "(status <> 'cancelled' and cancelled_at is null)",
            "ck_research_sessions_cancelled_at",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            "ck_research_sessions_updated_at",
        ),
        Index("ix_research_sessions_watchlist_item_id", "watchlist_item_id"),
        Index("ix_research_sessions_symbol", "symbol"),
        Index("ix_research_sessions_market", "market"),
        Index("ix_research_sessions_status", "status"),
        Index(
            "uq_research_sessions_active_scope",
            "watchlist_item_id",
            "as_of",
            "horizon_days",
            unique=True,
            postgresql_where=text("status <> 'cancelled'"),
        ),
    )

    research_session_id: Mapped[str] = mapped_column("id", String(64), primary_key=True)
    watchlist_item_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("watchlist_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(64), nullable=False)
    watchlist_note_snapshot: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    experiment_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("experiments.experiment_id", ondelete="RESTRICT"),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    evidence_links: Mapped[list[ResearchSessionEvidenceRecord]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ResearchSessionEvidenceRecord.position",
    )


class ResearchSessionEvidenceRecord(Base):
    __tablename__ = "research_session_evidence"
    __table_args__ = (
        UniqueConstraint(
            "research_session_id",
            "position",
            name="uq_research_session_evidence_position",
        ),
    )

    research_session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    evidence_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("evidence.evidence_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    session: Mapped[ResearchSessionRecord] = relationship(
        back_populates="evidence_links"
    )


class AgentReportRecord(Base):
    __tablename__ = "agent_reports"
    __table_args__ = (
        CheckConstraint(
            "role in ('technical', 'fundamental', 'news', 'sentiment', 'capital_flow')",
            "ck_agent_reports_role",
        ),
        CheckConstraint("status in ('active', 'archived')", "ck_agent_reports_status"),
        CheckConstraint(
            "confidence >= 0 and confidence <= 1",
            "ck_agent_reports_confidence",
        ),
        CheckConstraint(
            "(status = 'active' and archived_at is null) or "
            "(status = 'archived' and archived_at is not null)",
            "ck_agent_reports_archived_at",
        ),
        CheckConstraint("updated_at >= created_at", "ck_agent_reports_updated_at"),
        Index("ix_agent_reports_research_session_id", "research_session_id"),
        Index("ix_agent_reports_role", "role"),
        Index("ix_agent_reports_status", "status"),
        Index(
            "uq_agent_reports_active_session_role",
            "research_session_id",
            "role",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    research_session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("research_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    stance: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    evidence_links: Mapped[list[AgentReportEvidenceRecord]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="AgentReportEvidenceRecord.position",
    )


class AgentReportEvidenceRecord(Base):
    __tablename__ = "agent_report_evidence"
    __table_args__ = (
        UniqueConstraint(
            "report_id",
            "position",
            name="uq_agent_report_evidence_position",
        ),
    )

    report_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_reports.report_id", ondelete="CASCADE"),
        primary_key=True,
    )
    evidence_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("evidence.evidence_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    report: Mapped[AgentReportRecord] = relationship(back_populates="evidence_links")


class HypothesisRecord(Base):
    __tablename__ = "hypotheses"
    __table_args__ = (
        CheckConstraint(
            "status in ('proposed', 'validated', 'rejected', 'invalidated')",
            "ck_hypotheses_status",
        ),
        CheckConstraint(
            "confidence >= 0 and confidence <= 1",
            "ck_hypotheses_confidence",
        ),
        CheckConstraint("horizon_days in (1, 3, 7)", "ck_hypotheses_horizon"),
        CheckConstraint("updated_at >= created_at", "ck_hypotheses_updated_at"),
        Index("ix_hypotheses_research_session_id", "research_session_id"),
        Index("ix_hypotheses_status", "status"),
    )

    hypothesis_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    research_session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("research_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    statement: Mapped[str] = mapped_column(String, nullable=False)
    rationale: Mapped[str] = mapped_column(String, nullable=False)
    direction: Mapped[str] = mapped_column(String(64), nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    report_links: Mapped[list[HypothesisReportRecord]] = relationship(
        back_populates="hypothesis",
        cascade="all, delete-orphan",
        order_by="HypothesisReportRecord.position",
    )
    evidence_links: Mapped[list[HypothesisEvidenceRecord]] = relationship(
        back_populates="hypothesis",
        cascade="all, delete-orphan",
        order_by="HypothesisEvidenceRecord.position",
    )


class HypothesisReportRecord(Base):
    __tablename__ = "hypothesis_reports"
    __table_args__ = (
        UniqueConstraint(
            "hypothesis_id",
            "position",
            name="uq_hypothesis_reports_position",
        ),
    )

    hypothesis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("hypotheses.hypothesis_id", ondelete="CASCADE"),
        primary_key=True,
    )
    report_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_reports.report_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    hypothesis: Mapped[HypothesisRecord] = relationship(back_populates="report_links")


class HypothesisEvidenceRecord(Base):
    __tablename__ = "hypothesis_evidence"
    __table_args__ = (
        UniqueConstraint(
            "hypothesis_id",
            "position",
            name="uq_hypothesis_evidence_position",
        ),
    )

    hypothesis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("hypotheses.hypothesis_id", ondelete="CASCADE"),
        primary_key=True,
    )
    evidence_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("evidence.evidence_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    hypothesis: Mapped[HypothesisRecord] = relationship(back_populates="evidence_links")


class DebateRecordModel(Base):
    __tablename__ = "debate_records"
    __table_args__ = (
        CheckConstraint(
            "status in ('open', 'assembled', 'cancelled')",
            "ck_debate_records_status",
        ),
        CheckConstraint("updated_at >= created_at", "ck_debate_records_updated_at"),
        Index("ix_debate_records_research_session_id", "research_session_id"),
    )

    debate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    research_session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("research_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    report_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    hypothesis_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    final_decision_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("decisions.decision_id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DebateStatementRecord(Base):
    __tablename__ = "debate_statements"
    __table_args__ = (
        CheckConstraint(
            "stance in ('support', 'oppose', 'neutral')",
            "ck_debate_statements_stance",
        ),
        CheckConstraint(
            "confidence_before >= 0 and confidence_before <= 1",
            "ck_debate_statements_confidence_before",
        ),
        CheckConstraint(
            "confidence_after >= 0 and confidence_after <= 1",
            "ck_debate_statements_confidence_after",
        ),
        UniqueConstraint(
            "debate_id",
            "agent_report_id",
            "hypothesis_id",
            name="uq_debate_statement_pair",
        ),
        Index("ix_debate_statements_debate_id", "debate_id"),
    )

    statement_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    debate_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("debate_records.debate_id", ondelete="RESTRICT"),
        nullable=False,
    )
    agent_report_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_reports.report_id", ondelete="RESTRICT"),
        nullable=False,
    )
    hypothesis_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("hypotheses.hypothesis_id", ondelete="RESTRICT"),
        nullable=False,
    )
    stance: Mapped[str] = mapped_column(String(32), nullable=False)
    reasoning: Mapped[str] = mapped_column(String, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    confidence_before: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_after: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DecisionProposalRecord(Base):
    __tablename__ = "decision_proposals"
    __table_args__ = (
        CheckConstraint(
            "conclusion in ('buy', 'sell', 'hold', 'watch', 'no_trade', 'invalid')",
            "ck_decision_proposals_conclusion",
        ),
        CheckConstraint(
            "confidence >= 0 and confidence <= 1",
            "ck_decision_proposals_confidence",
        ),
        UniqueConstraint("debate_id", name="uq_decision_proposals_debate_id"),
        Index("ix_decision_proposals_debate_id", "debate_id"),
    )

    proposal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    debate_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("debate_records.debate_id", ondelete="RESTRICT"),
        nullable=False,
    )
    conclusion: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    thesis: Mapped[str] = mapped_column(String, nullable=False)
    supporting_hypothesis_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    rejected_hypothesis_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    risk_notes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class RiskReviewRecord(Base):
    __tablename__ = "risk_reviews"
    __table_args__ = (
        CheckConstraint(
            "verdict in ('approve', 'downgrade', 'veto')",
            "ck_risk_reviews_verdict",
        ),
        CheckConstraint(
            "final_conclusion in "
            "('buy', 'sell', 'hold', 'watch', 'no_trade', 'invalid')",
            "ck_risk_reviews_final_conclusion",
        ),
        CheckConstraint(
            "final_confidence >= 0 and final_confidence <= 1",
            "ck_risk_reviews_final_confidence",
        ),
        UniqueConstraint("proposal_id", name="uq_risk_reviews_proposal_id"),
    )

    risk_review_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("decision_proposals.proposal_id", ondelete="RESTRICT"),
        nullable=False,
    )
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    final_conclusion: Mapped[str] = mapped_column(String(32), nullable=False)
    final_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DecisionAssemblyRecordModel(Base):
    __tablename__ = "decision_assembly_records"
    __table_args__ = (
        CheckConstraint(
            "conclusion in ('buy', 'sell', 'hold', 'watch', 'no_trade', 'invalid')",
            "ck_decision_assembly_conclusion",
        ),
        UniqueConstraint("proposal_id", name="uq_decision_assembly_proposal_id"),
        UniqueConstraint("debate_id", name="uq_decision_assembly_debate_id"),
        UniqueConstraint("decision_id", name="uq_decision_assembly_decision_id"),
    )

    assembly_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    research_session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    debate_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("debate_records.debate_id", ondelete="RESTRICT"),
        nullable=False,
    )
    proposal_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("decision_proposals.proposal_id", ondelete="RESTRICT"),
        nullable=False,
    )
    risk_review_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("risk_reviews.risk_review_id", ondelete="RESTRICT"),
        nullable=False,
    )
    decision_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("decisions.decision_id", ondelete="RESTRICT"),
        nullable=False,
    )
    conclusion: Mapped[str] = mapped_column(String(32), nullable=False)
    report_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    hypothesis_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ResearchRunRecord(Base):
    __tablename__ = "research_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('running', 'completed', 'failed')",
            "ck_research_runs_status",
        ),
        Index("ix_research_runs_watchlist_item_id", "watchlist_item_id"),
        Index("ix_research_runs_research_session_id", "research_session_id"),
        UniqueConstraint(
            "watchlist_item_id",
            "workflow",
            "input_params",
            name="uq_research_runs_idempotency",
        ),
    )

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    research_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    watchlist_item_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("watchlist_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    vibe_run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workflow: Mapped[str] = mapped_column(String(128), nullable=False)
    input_params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    raw_output_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
