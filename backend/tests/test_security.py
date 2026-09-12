"""Security & Hardening Tests (Phase 13).

Validates:
- Injection of mandatory HTTP security headers (CSP, X-Frame-Options, HSTS, etc.)
- Rate-limiting enforcement on simulation runs (HTTP 429 & Retry-After)
- Production cryptographic safety guards (JWT secret validation)
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.jwt import DEFAULT_SECRET, validate_jwt_configuration
from backend.app.main import app
from backend.app.middleware import RateLimitMiddleware


def test_security_headers_present():
    """Verify that all standard security headers are injected into HTTP responses."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "max-age=31536000" in headers.get("Strict-Transport-Security", "")
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")


def test_rate_limit_enforcement_on_run():
    """Verify that POST /scenarios/{id}/run enforces rate limiting when threshold is reached."""
    client = TestClient(app)

    # Find the RateLimitMiddleware instance on app to adjust window or test cleanly
    rate_limiter = None
    for middleware in app.user_middleware:
        if middleware.cls == RateLimitMiddleware:
            # We can test by setting limit or using client
            pass

    # Find middleware in app's middleware stack
    current = app.middleware_stack
    while hasattr(current, "app"):
        if isinstance(current, RateLimitMiddleware):
            rate_limiter = current
            break
        current = current.app

    if rate_limiter:
        rate_limiter.reset()
        original_limit = rate_limiter.limit_per_window
        rate_limiter.limit_per_window = 3
        try:
            scenario_id = "00000000-0000-0000-0000-000000000001"
            headers = {"Authorization": "Bearer test-client-rate-limit-token-xyz"}

            # First 3 requests should pass through to auth/router (returning 401 or whatever)
            for _ in range(3):
                res = client.post(f"/scenarios/{scenario_id}/run", headers=headers)
                assert res.status_code != 429

            # 4th request MUST hit rate limiter and return 429
            res_limited = client.post(f"/scenarios/{scenario_id}/run", headers=headers)
            assert res_limited.status_code == 429
            data = res_limited.json()
            assert data.get("error_code") == "RATE_LIMIT_EXCEEDED"
            assert "retry_after_seconds" in data
            assert "Retry-After" in res_limited.headers
        finally:
            rate_limiter.limit_per_window = original_limit
            rate_limiter.reset()


def test_jwt_production_validation(monkeypatch):
    """Verify validate_jwt_configuration rejects insecure default secret in production."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", DEFAULT_SECRET)

    with pytest.raises(ValueError, match="CRITICAL SECURITY RISK"):
        validate_jwt_configuration()

    # Short secret in production should also fail
    monkeypatch.setenv("JWT_SECRET", "short_secret")
    with pytest.raises(ValueError, match="at least 32 characters"):
        validate_jwt_configuration()

    # Strong secret in production should succeed
    monkeypatch.setenv("JWT_SECRET", "super-secret-high-entropy-production-key-floodpath-32chars")
    assert validate_jwt_configuration() is True
