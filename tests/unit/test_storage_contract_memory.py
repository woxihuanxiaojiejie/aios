from tests.storage_contract import assert_storage_contract

from aios.storage.memory import InMemoryStorage


def test_in_memory_storage_contract() -> None:
    assert_storage_contract(InMemoryStorage)
