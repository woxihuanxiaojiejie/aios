class AiosError(Exception):
    """Base exception for AIOS kernel errors."""


class DuplicateEntityError(AiosError):
    """Raised when storage would overwrite an existing entity."""


class MissingEntityError(AiosError):
    """Raised when an entity cannot be found."""


class ReferenceIntegrityError(AiosError):
    """Raised when a lifecycle object references a missing entity."""


class UnsupportedEntityError(AiosError):
    """Raised when a storage adapter does not support an entity type."""


class DatabaseConfigurationError(AiosError):
    """Raised when database configuration is missing or invalid."""


class StorageOperationError(AiosError):
    """Raised when a storage operation fails without leaking adapter errors."""


class InvalidStateTransitionError(AiosError):
    """Raised when a controlled state transition is not allowed."""
