"""Security and Rate-Limiting Middlewares for FloodPath API."""

import os
import re
import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects industry-standard HTTP security headers to protect against clickjacking,

    XSS, MIME-sniffing, and insecure transport.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)

        # Standard HTTP security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https: blob:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "connect-src 'self' https: http: ws: wss:; "
            "worker-src 'self' blob:;"
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window rate limiter for high-compute simulation endpoints.

    Limits invocations of `/scenarios/{id}/run` to prevent compute exhaustion.
    """

    def __init__(
        self,
        app,
        limit_per_window: int = 10,
        window_seconds: int = 60,
    ):
        super().__init__(app)
        self.limit_per_window = int(os.getenv("RATE_LIMIT_RUNS_PER_MINUTE", limit_per_window))
        self.window_seconds = window_seconds
        # Mapping of client_identifier -> list of epoch timestamps
        self.requests_log: dict[str, list[float]] = defaultdict(list)
        # Regex matching /scenarios/{id}/run
        self.run_endpoint_pattern = re.compile(r"^/scenarios/[^/]+/run/?$")

    def _get_client_id(self, request: Request) -> str:
        """Derive client identifier from Authorization header or remote IP."""
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            if len(token) > 20:
                return f"token:{token[-16:]}"

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        client = request.client
        return f"ip:{client.host}" if client else "ip:unknown"

    def reset(self) -> None:
        """Clear requests log (used in automated test suites)."""
        self.requests_log.clear()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if target is a simulation trigger endpoint: POST /scenarios/{id}/run
        if request.method == "POST" and self.run_endpoint_pattern.match(request.url.path):
            now = time.time()
            client_id = self._get_client_id(request)
            timestamps = self.requests_log[client_id]

            # Prune timestamps outside the active window
            cutoff = now - self.window_seconds
            timestamps = [ts for ts in timestamps if ts > cutoff]
            self.requests_log[client_id] = timestamps

            if len(timestamps) >= self.limit_per_window:
                retry_after = int(self.window_seconds - (now - timestamps[0])) + 1
                return JSONResponse(
                    status_code=429,
                    content={
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": (
                            f"Simulation run rate limit of {self.limit_per_window} requests per "
                            f"{self.window_seconds}s exceeded. Please wait before retrying."
                        ),
                        "retry_after_seconds": retry_after,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self.limit_per_window),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            timestamps.append(now)

        return await call_next(request)
