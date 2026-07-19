from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from aios.adapters.llm import LLMStructuredResult
from aios.integrations.litellm.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMRateLimitError,
    LLMStructuredOutputError,
    LLMTimeoutError,
    LLMUpstreamError,
)


class LiteLLMAdapter:
    def __init__(self, completion_func: Callable[..., Any] | None = None) -> None:
        self._completion_func = completion_func

    def generate_structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        temperature: float,
    ) -> LLMStructuredResult:
        completion_func = self._completion_func or self._completion
        started = time.perf_counter()
        try:
            response = completion_func(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_schema.__name__,
                        "schema": response_schema.model_json_schema(),
                        "strict": True,
                    },
                },
            )
        except Exception as exc:
            raise self._map_exception(exc) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)
        parsed = self._parse_response(response, response_schema)
        usage = _usage(response)
        return LLMStructuredResult(
            parsed=parsed,
            provider=_provider(model),
            model=str(getattr(response, "model", model) or model),
            request_id=_optional_str(getattr(response, "id", None)),
            prompt_tokens=_optional_int(usage.get("prompt_tokens")),
            completion_tokens=_optional_int(usage.get("completion_tokens")),
            total_tokens=_optional_int(usage.get("total_tokens")),
            latency_ms=latency_ms,
            raw_finish_reason=_finish_reason(response),
        )

    def _completion(self, **kwargs: Any) -> Any:
        from litellm import completion  # type: ignore[import-not-found]

        return completion(**kwargs)

    def _map_exception(self, exc: Exception) -> Exception:
        try:
            import litellm
        except ImportError:
            return LLMConfigurationError("LiteLLM is not installed")

        if isinstance(exc, litellm.AuthenticationError):
            return LLMAuthenticationError("LLM authentication failed")
        if isinstance(exc, litellm.RateLimitError):
            return LLMRateLimitError("LLM rate limit exceeded")
        if isinstance(exc, litellm.Timeout):
            return LLMTimeoutError("LLM request timed out")
        if isinstance(exc, litellm.BadRequestError):
            return LLMConfigurationError("LLM request configuration is invalid")
        if isinstance(exc, litellm.APIConnectionError):
            return LLMUpstreamError("LLM upstream connection failed")
        if isinstance(exc, litellm.APIError):
            return LLMUpstreamError("LLM upstream request failed")
        return LLMUpstreamError("LLM upstream request failed")

    def _parse_response(
        self,
        response: Any,
        response_schema: type[BaseModel],
    ) -> BaseModel:
        content = _message_content(response)
        if not isinstance(content, str):
            msg = "LLM response did not contain text content"
            raise LLMStructuredOutputError(msg)
        try:
            payload = json.loads(content)
            return response_schema.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            msg = "LLM response failed structured output validation"
            raise LLMStructuredOutputError(msg) from exc


def _message_content(response: Any) -> Any:
    choice = response.choices[0]
    message = choice.message
    return message.get("content") if isinstance(message, dict) else message.content


def _finish_reason(response: Any) -> str | None:
    choice = response.choices[0]
    return _optional_str(getattr(choice, "finish_reason", None))


def _usage(response: Any) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    if isinstance(usage, dict):
        return usage
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def _provider(model: str) -> str:
    return model.split("/", maxsplit=1)[0] if "/" in model else "unknown"


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
