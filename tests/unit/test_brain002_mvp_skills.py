from datetime import UTC, datetime, timedelta

from aios.application.brain002 import SkillInput
from aios.kernel.brain002 import SkillResultPayload
from aios.kernel.evidence import Evidence
from aios.skills.brain002 import TechnicalTrendSkill


def now() -> datetime:
    return datetime.now(UTC)


def evidence(evidence_id: str, evidence_type: str, summary: str) -> Evidence:
    available_at = now()
    return Evidence(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        source="brain001",
        symbols=("000001",),
        published_at=available_at - timedelta(minutes=1),
        available_at=available_at,
        summary=summary,
        reliability=0.9,
        content_hash=f"hash-{evidence_id}",
    )


def skill_input() -> SkillInput:
    return SkillInput(
        task_id="at_example",
        symbol="000001",
        market="cn",
        asset_type="stock",
        analysis_horizon="swing",
        as_of=now(),
        evidence=(
            evidence("ev_price", "market_daily_bar", "Close above 20 day average."),
        ),
        market_context={"benchmark": "CSI300"},
        user_constraints={"language": "en"},
        skill_context={},
    )


def test_technical_trend_skill_definition_and_prompt_are_isolated() -> None:
    skill = TechnicalTrendSkill()

    prompt = skill.build_prompt(skill_input())

    assert skill.definition.skill_id == "technical_trend"
    assert skill.definition.required_evidence_types == ("market_daily_bar",)
    assert skill.response_schema is SkillResultPayload
    assert skill.prompt_version == "technical_trend_v1"
    assert "price trend" in prompt.system_prompt
    assert "moving averages" in prompt.system_prompt
    assert "Do not analyze policy" in prompt.system_prompt
    assert "Do not make final trading decisions" in prompt.system_prompt
    assert "ev_price" in prompt.user_prompt
    assert "Close above 20 day average." in prompt.user_prompt
