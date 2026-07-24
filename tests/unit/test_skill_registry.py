from datetime import UTC, datetime, timedelta

import pytest

from aios.application.brain002 import SkillRegistry
from aios.kernel.brain002 import SkillDefinition
from aios.kernel.enums import SkillStatus
from aios.kernel.errors import DuplicateEntityError, MissingEntityError


def now() -> datetime:
    return datetime.now(UTC)


def skill_definition(
    skill_id: str,
    version: str,
    *,
    status: SkillStatus = SkillStatus.ENABLED,
    evidence_types: tuple[str, ...] = ("market_daily_bar",),
    markets: tuple[str, ...] = ("cn",),
    asset_types: tuple[str, ...] = ("stock",),
    horizons: tuple[str, ...] = ("swing",),
    dependencies: tuple[str, ...] = (),
    created_at: datetime | None = None,
) -> SkillDefinition:
    created = created_at or now()
    return SkillDefinition(
        skill_id=skill_id,
        name=skill_id.replace("_", " ").title(),
        version=version,
        description=f"{skill_id} version {version}",
        supported_markets=markets,
        supported_asset_types=asset_types,
        supported_horizons=horizons,
        required_evidence_types=evidence_types,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        dependencies=dependencies,
        status=status,
        created_at=created,
        updated_at=created,
    )


def test_registry_registers_gets_and_lists_versioned_skills() -> None:
    registry = SkillRegistry()
    skill = skill_definition("technical_trend", "1.0.0")

    registry.register(skill)

    assert registry.get("technical_trend", "1.0.0") == skill
    assert registry.get_active_version("technical_trend") == skill
    assert registry.list() == [skill]

    with pytest.raises(DuplicateEntityError):
        registry.register(skill)


def test_registry_enables_disables_and_tracks_active_version() -> None:
    registry = SkillRegistry()
    old = skill_definition("technical_trend", "1.0.0")
    new = skill_definition("technical_trend", "1.1.0")
    registry.register(old)
    registry.register(new)

    assert registry.get_active_version("technical_trend") == old

    registry.replace_version(new)
    assert registry.get_active_version("technical_trend") == new

    disabled = registry.disable("technical_trend", "1.1.0")
    assert disabled.status is SkillStatus.DISABLED
    assert registry.get_active_version("technical_trend") == old

    enabled = registry.enable("technical_trend", "1.1.0")
    assert enabled.status is SkillStatus.ENABLED


def test_registry_rolls_back_to_previous_enabled_version() -> None:
    registry = SkillRegistry()
    earlier = now() - timedelta(days=1)
    registry.register(skill_definition("policy_impact", "1.0.0", created_at=earlier))
    current = skill_definition("policy_impact", "1.1.0")
    registry.replace_version(current)

    rolled_back = registry.rollback_version("policy_impact")

    assert rolled_back.version == "1.0.0"
    assert registry.get_active_version("policy_impact") == rolled_back


def test_registry_lists_compatible_enabled_skills_with_dependencies() -> None:
    registry = SkillRegistry()
    registry.register(skill_definition("base_market_context", "1.0.0"))
    registry.register(
        skill_definition(
            "technical_trend",
            "1.0.0",
            dependencies=("base_market_context",),
        )
    )
    registry.register(
        skill_definition(
            "policy_impact",
            "1.0.0",
            evidence_types=("policy",),
        )
    )
    registry.register(
        skill_definition(
            "disabled_sentiment",
            "1.0.0",
            status=SkillStatus.DISABLED,
        )
    )

    compatible = registry.list_compatible(
        market="cn",
        asset_type="stock",
        horizon="swing",
        evidence_types=("market_daily_bar",),
    )

    assert [skill.skill_id for skill in compatible] == [
        "base_market_context",
        "technical_trend",
    ]


def test_registry_rejects_missing_versions() -> None:
    registry = SkillRegistry()

    with pytest.raises(MissingEntityError):
        registry.get("technical_trend", "1.0.0")

    with pytest.raises(MissingEntityError):
        registry.rollback_version("technical_trend")
