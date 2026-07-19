from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from aios.adapters.llm import LLMStructuredResult
from aios.integrations.litellm.schemas import DecisionDraft
from aios.kernel.enums import Action


class FakeLLMAdapter:
    def __init__(
        self,
        *,
        draft: DecisionDraft | None = None,
        error: Exception | None = None,
    ) -> None:
        self.draft = draft
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def generate_structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        temperature: float,
    ) -> LLMStructuredResult:
        self.calls.append(
            {
                "model": model,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_schema": response_schema,
                "temperature": temperature,
            }
        )
        if self.error is not None:
            raise self.error
        evidence_id = _first_evidence_id(user_prompt)
        parsed = self.draft or DecisionDraft(
            action=Action.HOLD,
            confidence=0.62,
            expected_return=0.008,
            max_expected_loss=0.015,
            horizon="1d",
            reasoning_summary="Provided evidence supports a cautious hold.",
            supporting_evidence_ids=[evidence_id],
            risk_factors=["single evidence source"],
            invalidation_conditions=["new contradictory evidence"],
        )
        return LLMStructuredResult(
            parsed=parsed,
            provider="fake",
            model=model,
            request_id="llm_fake_request",
            prompt_tokens=100,
            completion_tokens=30,
            total_tokens=130,
            latency_ms=12,
            raw_finish_reason="stop",
        )


@dataclass
class CapturingGenerationRecorder:
    records: list[Any]

    def save_generation_record(self, record: Any) -> None:
        self.records.append(record)


def _first_evidence_id(user_prompt: str) -> str:
    payload = json.loads(user_prompt)
    return str(payload["evidence"][0]["evidence_id"])
