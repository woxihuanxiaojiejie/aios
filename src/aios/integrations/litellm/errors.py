from __future__ import annotations


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
