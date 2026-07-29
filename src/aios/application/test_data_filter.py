from __future__ import annotations

from typing import Any

from aios.kernel.decision import Decision
from aios.kernel.evidence import Evidence
from aios.kernel.research_run import ResearchRun
from aios.kernel.watchlist import WatchlistItem

ACCEPTANCE_ENVIRONMENTS = {"acceptance", "smoke", "test"}
ACCEPTANCE_TAGS = {"acceptance", "smoke", "test"}


def is_marked_test_data(value: object) -> bool:
    if isinstance(value, ResearchRun):
        return (
            _symbol_is_legacy_test(value.symbol)
            or _id_is_legacy_acceptance(value.run_id)
            or _mapping_is_test(value.input_params)
        )
    if isinstance(value, WatchlistItem):
        return _symbol_is_legacy_test(value.symbol) or _id_is_legacy_acceptance(
            value.watchlist_item_id
        )
    if isinstance(value, Evidence):
        return (
            any(_symbol_is_legacy_test(symbol) for symbol in value.symbols)
            or _id_is_legacy_acceptance(value.evidence_id)
            or _mapping_is_test(value.metadata)
            or _text_is_test(value.source)
        )
    if isinstance(value, Decision):
        return _symbol_is_legacy_test(value.symbol) or _id_is_legacy_acceptance(
            value.decision_id
        )
    return _id_is_legacy_acceptance(getattr(value, "entity_id", ""))


def should_include_test_data(value: object, *, include_test_data: bool) -> bool:
    return include_test_data or not is_marked_test_data(value)


def _mapping_is_test(value: dict[str, Any]) -> bool:
    if value.get("test_run") is True:
        return True
    environment = str(value.get("environment") or "").strip().lower()
    if environment in ACCEPTANCE_ENVIRONMENTS:
        return True
    source = str(value.get("source") or "").strip().lower()
    if source in ACCEPTANCE_TAGS:
        return True
    tag = value.get("tag") or value.get("tags")
    if isinstance(tag, str):
        return tag.strip().lower() in ACCEPTANCE_TAGS
    if isinstance(tag, list | tuple | set):
        return any(str(item).strip().lower() in ACCEPTANCE_TAGS for item in tag)
    return False


def _symbol_is_legacy_test(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().upper()
    return normalized.startswith("SMOKE") or normalized.startswith("PERSIST")


def _text_is_test(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    return normalized in ACCEPTANCE_TAGS or normalized.endswith("-smoke")


def _id_is_legacy_acceptance(value: str | None) -> bool:
    if not value:
        return False
    return (
        "00000000-0000-0000-0000-000000000901" in value
        or "00000000-0000-0000-0000-000000000902" in value
    )
