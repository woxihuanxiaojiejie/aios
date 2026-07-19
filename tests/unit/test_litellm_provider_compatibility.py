from __future__ import annotations

from typing import Any

from tests.unit.test_litellm_adapter import (
    Choice,
    Message,
    Response,
    completion_success,
)

from aios.integrations.litellm.adapter import LiteLLMAdapter
from aios.integrations.litellm.errors import LLMConfigurationError
from aios.integrations.litellm.schemas import DecisionDraft


def test_openai_uses_json_schema_structured_output() -> None:
    calls: list[dict[str, Any]] = []

    def completion(**kwargs: Any) -> Response:
        calls.append(kwargs)
        return completion_success()

    LiteLLMAdapter(completion).generate_structured(
        model="openai/gpt-4.1-mini",
        system_prompt="system",
        user_prompt="user",
        response_schema=DecisionDraft,
        temperature=0,
    )

    assert calls[0]["response_format"]["type"] == "json_schema"
    assert calls[0]["response_format"]["json_schema"]["name"] == "DecisionDraft"


def test_deepseek_starts_with_json_object_response_format() -> None:
    calls: list[dict[str, Any]] = []

    def completion(**kwargs: Any) -> Response:
        calls.append(kwargs)
        return completion_success()

    LiteLLMAdapter(completion).generate_structured(
        model="deepseek/deepseek-chat",
        system_prompt="system",
        user_prompt="user",
        response_schema=DecisionDraft,
        temperature=0,
    )

    assert calls[0]["response_format"] == {"type": "json_object"}


def test_deepseek_retries_without_response_format_when_json_object_is_rejected() -> (
    None
):
    calls: list[dict[str, Any]] = []

    def completion(**kwargs: Any) -> Response:
        calls.append(kwargs)
        if len(calls) == 1:
            raise RuntimeError("provider rejected response_format")
        return Response(
            choices=[
                Choice(
                    Message(
                        content=(
                            '{"action":"hold","confidence":0.5,'
                            '"expected_return":0,"max_expected_loss":0.01,'
                            '"horizon":"1d","reasoning_summary":"valid json",'
                            '"supporting_evidence_ids":["ev_1"],'
                            '"risk_factors":[],"invalidation_conditions":[]}'
                        )
                    )
                )
            ]
        )

    class Adapter(LiteLLMAdapter):
        def _map_exception(self, exc: Exception) -> Exception:
            return LLMConfigurationError("format rejected")

    result = Adapter(completion).generate_structured(
        model="deepseek/deepseek-chat",
        system_prompt="system",
        user_prompt="user",
        response_schema=DecisionDraft,
        temperature=0,
    )

    assert calls[0]["response_format"] == {"type": "json_object"}
    assert "response_format" not in calls[1]
    assert "JSON object" in calls[1]["messages"][0]["content"]
    assert isinstance(result.parsed, DecisionDraft)
