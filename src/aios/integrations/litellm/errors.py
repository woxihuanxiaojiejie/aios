from __future__ import annotations

from typing import Any


class LLMError(Exception):
    """Base error for LLM integration failures."""


class LLMConfigurationError(LLMError):
    """Raised when model/provider configuration is missing or invalid."""


class LLMAuthenticationError(LLMError):
    """Raised when a provider rejects authentication."""


class LLMRateLimitError(LLMError):
    """Raised when a provider rate limit is hit."""


class LLMTimeoutError(LLMError):
    """Raised when a provider request times out."""


class LLMUpstreamError(LLMError):
    """Raised for non-classified provider failures."""


class LLMStructuredOutputError(LLMError):
    """Raised when provider output cannot be validated against the schema."""

    def __init__(
        self,
        message: str,
        *,
        raw_response: str | None = None,
        extracted_payload: dict[str, Any] | None = None,
        validation_error: Any | None = None,
        provider: str | None = None,
        model: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        latency_ms: int | None = None,
        finish_reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.raw_response = raw_response
        self.extracted_payload = extracted_payload
        self.validation_error = validation_error
        self.provider = provider
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.latency_ms = latency_ms
        self.finish_reason = finish_reason
