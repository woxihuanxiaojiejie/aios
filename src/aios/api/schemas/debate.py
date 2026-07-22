from __future__ import annotations

from datetime import datetime

from pydantic import Field

from aios.api.schemas.common import ApiSchema
from aios.kernel.debate import (
    DebateRecord,
    DebateStatement,
    DecisionAssemblyRecord,
    DecisionProposal,
    RiskReview,
)
from aios.kernel.enums import (
    DebateStance,
    DebateStatus,
    ResearchConclusion,
    RiskVerdict,
)


class DebateResponse(ApiSchema):
    debate_id: str
    research_session_id: str
    report_ids: list[str]
    hypothesis_ids: list[str]
    status: DebateStatus
    final_decision_id: str | None
    created_at: datetime
    updated_at: datetime


class DebateStatementCreateRequest(ApiSchema):
    agent_report_id: str = Field(min_length=1)
    hypothesis_id: str = Field(min_length=1)
    stance: DebateStance
    reasoning: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    confidence_before: float = Field(ge=0, le=1)
    confidence_after: float = Field(ge=0, le=1)


class DebateStatementResponse(ApiSchema):
    statement_id: str
    debate_id: str
    agent_report_id: str
    hypothesis_id: str
    stance: DebateStance
    reasoning: str
    evidence_ids: list[str]
    confidence_before: float
    confidence_after: float
    created_at: datetime


class DecisionProposalCreateRequest(ApiSchema):
    conclusion: ResearchConclusion
    confidence: float = Field(ge=0, le=1)
    thesis: str = Field(min_length=1)
    supporting_hypothesis_ids: list[str] = Field(default_factory=list)
    rejected_hypothesis_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)


class DecisionProposalResponse(ApiSchema):
    proposal_id: str
    debate_id: str
    conclusion: ResearchConclusion
    confidence: float
    thesis: str
    supporting_hypothesis_ids: list[str]
    rejected_hypothesis_ids: list[str]
    evidence_ids: list[str]
    risk_notes: list[str]
    created_at: datetime


class RiskReviewCreateRequest(ApiSchema):
    verdict: RiskVerdict
    final_conclusion: ResearchConclusion
    final_confidence: float = Field(ge=0, le=1)
    reasons: list[str] = Field(min_length=1)


class RiskReviewResponse(ApiSchema):
    risk_review_id: str
    proposal_id: str
    verdict: RiskVerdict
    final_conclusion: ResearchConclusion
    final_confidence: float
    reasons: list[str]
    created_at: datetime


class DecisionAssemblyResponse(ApiSchema):
    assembly_id: str
    research_session_id: str
    debate_id: str
    proposal_id: str
    risk_review_id: str
    decision_id: str
    conclusion: ResearchConclusion
    report_ids: list[str]
    hypothesis_ids: list[str]
    evidence_ids: list[str]
    created_at: datetime


def debate_response(debate: DebateRecord) -> DebateResponse:
    return DebateResponse(
        debate_id=debate.debate_id,
        research_session_id=debate.research_session_id,
        report_ids=list(debate.report_ids),
        hypothesis_ids=list(debate.hypothesis_ids),
        status=debate.status,
        final_decision_id=debate.final_decision_id,
        created_at=debate.created_at,
        updated_at=debate.updated_at,
    )


def debate_statement_response(statement: DebateStatement) -> DebateStatementResponse:
    return DebateStatementResponse(
        statement_id=statement.statement_id,
        debate_id=statement.debate_id,
        agent_report_id=statement.agent_report_id,
        hypothesis_id=statement.hypothesis_id,
        stance=statement.stance,
        reasoning=statement.reasoning,
        evidence_ids=list(statement.evidence_ids),
        confidence_before=statement.confidence_before,
        confidence_after=statement.confidence_after,
        created_at=statement.created_at,
    )


def decision_proposal_response(proposal: DecisionProposal) -> DecisionProposalResponse:
    return DecisionProposalResponse(
        proposal_id=proposal.proposal_id,
        debate_id=proposal.debate_id,
        conclusion=proposal.conclusion,
        confidence=proposal.confidence,
        thesis=proposal.thesis,
        supporting_hypothesis_ids=list(proposal.supporting_hypothesis_ids),
        rejected_hypothesis_ids=list(proposal.rejected_hypothesis_ids),
        evidence_ids=list(proposal.evidence_ids),
        risk_notes=list(proposal.risk_notes),
        created_at=proposal.created_at,
    )


def risk_review_response(review: RiskReview) -> RiskReviewResponse:
    return RiskReviewResponse(
        risk_review_id=review.risk_review_id,
        proposal_id=review.proposal_id,
        verdict=review.verdict,
        final_conclusion=review.final_conclusion,
        final_confidence=review.final_confidence,
        reasons=list(review.reasons),
        created_at=review.created_at,
    )


def decision_assembly_response(
    assembly: DecisionAssemblyRecord,
) -> DecisionAssemblyResponse:
    return DecisionAssemblyResponse(
        assembly_id=assembly.assembly_id,
        research_session_id=assembly.research_session_id,
        debate_id=assembly.debate_id,
        proposal_id=assembly.proposal_id,
        risk_review_id=assembly.risk_review_id,
        decision_id=assembly.decision_id,
        conclusion=assembly.conclusion,
        report_ids=list(assembly.report_ids),
        hypothesis_ids=list(assembly.hypothesis_ids),
        evidence_ids=list(assembly.evidence_ids),
        created_at=assembly.created_at,
    )
