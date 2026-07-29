from __future__ import annotations

from datetime import datetime

from pydantic import Field

from aios.api.schemas.common import ApiSchema
from aios.kernel.enums import (
    AgentReportStatus,
    AgentRole,
    HypothesisStatus,
)
from aios.kernel.research_records import AgentReport, Hypothesis


class AgentReportCreateRequest(ApiSchema):
    role: AgentRole
    summary: str = Field(min_length=1)
    stance: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)
    source: str = Field(min_length=1)
    raw_reference: str | None = Field(default=None, max_length=500)


class AgentReportResponse(ApiSchema):
    report_id: str
    research_session_id: str
    role: AgentRole
    summary: str
    stance: str
    confidence: float
    evidence_ids: list[str]
    source: str
    raw_reference: str | None
    status: AgentReportStatus
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class HypothesisCreateRequest(ApiSchema):
    statement: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    direction: str = Field(min_length=1)
    horizon_days: int
    confidence: float = Field(ge=0, le=1)
    supporting_report_ids: list[str] = Field(min_length=1)
    supporting_evidence_ids: list[str] = Field(default_factory=list)


class HypothesisStatusUpdateRequest(ApiSchema):
    status: HypothesisStatus


class HypothesisResponse(ApiSchema):
    hypothesis_id: str
    research_session_id: str
    statement: str
    rationale: str
    direction: str
    horizon_days: int
    confidence: float
    supporting_report_ids: list[str]
    supporting_evidence_ids: list[str]
    status: HypothesisStatus
    created_at: datetime
    updated_at: datetime


def agent_report_response(report: AgentReport) -> AgentReportResponse:
    return AgentReportResponse(
        report_id=report.report_id,
        research_session_id=report.research_session_id,
        role=report.role,
        summary=report.summary,
        stance=report.stance,
        confidence=report.confidence,
        evidence_ids=list(report.evidence_ids),
        source=report.source,
        raw_reference=report.raw_reference,
        status=report.status,
        archived_at=report.archived_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def hypothesis_response(hypothesis: Hypothesis) -> HypothesisResponse:
    return HypothesisResponse(
        hypothesis_id=hypothesis.hypothesis_id,
        research_session_id=hypothesis.research_session_id,
        statement=hypothesis.statement,
        rationale=hypothesis.rationale,
        direction=hypothesis.direction,
        horizon_days=hypothesis.horizon_days,
        confidence=hypothesis.confidence,
        supporting_report_ids=list(hypothesis.supporting_report_ids),
        supporting_evidence_ids=list(hypothesis.supporting_evidence_ids),
        status=hypothesis.status,
        created_at=hypothesis.created_at,
        updated_at=hypothesis.updated_at,
    )
