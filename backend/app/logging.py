"""Structured JSON logging with request ID tracking."""
import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return request_id_ctx_var.get()


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }

        # Include any extra attributes attached to the record
        for key in ("scenario_id", "run_id", "stage", "duration_ms", "status_code"):
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(level: str = "INFO") -> None:
    """Configures structured JSON logging on the root logger."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(stream_handler)


class RequestIdLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a traceable request ID and logs request lifecycle."""

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx_var.set(req_id)
        start_time = time.perf_counter()

        logger = logging.getLogger("floodpath.api")
        logger.info(
            f"Started {request.method} {request.url.path}",
            extra={"path": request.url.path, "method": request.method},
        )

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = req_id
            logger.info(
                f"Completed {request.method} {request.url.path} with status {response.status_code} in {duration_ms}ms",
                extra={
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "path": request.url.path,
                },
            )
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Failed {request.method} {request.url.path} after {duration_ms}ms: {exc}",
                exc_info=True,
                extra={"duration_ms": duration_ms, "path": request.url.path},
            )
            raise
        finally:
            request_id_ctx_var.reset(token)
