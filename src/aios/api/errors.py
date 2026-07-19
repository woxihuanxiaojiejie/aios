from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

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
