from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

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

DEFAULT_BASE_URLS = {
    "deepseek": "https://api.deepseek.com/beta",
    "openai": "https://api.openai.com/v1",
}

PROVIDER_API_KEY_ENV = {
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
}

PROVIDER_API_BASE_ENV = {
    "deepseek": "DEEPSEEK_API_BASE",
    "openai": "OPENAI_API_BASE",
}


@dataclass(frozen=True)
class LLMRuntimeConfig:
    provider: str
    model: str
    api_key: str
    api_base: str


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
        runtime_config = (
            None
            if self._completion_func is not None
            else validate_llm_runtime_config(model, os.environ)
        )
        started = time.perf_counter()
        response = self._complete_with_provider_response_format(
            completion_func=completion_func,
            provider=provider,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=response_schema,
            temperature=temperature,
            api_key=runtime_config.api_key if runtime_config else None,
            api_base=runtime_config.api_base if runtime_config else None,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        usage = _usage(response)
        raw_response = _message_content(response)
        parsed, extracted_payload = self._parse_response(
            response=response,
            response_schema=response_schema,
            raw_response=raw_response,
            provider=provider,
            model=str(getattr(response, "model", model) or model),
            usage=usage,
            latency_ms=latency_ms,
        )
        return LLMStructuredResult(
            parsed=parsed,
            provider=provider,
            model=str(getattr(response, "model", model) or model),
            request_id=_optional_str(getattr(response, "id", None)),
            raw_response=raw_response if isinstance(raw_response, str) else None,
            extracted_payload=extracted_payload,
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
        api_key: str | None,
        api_base: str | None,
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
                    api_key=api_key,
                    api_base=api_base,
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
        *,
        response: Any,
        response_schema: type[BaseModel],
        raw_response: Any,
        provider: str,
        model: str,
        usage: dict[str, Any],
        latency_ms: int,
    ) -> tuple[BaseModel, dict[str, Any]]:
        content = raw_response
        if not isinstance(content, str):
            msg = "LLM response did not contain text content"
            raise LLMStructuredOutputError(
                msg,
                raw_response=None,
                provider=provider,
                model=model,
                prompt_tokens=_optional_int(usage.get("prompt_tokens")),
                completion_tokens=_optional_int(usage.get("completion_tokens")),
                total_tokens=_optional_int(usage.get("total_tokens")),
                latency_ms=latency_ms,
                finish_reason=_finish_reason(response),
            )
        try:
            payload = _extract_json_object(content)
            return response_schema.model_validate(payload), payload
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            msg = "LLM response failed structured output validation"
            validation_error = (
                exc.errors() if isinstance(exc, ValidationError) else str(exc)
            )
            raise LLMStructuredOutputError(
                msg,
                raw_response=content,
                extracted_payload=payload if "payload" in locals() else None,
                validation_error=validation_error,
                provider=provider,
                model=model,
                prompt_tokens=_optional_int(usage.get("prompt_tokens")),
                completion_tokens=_optional_int(usage.get("completion_tokens")),
                total_tokens=_optional_int(usage.get("total_tokens")),
                latency_ms=latency_ms,
                finish_reason=_finish_reason(response),
            ) from exc


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


def _extract_json_object(content: str) -> dict[str, Any]:
    text = _strip_json_code_fence(content.strip())
    decoder = json.JSONDecoder()
    starts = [index for index in (text.find("{"), text.find("[")) if index >= 0]
    if not starts:
        msg = "LLM response did not contain a JSON object"
        raise ValueError(msg)
    parsed, _ = decoder.raw_decode(text[min(starts) :])
    if isinstance(parsed, dict):
        wrapped = _unwrap_common_payload(parsed)
        if isinstance(wrapped, dict):
            return wrapped
    msg = "LLM response JSON root must be an object"
    raise ValueError(msg)


def _strip_json_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _unwrap_common_payload(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("payload", "result", "output"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    arguments = payload.get("arguments")
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return payload
        if isinstance(parsed, dict):
            return parsed
    return payload


def validate_llm_runtime_config(
    model: str,
    environ: Mapping[str, str],
) -> LLMRuntimeConfig:
    if not model.strip():
        msg = "AIOS_EXTERNAL_LLM_MODEL must be set for real LLM calls"
        raise LLMConfigurationError(msg)
    provider = _provider(model)
    if provider == "unknown" or not model.split("/", maxsplit=1)[1].strip():
        msg = "AIOS_EXTERNAL_LLM_MODEL must use a provider-prefixed model"
        raise LLMConfigurationError(msg)
    if provider not in PROVIDER_API_KEY_ENV:
        supported = ", ".join(sorted(PROVIDER_API_KEY_ENV))
        msg = f"unsupported LLM provider {provider}; supported providers: {supported}"
        raise LLMConfigurationError(msg)

    api_key_env = PROVIDER_API_KEY_ENV[provider]
    api_key = environ.get(api_key_env, "").strip()
    if not api_key:
        msg = f"{api_key_env} must be set for {provider} model {model}"
        raise LLMConfigurationError(msg)

    api_base_env = PROVIDER_API_BASE_ENV[provider]
    api_base = environ.get(api_base_env, DEFAULT_BASE_URLS[provider]).strip()
    if not _valid_url(api_base):
        msg = f"{api_base_env} must be an absolute http(s) URL"
        raise LLMConfigurationError(msg)

    return LLMRuntimeConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        api_base=api_base,
    )


def _valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


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
