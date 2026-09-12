"""Standardized error responses and global exception handlers for FloodPath API."""
import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("floodpath.errors")


class AppException(Exception):
    """Base application exception with machine-readable error codes."""

    def __init__(
        self,
        message: str,
        error_code: str = "BAD_REQUEST",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or []


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", error_code: str = "RESOURCE_NOT_FOUND", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, error_code=error_code, status_code=status.HTTP_404_NOT_FOUND, details=details)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Permission denied", error_code: str = "FORBIDDEN", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, error_code=error_code, status_code=status.HTTP_403_FORBIDDEN, details=details)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Authentication required", error_code: str = "UNAUTHORIZED", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, error_code=error_code, status_code=status.HTTP_401_UNAUTHORIZED, details=details)


class ConflictError(AppException):
    def __init__(self, message: str = "Resource conflict", error_code: str = "CONFLICT", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, error_code=error_code, status_code=status.HTTP_409_CONFLICT, details=details)


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", error_code: str = "VALIDATION_ERROR", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, error_code=error_code, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, details=details)


class DEMUnavailableError(AppException):
    def __init__(self, message: str = "DEM data is unavailable for this region", details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message=message, error_code="DEM_DATA_UNAVAILABLE", status_code=status.HTTP_400_BAD_REQUEST, details=details)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    payload: Dict[str, Any] = {
        "error_code": exc.error_code,
        "message": exc.message,
    }
    if exc.details:
        payload["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=payload)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details: List[Dict[str, Any]] = []
    for error in exc.errors():
        field_loc = ".".join(str(loc) for loc in error.get("loc", []) if loc != "body")
        details.append({
            "field": field_loc if field_loc else None,
            "message": error.get("msg", "Invalid input"),
        })

    payload = {
        "error_code": "VALIDATION_ERROR",
        "message": "Invalid request payload or parameters",
        "details": details,
    }
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    error_code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        error_code = "UNAUTHORIZED"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        error_code = "FORBIDDEN"
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        error_code = "NOT_FOUND"

    payload = {
        "error_code": error_code,
        "message": str(exc.detail),
        "detail": str(exc.detail),
    }
    headers = getattr(exc, "headers", None)
    return JSONResponse(status_code=exc.status_code, content=payload, headers=headers)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled server exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    payload = {
        "error_code": "INTERNAL_SERVER_ERROR",
        "message": "An unexpected internal error occurred. Please try again later.",
    }
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all standard exception handlers on the FastAPI application."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
