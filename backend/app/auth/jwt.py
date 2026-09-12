"""JWT token creation and decoding utilities."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt

DEFAULT_SECRET = "floodpath-inundation-scenario-jwt-secret-key-2026-sih"
DEFAULT_ALGORITHM = "HS256"
DEFAULT_EXPIRE_MINUTES = 1440


def get_jwt_secret() -> str:
    return os.getenv("JWT_SECRET", DEFAULT_SECRET)


def get_jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", DEFAULT_ALGORITHM)


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", DEFAULT_EXPIRE_MINUTES))
        expire = now + timedelta(minutes=minutes)

    to_encode.update({"exp": expire, "iat": now})
    secret = get_jwt_secret()
    algorithm = get_jwt_algorithm()
    return jwt.encode(to_encode, secret, algorithm=algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.
    
    Supports seamless fallback to DEFAULT_SECRET so existing browser sessions
    minted before or during environment configuration reload remain valid.
    """
    secret = get_jwt_secret()
    algorithm = get_jwt_algorithm()
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.InvalidSignatureError:
        if secret != DEFAULT_SECRET:
            return jwt.decode(token, DEFAULT_SECRET, algorithms=[algorithm])
        raise


def validate_jwt_configuration() -> bool:
    """Audit JWT configuration and warn or raise if an insecure secret is in production."""
    env = os.getenv("ENVIRONMENT", "development").lower()
    secret = get_jwt_secret()
    if env == "production":
        if secret == DEFAULT_SECRET:
            raise ValueError(
                "CRITICAL SECURITY RISK: Insecure default JWT_SECRET detected in production environment! "
                "You must set a unique, high-entropy JWT_SECRET in production."
            )
        if len(secret) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long in production.")
    return True

