import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class ServiceUnavailableError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="service_unavailable",
            message=message,
            status_code=503,
            details=details,
        )


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
                "details": details,
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(HTTPException, _handle_http_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)


async def _handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    app_error = _require_type(exc, AppError)
    if app_error.status_code >= 500:
        logger.error(
            "Application error",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "path": request.url.path,
                "status_code": app_error.status_code,
                "error_code": app_error.code,
                "error_details": app_error.details or {},
            },
        )
    return error_response(
        request,
        status_code=app_error.status_code,
        code=app_error.code,
        message=app_error.message,
        details=app_error.details,
    )


async def _handle_http_error(request: Request, exc: Exception) -> JSONResponse:
    http_error = _require_type(exc, HTTPException)
    if http_error.status_code >= 500:
        logger.error(
            "HTTP error",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "path": request.url.path,
                "status_code": http_error.status_code,
            },
        )
    return error_response(
        request,
        status_code=http_error.status_code,
        code="http_error",
        message=str(http_error.detail),
    )


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    validation_error = _require_type(exc, RequestValidationError)
    details = []
    for error in validation_error.errors():
        sanitized_error = dict(error)
        sanitized_error.pop("ctx", None)
        sanitized_error.pop("input", None)
        details.append(sanitized_error)
    return error_response(
        request,
        status_code=422,
        code="validation_error",
        message="Request validation failed",
        details=details,
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled application error",
        exc_info=exc,
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "method": request.method,
            "path": request.url.path,
            "status_code": 500,
        },
    )
    return error_response(
        request,
        status_code=500,
        code="internal_server_error",
        message="An unexpected error occurred",
    )


def _require_type[T: Exception](exc: Exception, expected: type[T]) -> T:
    if not isinstance(exc, expected):
        raise TypeError(f"Expected {expected.__name__}, received {type(exc).__name__}")
    return exc
