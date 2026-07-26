from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy.exc import IntegrityError

from aios.adapters.storage import Storage
from aios.integrations.evidence import Evidence as BrainEvidence
from aios.kernel.errors import StorageOperationError
from aios.kernel.evidence import Evidence


class CoreEvidenceBridge:
    """Compatibility bridge from legacy BRAIN-001 Evidence to core Evidence."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def ensure_core_evidence(
        self,
        evidence: BrainEvidence,
        *,
        default_symbol: str,
    ) -> Evidence:
        legacy_id = str(evidence.evidence_id)
        existing = self.find_by_legacy_brain_evidence_id(legacy_id)
        if existing is not None:
            return existing

        core = self.build_core_evidence(evidence, default_symbol=default_symbol)
        try:
            self._storage.save(core)
            return core
        except (IntegrityError, StorageOperationError):
            existing = self.find_by_legacy_brain_evidence_id(legacy_id)
            if existing is not None:
                return existing
            raise

    def build_core_evidence(
        self,
        evidence: BrainEvidence,
        *,
        default_symbol: str,
    ) -> Evidence:
        evidence_type = self._evidence_type(evidence)
        published_at = evidence.published_at or evidence.collected_at
        raw_response = evidence.provider_record.model_dump(mode="json")
        metadata = {
            **evidence.metadata,
            "legacy_source": "brain_evidence",
            "raw_artifact_path": str(evidence.raw_artifact_path),
            "provider_record": raw_response,
        }
        return Evidence(
            evidence_type=evidence_type,
            source=evidence.source,
            symbols=self._symbols(evidence, default_symbol),
            published_at=published_at,
            available_at=evidence.available_at,
            summary=evidence.summary or evidence.content[:500],
            reliability=self._reliability(evidence_type),
            content_hash=self._content_hash(evidence),
            metadata=metadata,
            title=evidence.title,
            raw_content=evidence.content,
            raw_response=raw_response,
            source_type=evidence.source_type,
            source_identifier=evidence.source_identifier,
            source_url=evidence.source_url,
            collected_at=evidence.collected_at,
            entities=self._entities(evidence, default_symbol),
            fingerprint=evidence.fingerprint,
            credibility=self._reliability(evidence_type),
            freshness=self._freshness(evidence),
            processing_status="parsed",
            parse_error=None,
            legacy_brain_evidence_id=str(evidence.evidence_id),
            created_at=evidence.collected_at,
        )

    def find_by_legacy_brain_evidence_id(
        self,
        legacy_brain_evidence_id: str,
    ) -> Evidence | None:
        for evidence in self._storage.list(Evidence):
            if evidence.legacy_brain_evidence_id == legacy_brain_evidence_id:
                return evidence
        return None

    def _evidence_type(self, evidence: BrainEvidence) -> str:
        if evidence.metadata.get("source_domain") == "policy":
            return "policy"
        if evidence.source_type == "announcement":
            return "company_announcement"
        if evidence.source_type in {"rss", "webpage"}:
            return "news"
        return evidence.source_type

    def _symbols(self, evidence: BrainEvidence, default_symbol: str) -> tuple[str, ...]:
        raw_symbols = _string_values(evidence.metadata.get("symbols")) or (
            default_symbol,
        )
        symbols = tuple(str(symbol).strip().upper() for symbol in raw_symbols)
        return tuple(symbol for symbol in symbols if symbol) or (
            default_symbol.strip().upper(),
        )

    def _entities(
        self,
        evidence: BrainEvidence,
        default_symbol: str,
    ) -> dict[str, Any]:
        return {
            "symbols": list(self._symbols(evidence, default_symbol)),
            "markets": list(_string_values(evidence.metadata.get("markets"))),
            "sectors": list(_string_values(evidence.metadata.get("sectors"))),
            "themes": list(_string_values(evidence.metadata.get("themes"))),
        }

    def _content_hash(self, evidence: BrainEvidence) -> str:
        return hashlib.sha256(
            f"brain001:{evidence.evidence_id}:{evidence.fingerprint}".encode()
        ).hexdigest()

    def _reliability(self, evidence_type: str) -> float:
        return 0.9 if evidence_type == "policy" else 0.8

    def _freshness(self, evidence: BrainEvidence) -> str | None:
        value = evidence.metadata.get("freshness")
        return str(value) if value is not None else None


def _string_values(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list | tuple | set):
        return tuple(str(item) for item in value)
    return (str(value),)
