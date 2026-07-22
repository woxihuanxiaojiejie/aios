from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from aios.integrations.evidence import Evidence

DuplicateType = Literal[
    "same_source_identifier",
    "source_identifier_revision",
    "exact_duplicate_candidate",
]


class ExactDuplicateResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    duplicate_type: DuplicateType | None
    matched_evidence_id: UUID | None
    matched_fingerprint: str | None
    rule_name: str | None
    is_duplicate_candidate: bool
    preserve_candidate: bool = True


def check_exact_duplicate(
    candidate: Evidence,
    existing: list[Evidence] | tuple[Evidence, ...],
) -> ExactDuplicateResult:
    for evidence in existing:
        if _same_source_identifier(candidate, evidence):
            if candidate.fingerprint == evidence.fingerprint:
                return _result(
                    "same_source_identifier",
                    evidence,
                    "same_source_same_identifier",
                    is_duplicate_candidate=True,
                )
            return _result(
                "source_identifier_revision",
                evidence,
                "same_source_same_identifier_changed_fingerprint",
                is_duplicate_candidate=False,
            )

    for evidence in existing:
        if candidate.fingerprint != evidence.fingerprint:
            continue
        if candidate.source == evidence.source:
            return _result(
                "exact_duplicate_candidate",
                evidence,
                "same_source_different_identifier_same_fingerprint",
                is_duplicate_candidate=True,
            )
        return _result(
            "exact_duplicate_candidate",
            evidence,
            "different_source_same_fingerprint",
            is_duplicate_candidate=True,
        )

    return ExactDuplicateResult(
        duplicate_type=None,
        matched_evidence_id=None,
        matched_fingerprint=None,
        rule_name=None,
        is_duplicate_candidate=False,
    )


def _same_source_identifier(candidate: Evidence, existing: Evidence) -> bool:
    return (
        candidate.source == existing.source
        and candidate.source_identifier is not None
        and candidate.source_identifier == existing.source_identifier
    )


def _result(
    duplicate_type: DuplicateType,
    matched: Evidence,
    rule_name: str,
    *,
    is_duplicate_candidate: bool,
) -> ExactDuplicateResult:
    return ExactDuplicateResult(
        duplicate_type=duplicate_type,
        matched_evidence_id=matched.evidence_id,
        matched_fingerprint=matched.fingerprint,
        rule_name=rule_name,
        is_duplicate_candidate=is_duplicate_candidate,
    )
