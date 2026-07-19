from tests.storage_contract import assert_storage_contract

from aios.storage.postgres.storage import PostgresStorage


def test_postgres_storage_contract(migrated_postgres_url: str) -> None:
    assert_storage_contract(lambda: PostgresStorage(migrated_postgres_url))
