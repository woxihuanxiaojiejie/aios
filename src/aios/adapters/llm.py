from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict


class LLMStructuredResult(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    parsed: BaseModel
    provider: str
    model: str
    request_id: str | None = None
    raw_response: str | None = None
    extracted_payload: dict[str, Any] | None = None
    validation_error: Any | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int
    raw_finish_reason: str | None = None


class LLMAdapter(Protocol):
    def generate_structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        temperature: float,
    ) -> LLMStructuredResult:
        """Generate a locally validated structured response."""
