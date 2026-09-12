"""Authentication service logic: password hashing and verification."""

from typing import Optional

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.user import User


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def authenticate_user(session: Session, email: str, password: str) -> Optional[User]:
    user = session.execute(
        select(User).where(User.email == email.strip().lower())
    ).scalar_one_or_none()

    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
