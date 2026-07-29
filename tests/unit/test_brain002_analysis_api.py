from __future__ import annotations

import json
from datetime import timedelta

from fastapi.testclient import TestClient
from pydantic import BaseModel
from tests.api_helpers import evidence_payload, now

from aios.adapters.llm import LLMStructuredResult
from aios.api.app import create_app
from aios.kernel.brain002 import SkillResultPayload
from aios.kernel.enums import SkillDirection
from aios.storage.memory import InMemoryStorage


class SkillLLMAdapter:
    def generate_structured(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel],
        temperature: float,
    ) -> LLMStructuredResult:
        evidence_id = str(json.loads(user_prompt)["evidence"][0]["evidence_id"])
        return LLMStructuredResult(
            parsed=SkillResultPayload(
                conclusion="Independent skill analysis completed.",
                direction=SkillDirection.NEUTRAL,
                confidence=0.55,
                supporting_evidence_ids=(evidence_id,),
                risk_factors=("single evidence source",),
                invalid_conditions=("new contradictory evidence",),
                missing_information=("more market context",),
                reasoning_summary="The evidence is enough for a neutral analysis.",
            ),
            provider="fake",
            model=model,
            request_id="skill_fake_request",
            prompt_tokens=20,
            completion_tokens=10,
            total_tokens=30,
            latency_ms=5,
            raw_finish_reason="stop",
        )


def client() -> TestClient:
    return TestClient(
        create_app(storage=InMemoryStorage(), llm_adapter=SkillLLMAdapter())
    )


def test_brain002_analysis_api_creates_and_gets_task() -> None:
    api = client()
    evidence = api.post(
        "/api/v1/evidence",
        json=evidence_payload(
            evidence_type="market_daily_bar",
            available_at=(now() + timedelta(minutes=1)).isoformat(),
        ),
    ).json()

    response = api.post(
        "/api/v1/brain/analysis/tasks",
        json={
            "symbol": "NVDA",
            "market": "us",
            "asset_type": "stock",
            "horizon": "swing",
            "as_of": (now() + timedelta(minutes=2)).isoformat(),
            "evidence_ids": [evidence["evidence_id"]],
            "requested_skill_ids": ["technical_trend"],
        },
    )

    assert response.status_code == 201
    task_id = response.json()["task_id"]
    assert task_id.startswith("at_")
    fetched = api.get(f"/api/v1/brain/analysis/tasks/{task_id}").json()
    assert fetched["task_id"] == task_id


def test_brain002_analysis_api_lists_and_toggles_skills() -> None:
    api = client()

    skills = api.get("/api/v1/brain/analysis/skills").json()["items"]
    assert {item["skill_id"] for item in skills} >= {
        "technical_trend",
        "sector_strength",
        "policy_impact",
        "announcement_risk",
        "market_sentiment",
    }

    disabled = api.post(
        "/api/v1/brain/analysis/skills/technical_trend/disable",
        params={"version": "1.0.0"},
    )
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"

    enabled = api.post(
        "/api/v1/brain/analysis/skills/technical_trend/enable",
        params={"version": "1.0.0"},
    )
    assert enabled.json()["status"] == "enabled"


def test_brain002_analysis_api_executes_task_and_lists_results() -> None:
    api = client()
    evidence = api.post(
        "/api/v1/evidence",
        json=evidence_payload(
            evidence_type="market_daily_bar",
            available_at=(now() + timedelta(minutes=1)).isoformat(),
        ),
    ).json()
    task = api.post(
        "/api/v1/brain/analysis/tasks",
        json={
            "symbol": "NVDA",
            "market": "us",
            "asset_type": "stock",
            "horizon": "swing",
            "as_of": (now() + timedelta(minutes=2)).isoformat(),
            "evidence_ids": [evidence["evidence_id"]],
            "requested_skill_ids": ["technical_trend"],
        },
    ).json()

    executed = api.post(
        f"/api/v1/brain/analysis/tasks/{task['task_id']}/execute",
        json={"model": "fake/model"},
    )

    assert executed.status_code == 200
    assert executed.json()["results"][0]["skill_id"] == "technical_trend"
    assert executed.json()["executions"][0]["provider"] == "fake"
    results = api.get(
        "/api/v1/brain/analysis/results",
        params={"task_id": task["task_id"]},
    ).json()
    assert results["items"][0]["supporting_evidence_ids"] == [evidence["evidence_id"]]


def test_brain002_analysis_api_lists_failed_records() -> None:
    api = client()

    failures = api.get("/api/v1/brain/analysis/failures").json()

    assert failures["items"] == []
