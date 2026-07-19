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
        provider = _provider(model)
        started = time.perf_counter()
        response = self._complete_with_provider_response_format(
            completion_func=completion_func,
            provider=provider,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=response_schema,
            temperature=temperature,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        parsed = self._parse_response(response, response_schema)
        usage = _usage(response)
        return LLMStructuredResult(
            parsed=parsed,
            provider=provider,
            model=str(getattr(response, "model", model) or model),
            request_id=_optional_str(getattr(response, "id", None)),
            prompt_tokens=_optional_int(usage.get("prompt_tokens")),
            completion_tokens=_optional_int(usage.get("completion_tokens")),
            total_tokens=_optional_int(usage.get("total_tokens")),
            latency_ms=latency_ms,
            raw_finish_reason=_finish_reason(response),
        )

    def _complete_with_provider_response_format(
        self,
        *,
        completion_func: Callable[..., Any],
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        temperature: float,
    ) -> Any:
        attempts = self._response_format_attempts(provider, response_schema)
        for index, response_format in enumerate(attempts):
            try:
                return completion_func(
                    model=model,
                    messages=_messages(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        require_json=response_format is None,
                    ),
                    temperature=temperature,
                    **_response_format_kwargs(response_format),
                )
            except Exception as exc:
                mapped = self._map_exception(exc)
                can_retry_without_format = (
                    provider == "deepseek"
                    and isinstance(mapped, LLMConfigurationError)
                    and response_format is not None
                    and index + 1 < len(attempts)
                )
                if can_retry_without_format:
                    continue
                raise mapped from exc
        msg = "LLM request could not be completed"
        raise LLMUpstreamError(msg)

    def _json_schema_response_format(
        self,
        response_schema: type[BaseModel],
    ) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": response_schema.__name__,
                "schema": response_schema.model_json_schema(),
                "strict": True,
            },
        }

    def _deepseek_response_format(self) -> dict[str, str]:
        return {"type": "json_object"}

    def _response_format_attempts(
        self,
        provider: str,
        response_schema: type[BaseModel],
    ) -> tuple[dict[str, Any] | None, ...]:
        if provider == "deepseek":
            return (self._deepseek_response_format(), None)
        return (self._json_schema_response_format(response_schema),)

    def _completion(self, **kwargs: Any) -> Any:
        from litellm import completion

        return completion(**kwargs)

    def _map_exception(self, exc: Exception) -> Exception:
        try:
            import litellm
        except ImportError:
            return LLMConfigurationError("LiteLLM is not installed")

        if isinstance(exc, _litellm_error(litellm, "AuthenticationError")):
            return LLMAuthenticationError("LLM authentication failed")
        if isinstance(exc, _litellm_error(litellm, "RateLimitError")):
            return LLMRateLimitError("LLM rate limit exceeded")
        if isinstance(exc, _litellm_error(litellm, "Timeout")):
            return LLMTimeoutError("LLM request timed out")
        if isinstance(exc, _litellm_error(litellm, "BadRequestError")):
            return LLMConfigurationError("LLM request configuration is invalid")
        if isinstance(exc, _litellm_error(litellm, "APIConnectionError")):
            return LLMUpstreamError("LLM upstream connection failed")
        if isinstance(exc, _litellm_error(litellm, "APIError")):
            return LLMUpstreamError("LLM upstream request failed")
        if isinstance(exc, RuntimeError):
            return LLMConfigurationError("LLM request configuration is invalid")
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


def _messages(
    *,
    system_prompt: str,
    user_prompt: str,
    require_json: bool,
) -> list[dict[str, str]]:
    if require_json:
        system_prompt = (
            f"{system_prompt}\n"
            "Return only a JSON object matching the requested schema. "
            "Do not wrap it in Markdown."
        )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _response_format_kwargs(response_format: dict[str, Any] | None) -> dict[str, Any]:
    return {} if response_format is None else {"response_format": response_format}


def _litellm_error(module: Any, name: str) -> type[Exception] | tuple[()]:
    value = getattr(module, name, None)
    if isinstance(value, type) and issubclass(value, Exception):
        return value
    return ()


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
