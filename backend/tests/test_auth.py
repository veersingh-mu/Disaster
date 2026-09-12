"""Unit and integration tests for Authentication (Phase 3)."""

import os
import sys
from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
for p in [BASE_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.auth.jwt import create_access_token, decode_access_token  # noqa: E402
from backend.app.auth.service import hash_password, verify_password  # noqa: E402
from backend.app.database import get_db  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models import Base, User  # noqa: E402
from backend.seed.seed_system_user import DEFAULT_PASSWORD, seed_users  # noqa: E402


@pytest.fixture
def auth_test_db():
    """Sets up an in-memory SQLite database populated with seeded users."""
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    from sqlalchemy.ext.compiler import compiles

    @compiles(PG_UUID, "sqlite")
    def compile_uuid(type_, comp, **kw):
        return "TEXT"

    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Base.metadata.tables["users"]])
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    seed_users(session)

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(auth_test_db):
    """TestClient that overrides the get_db dependency with the test session."""

    def override_get_db():
        try:
            yield auth_test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


class TestAuthUnits:
    """Unit tests for password hashing and JWT issuance/decoding."""

    def test_password_hash_and_verification(self):
        plain = "SecretPass123!"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed) is True
        assert verify_password("WrongPassword!", hashed) is False

    def test_jwt_encode_and_decode(self):
        payload = {"sub": "12345", "email": "test@example.com", "role": "analyst"}
        token = create_access_token(payload, expires_delta=timedelta(minutes=15))
        decoded = decode_access_token(token)

        assert decoded["sub"] == "12345"
        assert decoded["email"] == "test@example.com"
        assert decoded["role"] == "analyst"
        assert "exp" in decoded

    def test_jwt_expired_token_raises(self):
        payload = {"sub": "12345"}
        expired_token = create_access_token(payload, expires_delta=timedelta(seconds=-10))

        with pytest.raises(jwt.ExpiredSignatureError):
            decode_access_token(expired_token)

    def test_jwt_invalid_signature_raises(self):
        payload = {"sub": "12345"}
        token = jwt.encode(
            payload, "completely-wrong-secret-key-that-is-at-least-32-chars-long", algorithm="HS256"
        )

        with pytest.raises(jwt.InvalidSignatureError):
            decode_access_token(token)


class TestAuthEndpoints:
    """Integration tests for /auth/login, /auth/guest, and /auth/me."""

    def test_login_success_returns_jwt_and_user(self, client):
        response = client.post(
            "/auth/login",
            json={
                "email": "analyst@floodpath.internal",
                "password": DEFAULT_PASSWORD,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "analyst@floodpath.internal"
        assert data["user"]["role"] == "analyst"

        # Verify the issued token decodes cleanly
        decoded = decode_access_token(data["access_token"])
        assert decoded["email"] == "analyst@floodpath.internal"
        assert decoded["role"] == "analyst"

    def test_login_invalid_password_returns_401(self, client):
        response = client.post(
            "/auth/login",
            json={
                "email": "analyst@floodpath.internal",
                "password": "IncorrectPassword123!",
            },
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    def test_login_nonexistent_user_returns_401(self, client):
        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@floodpath.internal",
                "password": "AnyPassword123!",
            },
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    def test_guest_session_creates_no_database_user(self, client, auth_test_db):
        # Count users before
        users_before = auth_test_db.query(User).count()

        response = client.post("/auth/guest")
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "guest"
        assert "Guest session initialized" in data["message"]

        # Count users after: must be identical
        users_after = auth_test_db.query(User).count()
        assert users_after == users_before

    def test_protected_me_endpoint_with_valid_token(self, client):
        login_resp = client.post(
            "/auth/login",
            json={
                "email": "analyst@floodpath.internal",
                "password": DEFAULT_PASSWORD,
            },
        )
        token = login_resp.json()["access_token"]

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "analyst@floodpath.internal"
        assert data["role"] == "analyst"

    def test_protected_me_endpoint_missing_token_returns_401(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_protected_me_endpoint_invalid_token_returns_401(self, client):
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer not-a-valid-token"},
        )
        assert response.status_code == 401
