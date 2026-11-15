"""Uniform JSON error responses: ``{"error": {"code": ..., "message": ..., "details": ...}}``."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from piscope_engine.errors import (
    DatasetIntegrityError,
    DatasetNotFoundError,
    InvalidPatternError,
    PiScopeError,
    PositionOutOfRangeError,
)

logger = logging.getLogger(__name__)


class DatasetUnavailableError(Exception):
    """The API is running but has no usable dataset."""


class RequestLimitError(Exception):
    """A request is well formed but exceeds a configured computational limit."""


def _body(code: str, message: str, details: object | None = None) -> dict[str, object]:
    error: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


def register_error_handlers(app: FastAPI) -> None:
    """Attach handlers that turn engine and validation errors into JSON responses."""

    @app.exception_handler(DatasetUnavailableError)
    def dataset_unavailable(_: Request, exc: DatasetUnavailableError) -> JSONResponse:
        return JSONResponse(status_code=503, content=_body("dataset_unavailable", str(exc)))

    @app.exception_handler(DatasetNotFoundError)
    @app.exception_handler(DatasetIntegrityError)
    def dataset_broken(_: Request, exc: PiScopeError) -> JSONResponse:
        return JSONResponse(status_code=503, content=_body("dataset_unavailable", str(exc)))

    @app.exception_handler(PositionOutOfRangeError)
    def out_of_range(_: Request, exc: PositionOutOfRangeError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_body("position_out_of_range", str(exc)))

    @app.exception_handler(InvalidPatternError)
    def invalid_pattern(_: Request, exc: InvalidPatternError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_body("invalid_pattern", str(exc)))

    @app.exception_handler(RequestLimitError)
    def limit_exceeded(_: Request, exc: RequestLimitError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_body("limit_exceeded", str(exc)))

    @app.exception_handler(ValidationError)
    def response_model_invalid(_: Request, exc: ValidationError) -> JSONResponse:
        # Raised while building a response, so it is a server bug, not bad input.
        # Registered separately because pydantic's ValidationError is a ValueError.
        logger.error("response model validation failed: %s", exc)
        return JSONResponse(
            status_code=500, content=_body("internal_error", "unexpected server error")
        )

    @app.exception_handler(ValueError)
    def invalid_value(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_body("invalid_request", str(exc)))

    @app.exception_handler(RequestValidationError)
    def validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(part) for part in error["loc"][1:]), "message": error["msg"]}
            for error in exc.errors()
        ]
        message = "; ".join(f"{d['field']}: {d['message']}" for d in details) or "invalid request"
        return JSONResponse(status_code=422, content=_body("validation_error", message, details))

    @app.exception_handler(Exception)
    def unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500, content=_body("internal_error", "unexpected server error")
        )
