from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from aios.integrations.litellm.adapter import (
    LiteLLMAdapter,
    validate_llm_runtime_config,
)
from aios.integrations.litellm.errors import (
    LLMConfigurationError,
    LLMStructuredOutputError,
)
from aios.integrations.litellm.schemas import DecisionDraft


@dataclass
class Message:
    content: str


@dataclass
class Choice:
    message: Message
    finish_reason: str = "stop"


@dataclass
class Usage:
    prompt_tokens: int = 10
    completion_tokens: int = 5
    total_tokens: int = 15


@dataclass
class Response:
    choices: list[Choice]
    model: str = "fake/model"
    id: str = "req_1"
    usage: Usage = field(default_factory=Usage)


def completion_success(**_kwargs: object) -> Response:
    return Response(
        choices=[
            Choice(
                Message(
                    content=(
                        '{"action":"hold","confidence":0.5,"expected_return":0,'
                        '"max_expected_loss":0.01,"horizon":"1d",'
                        '"reasoning_summary":"hold based on provided evidence",'
                        '"supporting_evidence_ids":["ev_1"],'
                        '"risk_factors":[],"invalidation_conditions":[]}'
                    )
                )
            )
        ]
    )


def test_litellm_adapter_parses_structured_response() -> None:
    result = LiteLLMAdapter(completion_success).generate_structured(
        model="fake/model",
        system_prompt="system",
        user_prompt="user",
        response_schema=DecisionDraft,
        temperature=0,
    )

    assert isinstance(result.parsed, DecisionDraft)
    assert result.provider == "fake"
    assert result.prompt_tokens == 10
    assert result.raw_finish_reason == "stop"


def test_litellm_adapter_rejects_invalid_json() -> None:
    def completion_bad_json(**_kwargs: object) -> Response:
        return Response(choices=[Choice(Message(content="not-json"))])

    with pytest.raises(LLMStructuredOutputError):
        LiteLLMAdapter(completion_bad_json).generate_structured(
            model="fake/model",
            system_prompt="system",
            user_prompt="user",
            response_schema=DecisionDraft,
            temperature=0,
        )


def test_litellm_adapter_missing_sdk_maps_to_configuration_error() -> None:
    def completion_failure(**_kwargs: object) -> Response:
        raise RuntimeError("provider details with secret")

    with pytest.raises(LLMConfigurationError):
        LiteLLMAdapter(completion_failure).generate_structured(
            model="fake/model",
            system_prompt="system",
            user_prompt="user",
            response_schema=DecisionDraft,
            temperature=0,
        )


def test_runtime_config_requires_model() -> None:
    with pytest.raises(LLMConfigurationError, match="AIOS_EXTERNAL_LLM_MODEL"):
        validate_llm_runtime_config("", {})


def test_runtime_config_requires_provider_key() -> None:
    with pytest.raises(LLMConfigurationError, match="DEEPSEEK_API_KEY"):
        validate_llm_runtime_config("deepseek/deepseek-chat", {})


def test_runtime_config_rejects_mismatched_provider_key() -> None:
    with pytest.raises(LLMConfigurationError, match="DEEPSEEK_API_KEY"):
        validate_llm_runtime_config(
            "deepseek/deepseek-chat",
            {"OPENAI_API_KEY": "openai-test-token"},
        )


def test_runtime_config_rejects_invalid_base_url() -> None:
    with pytest.raises(LLMConfigurationError, match="DEEPSEEK_API_BASE"):
        validate_llm_runtime_config(
            "deepseek/deepseek-chat",
            {
                "DEEPSEEK_API_KEY": "deepseek-test-token",
                "DEEPSEEK_API_BASE": "not-a-url",
            },
        )


def test_runtime_config_returns_provider_specific_credentials() -> None:
    config = validate_llm_runtime_config(
        "deepseek/deepseek-chat",
        {"DEEPSEEK_API_KEY": "deepseek-test-token"},
    )

    assert config.provider == "deepseek"
    assert config.model == "deepseek/deepseek-chat"
    assert config.api_key == "deepseek-test-token"
    assert config.api_base == "https://api.deepseek.com/beta"
