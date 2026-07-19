from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.prompts.versions import DECISION_V1

EVIDENCE_LIMIT = 50
MAX_EVIDENCE_CHARS = 50_000


@dataclass(frozen=True)
class DecisionPrompt:
    version: str
    system_prompt: str
    user_prompt: str
    evidence_snapshot_hash: str


def build_decision_prompt(
    *,
    experiment: Experiment,
    evidence: list[Evidence],
    symbol: str,
    horizon: str,
    user_constraints: str | None = None,
) -> DecisionPrompt:
    evidence_json = serialize_evidence(evidence)
    constraints = user_constraints or "None"
    system_prompt = (
        "You generate one structured AIOS DecisionDraft. "
        "You must only use the provided Evidence. "
        "Do not invent news, filings, prices, financial data, or evidence IDs. "
        "If evidence is insufficient, choose hold or no_trade. "
        "supporting_evidence_ids must come from the input Evidence and confidence "
        "does not mean the decision is guaranteed correct. max_expected_loss is "
        "required and reasoning_summary must not include hidden chain-of-thought."
    )
    user_prompt = json.dumps(
        {
            "prompt_version": DECISION_V1,
            "experiment": {
                "experiment_id": experiment.experiment_id,
                "name": experiment.name,
                "model": experiment.model,
                "prompt_version": experiment.prompt_version,
                "agent_config_version": experiment.agent_config_version,
                "dataset_snapshot": experiment.dataset_snapshot,
            },
            "request": {
                "symbol": symbol,
                "horizon": horizon,
                "horizon_semantics": "natural_time",
                "user_constraints": constraints,
            },
            "evidence": json.loads(evidence_json),
            "output_schema": {
                "action": "buy | sell | hold | observe | no_trade",
                "confidence": "number between 0 and 1",
                "expected_return": "number",
                "max_expected_loss": "non-negative number",
                "horizon": horizon,
                "reasoning_summary": "brief audit summary, no hidden reasoning",
                "supporting_evidence_ids": "non-empty subset of input evidence IDs",
                "risk_factors": "string array",
                "invalidation_conditions": "string array",
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return DecisionPrompt(
        version=DECISION_V1,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        evidence_snapshot_hash=evidence_snapshot_hash(evidence),
    )


def serialize_evidence(evidence: list[Evidence]) -> str:
    if len(evidence) > EVIDENCE_LIMIT:
        msg = f"at most {EVIDENCE_LIMIT} Evidence items can be serialized"
        raise ValueError(msg)
    ordered = sorted(evidence, key=lambda item: (item.published_at, item.evidence_id))
    payload = [_evidence_payload(item) for item in ordered]
    text = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )
    if len(text) > MAX_EVIDENCE_CHARS:
        msg = f"serialized Evidence exceeds {MAX_EVIDENCE_CHARS} characters"
        raise ValueError(msg)
    return text


def evidence_snapshot_hash(evidence: list[Evidence]) -> str:
    return hashlib.sha256(serialize_evidence(evidence).encode("utf-8")).hexdigest()


def prompt_hash(prompt: DecisionPrompt) -> str:
    payload = json.dumps(
        {
            "version": prompt.version,
            "system_prompt": prompt.system_prompt,
            "user_prompt": prompt.user_prompt,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _evidence_payload(evidence: Evidence) -> dict[str, Any]:
    metadata = {
        key: value
        for key, value in evidence.metadata.items()
        if key in {"provider", "market_bar", "adjustment", "source_function", "form"}
    }
    return {
        "evidence_id": evidence.evidence_id,
        "evidence_type": evidence.evidence_type,
        "source": evidence.source,
        "symbols": list(evidence.symbols),
        "published_at": evidence.published_at,
        "available_at": evidence.available_at,
        "summary": evidence.summary,
        "reliability": evidence.reliability,
        "metadata": metadata,
    }


def _json_default(value: object) -> str:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)
