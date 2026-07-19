import pytest
from sqlalchemy.exc import SQLAlchemyError
from tests.factories import make_evidence

from aios.kernel.errors import DatabaseConfigurationError, StorageOperationError
from aios.storage.postgres.database import get_database_url
from aios.storage.postgres.storage import PostgresStorage


class FailingSession:
    def get(self, entity_type: type[object], entity_id: str) -> None:
        return None

    def add(self, entity: object) -> None:
        return None

    def commit(self) -> None:
        raise SQLAlchemyError("database failed")

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


def test_database_config_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIOS_DATABASE_URL", raising=False)

    with pytest.raises(DatabaseConfigurationError, match="AIOS_DATABASE_URL"):
        get_database_url()


def test_database_exception_converts_to_domain_error() -> None:
    storage = PostgresStorage(session_factory=FailingSession)

    with pytest.raises(StorageOperationError, match="Evidence"):
        storage.save(make_evidence())
