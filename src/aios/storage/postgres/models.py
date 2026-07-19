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
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
