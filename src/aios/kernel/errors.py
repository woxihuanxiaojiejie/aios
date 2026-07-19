class AiosError(Exception):
    """Base exception for AIOS kernel errors."""


class DuplicateEntityError(AiosError):
    """Raised when storage would overwrite an existing entity."""


class MissingEntityError(AiosError):
    """Raised when an entity cannot be found."""


class ReferenceIntegrityError(AiosError):
    """Raised when a lifecycle object references a missing entity."""
