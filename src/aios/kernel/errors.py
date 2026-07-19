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


class DecisionNotFoundError(MissingEntityError):
    """Raised when a Decision cannot be found for settlement."""


class ExperimentNotFoundError(MissingEntityError):
    """Raised when a Decision references a missing Experiment."""


class DecisionNotReadyForSettlementError(InvalidStateTransitionError):
    """Raised when a Decision horizon has not ended yet."""


class OutcomeAlreadySettledError(DuplicateEntityError):
    """Raised when a Decision already has a settlement outcome."""


class InsufficientMarketDataError(AiosError):
    """Raised when market data cannot support settlement."""


class EvaluationConfigurationError(AiosError):
    """Raised when deterministic evaluation rules cannot be applied."""


class SettlementReviewMappingError(AiosError):
    """Raised when settlement details cannot be mapped to a Review."""


class ReviewConsistencyError(AiosError):
    """Raised when an existing Review conflicts with settlement details."""
