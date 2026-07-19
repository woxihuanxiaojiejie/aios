from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from aios.adapters.market_errors import (
    EmptyMarketDataError,
    InvalidMarketDataError,
    MarketDataDateRangeError,
    MissingMarketDataFieldError,
    UnsupportedAdjustmentError,
    UnsupportedMarketSymbolError,
    UpstreamMarketDataError,
)
from aios.application.decision_generation import (
    DecisionEvidenceValidationError,
    UnsupportedPromptVersionError,
)
from aios.integrations.litellm.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMRateLimitError,
    LLMStructuredOutputError,
    LLMTimeoutError,
    LLMUpstreamError,
)
from aios.kernel.errors import (
    DatabaseConfigurationError,
    DuplicateEntityError,
    InvalidStateTransitionError,
    MissingEntityError,
    ReferenceIntegrityError,
    StorageOperationError,
    UnsupportedEntityError,
)


class DomainValidationError(Exception):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


def error_body(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def validation_details(errors: Sequence[Any]) -> dict[str, Any]:
    safe_errors: list[dict[str, Any]] = []
    for error in errors:
        safe_error = dict(error)
        if "ctx" in safe_error:
            safe_error["ctx"] = {
                key: str(value) for key, value in dict(safe_error["ctx"]).items()
            }
        safe_errors.append(safe_error)
    return {"errors": jsonable_encoder(safe_errors)}


def request_validation_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_body(
            "request_validation_error",
            "Request validation failed",
            validation_details(exc.errors()),
        ),
    )


def validation_handler(_request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_body(
            "validation_failed",
            "Domain validation failed",
            validation_details(exc.errors()),
        ),
    )


def domain_validation_handler(
    _request: Request,
    exc: DomainValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_body("validation_failed", str(exc), exc.details),
    )


def missing_entity_handler(
    _request: Request,
    exc: MissingEntityError,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_body("entity_not_found", str(exc)),
    )


def reference_handler(
    _request: Request,
    exc: ReferenceIntegrityError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_body("reference_integrity_error", str(exc)),
    )


def duplicate_handler(_request: Request, exc: DuplicateEntityError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=error_body("entity_conflict", str(exc)),
    )


def state_handler(
    _request: Request,
    exc: InvalidStateTransitionError,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=error_body("invalid_state_transition", str(exc)),
    )


def unsupported_handler(
    _request: Request,
    exc: UnsupportedEntityError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_body("unsupported_entity", str(exc)),
    )


def database_config_handler(
    _request: Request,
    exc: DatabaseConfigurationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_body("database_configuration_error", str(exc)),
    )


def storage_handler(_request: Request, _exc: StorageOperationError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_body("storage_operation_error", "Storage operation failed"),
    )


def unsupported_market_symbol_handler(
    _request: Request,
    exc: UnsupportedMarketSymbolError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_body("market_data_unsupported_symbol", str(exc)),
    )


def unsupported_adjustment_handler(
    _request: Request,
    exc: UnsupportedAdjustmentError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_body("market_data_unsupported_adjustment", str(exc)),
    )


def market_data_date_range_handler(
    _request: Request,
    exc: MarketDataDateRangeError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_body("market_data_date_range_error", str(exc)),
    )


def market_data_bad_request_handler(
    _request: Request,
    exc: InvalidMarketDataError | MissingMarketDataFieldError | ValueError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_body("market_data_invalid", str(exc)),
    )


def empty_market_data_handler(
    _request: Request,
    exc: EmptyMarketDataError,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=error_body("market_data_empty", str(exc)),
    )


def upstream_market_data_handler(
    _request: Request,
    _exc: UpstreamMarketDataError,
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content=error_body("market_data_upstream_error", "Upstream market data failed"),
    )


def decision_generation_validation_handler(
    _request: Request,
    exc: DecisionEvidenceValidationError | UnsupportedPromptVersionError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_body("decision_generation_validation_error", str(exc)),
    )


def llm_service_unavailable_handler(
    _request: Request,
    _exc: LLMConfigurationError | LLMAuthenticationError | LLMRateLimitError,
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=error_body("llm_unavailable", "LLM provider is unavailable"),
    )


def llm_timeout_handler(_request: Request, _exc: LLMTimeoutError) -> JSONResponse:
    return JSONResponse(
        status_code=504,
        content=error_body("llm_timeout", "LLM request timed out"),
    )


def llm_bad_gateway_handler(
    _request: Request,
    _exc: LLMUpstreamError | LLMStructuredOutputError,
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content=error_body("llm_upstream_error", "LLM generation failed"),
    )


def add_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        RequestValidationError,
        cast("Any", request_validation_handler),
    )
    app.add_exception_handler(ValidationError, cast("Any", validation_handler))
    app.add_exception_handler(
        DomainValidationError,
        cast("Any", domain_validation_handler),
    )
    app.add_exception_handler(MissingEntityError, cast("Any", missing_entity_handler))
    app.add_exception_handler(ReferenceIntegrityError, cast("Any", reference_handler))
    app.add_exception_handler(DuplicateEntityError, cast("Any", duplicate_handler))
    app.add_exception_handler(
        InvalidStateTransitionError,
        cast("Any", state_handler),
    )
    app.add_exception_handler(UnsupportedEntityError, cast("Any", unsupported_handler))
    app.add_exception_handler(
        DatabaseConfigurationError,
        cast("Any", database_config_handler),
    )
    app.add_exception_handler(StorageOperationError, cast("Any", storage_handler))
    app.add_exception_handler(
        UnsupportedMarketSymbolError,
        cast("Any", unsupported_market_symbol_handler),
    )
    app.add_exception_handler(
        UnsupportedAdjustmentError,
        cast("Any", unsupported_adjustment_handler),
    )
    app.add_exception_handler(
        MarketDataDateRangeError,
        cast("Any", market_data_date_range_handler),
    )
    for market_error_type in (
        InvalidMarketDataError,
        MissingMarketDataFieldError,
        ValueError,
    ):
        app.add_exception_handler(
            market_error_type,
            cast("Any", market_data_bad_request_handler),
        )
    app.add_exception_handler(
        EmptyMarketDataError,
        cast("Any", empty_market_data_handler),
    )
    app.add_exception_handler(
        UpstreamMarketDataError,
        cast("Any", upstream_market_data_handler),
    )
    for decision_generation_error_type in (
        DecisionEvidenceValidationError,
        UnsupportedPromptVersionError,
    ):
        app.add_exception_handler(
            decision_generation_error_type,
            cast("Any", decision_generation_validation_handler),
        )
    for llm_unavailable_error_type in (
        LLMConfigurationError,
        LLMAuthenticationError,
        LLMRateLimitError,
    ):
        app.add_exception_handler(
            llm_unavailable_error_type,
            cast("Any", llm_service_unavailable_handler),
        )
    app.add_exception_handler(LLMTimeoutError, cast("Any", llm_timeout_handler))
    for llm_gateway_error_type in (LLMUpstreamError, LLMStructuredOutputError):
        app.add_exception_handler(
            llm_gateway_error_type,
            cast("Any", llm_bad_gateway_handler),
        )
