from datetime import UTC, datetime, timedelta

from aios.application.brain002 import SkillRegistry, SkillSelector
from aios.kernel.brain002 import AnalysisTask, SkillDefinition
from aios.kernel.enums import SkillStatus
from aios.kernel.evidence import Evidence


def now() -> datetime:
    return datetime.now(UTC)


def evidence(
    evidence_id: str,
    evidence_type: str,
    *,
    available_at: datetime,
    metadata: dict[str, object] | None = None,
) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        source="brain001",
        symbols=("000001",),
        published_at=available_at - timedelta(minutes=1),
        available_at=available_at,
        summary=f"{evidence_type} summary",
        reliability=0.9,
        content_hash=f"hash-{evidence_id}",
        metadata=metadata or {},
    )


def skill_definition(
    skill_id: str,
    *,
    evidence_types: tuple[str, ...],
    status: SkillStatus = SkillStatus.ENABLED,
    dependencies: tuple[str, ...] = (),
    trigger_conditions: dict[str, object] | None = None,
) -> SkillDefinition:
    return SkillDefinition(
        skill_id=skill_id,
        name=skill_id.replace("_", " ").title(),
        version="1.0.0",
        description=f"{skill_id} analysis",
        supported_markets=("cn",),
        supported_asset_types=("stock",),
        supported_horizons=("swing",),
        required_evidence_types=evidence_types,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        trigger_conditions=trigger_conditions or {},
        dependencies=dependencies,
        status=status,
    )


def task(
    *,
    as_of: datetime,
    evidence_ids: tuple[str, ...],
    requested_skill_ids: tuple[str, ...] = (),
) -> AnalysisTask:
    return AnalysisTask(
        symbol="000001",
        market="cn",
        asset_type="stock",
        horizon="swing",
        as_of=as_of,
        evidence_ids=evidence_ids,
        requested_skill_ids=requested_skill_ids,
    )


def test_selector_uses_requested_skill_ids_as_deterministic_filter() -> None:
    registry = SkillRegistry()
    registry.register(skill_definition("technical_trend", evidence_types=("price",)))
    registry.register(skill_definition("market_sentiment", evidence_types=("price",)))
    as_of = now()
    selection = SkillSelector(registry).select(
        task=task(
            as_of=as_of,
            evidence_ids=("ev_price",),
            requested_skill_ids=("technical_trend",),
        ),
        evidence=(evidence("ev_price", "price", available_at=as_of),),
    )

    assert selection.selected_skill_ids == ("technical_trend",)
    assert selection.rejected_skill_ids == ("market_sentiment",)
    assert selection.selection_reason["technical_trend"] == "selected"
    assert selection.selection_reason["market_sentiment"] == "not_requested"


def test_selector_filters_out_evidence_after_task_as_of() -> None:
    registry = SkillRegistry()
    registry.register(skill_definition("technical_trend", evidence_types=("price",)))
    registry.register(skill_definition("policy_impact", evidence_types=("policy",)))
    as_of = now()
    selection = SkillSelector(registry).select(
        task=task(as_of=as_of, evidence_ids=("ev_price", "ev_future_policy")),
        evidence=(
            evidence("ev_price", "price", available_at=as_of),
            evidence(
                "ev_future_policy",
                "policy",
                available_at=as_of + timedelta(seconds=1),
            ),
        ),
    )

    assert selection.selected_skill_ids == ("technical_trend",)
    assert selection.selection_reason["policy_impact"] == "missing_evidence_type"
    assert selection.matched_conditions["point_in_time_evidence_ids"] == ("ev_price",)


def test_selector_rejects_skill_when_dependency_is_not_active() -> None:
    registry = SkillRegistry()
    registry.register(
        skill_definition(
            "technical_trend",
            evidence_types=("price",),
            dependencies=("base_market_context",),
        )
    )
    as_of = now()

    selection = SkillSelector(registry).select(
        task=task(as_of=as_of, evidence_ids=("ev_price",)),
        evidence=(evidence("ev_price", "price", available_at=as_of),),
    )

    assert selection.selected_skill_ids == ()
    assert selection.selection_reason["technical_trend"] == "missing_dependency"


def test_selector_matches_metadata_trigger_conditions() -> None:
    registry = SkillRegistry()
    registry.register(
        skill_definition(
            "policy_impact",
            evidence_types=("policy",),
            trigger_conditions={"metadata_equals": {"policy_level": "national"}},
        )
    )
    registry.register(
        skill_definition(
            "local_policy_impact",
            evidence_types=("policy",),
            trigger_conditions={"metadata_equals": {"policy_level": "local"}},
        )
    )
    as_of = now()

    selection = SkillSelector(registry).select(
        task=task(as_of=as_of, evidence_ids=("ev_policy",)),
        evidence=(
            evidence(
                "ev_policy",
                "policy",
                available_at=as_of,
                metadata={"policy_level": "national"},
            ),
        ),
    )

    assert selection.selected_skill_ids == ("policy_impact",)
    assert selection.selection_reason["local_policy_impact"] == "trigger_not_matched"
    assert selection.matched_conditions["policy_impact"] == (
        "market",
        "asset_type",
        "horizon",
        "evidence_type",
        "trigger_conditions",
    )
