from __future__ import annotations

from datetime import timedelta

import pytest
from tests.factories import fixed_now, make_evidence, make_experiment

from aios.prompts.decision_v1 import (
    EVIDENCE_LIMIT,
    MAX_EVIDENCE_CHARS,
    build_decision_prompt,
    evidence_snapshot_hash,
    prompt_hash,
    serialize_evidence,
)
from aios.prompts.versions import DECISION_V1


def test_decision_prompt_has_version_and_evidence_ids() -> None:
    evidence = make_evidence()
    experiment = make_experiment(evidence.evidence_id, prompt_version=DECISION_V1)

    prompt = build_decision_prompt(
        experiment=experiment,
        evidence=[evidence],
        symbol="NVDA",
        horizon="1d",
    )

    assert prompt.version == DECISION_V1
    assert evidence.evidence_id in prompt.user_prompt
    assert "only use the provided Evidence" in prompt.system_prompt


def test_serialize_evidence_stable_sort_and_time_format() -> None:
    later = make_evidence(
        evidence_id="ev_later",
        created_at=fixed_now() + timedelta(minutes=1),
    )
    earlier = make_evidence(evidence_id="ev_earlier")
    later = later.model_copy(update={"published_at": fixed_now() + timedelta(days=1)})

    text = serialize_evidence([later, earlier])

    assert text.index("ev_earlier") < text.index("ev_later")
    assert "+00:00" in text
    assert "metadata_json" not in text
    assert "_sa_instance_state" not in text


def test_evidence_snapshot_hash_changes_when_content_changes() -> None:
    evidence = make_evidence()
    changed = evidence.model_copy(update={"summary": "changed summary"})

    assert evidence_snapshot_hash([evidence]) != evidence_snapshot_hash([changed])


def test_prompt_hash_is_stable() -> None:
    evidence = make_evidence()
    experiment = make_experiment(evidence.evidence_id, prompt_version=DECISION_V1)

    first = build_decision_prompt(
        experiment=experiment,
        evidence=[evidence],
        symbol="NVDA",
        horizon="1d",
    )
    second = build_decision_prompt(
        experiment=experiment,
        evidence=[evidence],
        symbol="NVDA",
        horizon="1d",
    )

    assert prompt_hash(first) == prompt_hash(second)


def test_evidence_limits_are_explicit() -> None:
    evidence = [
        make_evidence(evidence_id=f"ev_{index:032d}")
        for index in range(EVIDENCE_LIMIT + 1)
    ]

    with pytest.raises(ValueError):
        serialize_evidence(evidence)


def test_evidence_character_limit_is_explicit() -> None:
    evidence = make_evidence(summary="x" * (MAX_EVIDENCE_CHARS + 1))

    with pytest.raises(ValueError):
        serialize_evidence([evidence])
