from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

import pytest

from aios.kernel.base import KernelModel
from aios.kernel.errors import (
    DuplicateEntityError,
    MissingEntityError,
    UnsupportedEntityError,
)
from aios.kernel.evidence import Evidence
from tests.factories import fixed_now, make_evidence


class UnsupportedEntity(KernelModel):
    id_field = "unsupported_id"

    unsupported_id: str = "zz_unsupported"


def assert_storage_contract(storage_factory: Callable[[], object]) -> None:
    storage = storage_factory()
    first = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000101",
        created_at=fixed_now() + timedelta(minutes=2),
    )
    second = make_evidence(
        evidence_id="ev_00000000-0000-0000-0000-000000000100",
        created_at=fixed_now(),
    )

    assert not storage.exists(Evidence, first.evidence_id)
    storage.save(first)
    storage.save(second)

    assert storage.exists(Evidence, first.evidence_id)
    assert storage.get(Evidence, first.evidence_id) == first
    assert [item.evidence_id for item in storage.list(Evidence)] == [
        second.evidence_id,
        first.evidence_id,
    ]

    with pytest.raises(DuplicateEntityError):
        storage.save(first)

    with pytest.raises(MissingEntityError):
        storage.get(Evidence, "ev_missing")

    with pytest.raises(UnsupportedEntityError, match="UnsupportedEntity"):
        storage.exists(UnsupportedEntity, "zz_unsupported")

    with pytest.raises(UnsupportedEntityError, match="UnsupportedEntity"):
        storage.save(UnsupportedEntity())
