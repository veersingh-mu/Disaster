"""Seed system and demo analyst users."""

import os
import sys
import uuid

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

# Add project root and backend to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
for p in [BASE_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.models.enums import UserRole  # noqa: E402
from backend.app.models.user import User  # noqa: E402

SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ANALYST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

DEFAULT_PASSWORD = "FloodPath2026!"


def hash_password(plain_text: str) -> str:
    return bcrypt.hashpw(plain_text.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def seed_users(session: Session) -> dict[str, User]:
    """Seeds the fixed system user and demo analyst user if not present."""
    users_to_seed = [
        {
            "id": SYSTEM_USER_ID,
            "email": "system@floodpath.internal",
            "password_hash": hash_password(DEFAULT_PASSWORD),
            "role": UserRole.ANALYST,
        },
        {
            "id": ANALYST_USER_ID,
            "email": "analyst@floodpath.internal",
            "password_hash": hash_password(DEFAULT_PASSWORD),
            "role": UserRole.ANALYST,
        },
    ]

    seeded_users = {}
    for user_data in users_to_seed:
        existing = session.execute(
            select(User).where(User.email == user_data["email"])
        ).scalar_one_or_none()

        if existing is None:
            user = User(**user_data)
            session.add(user)
            seeded_users[user_data["email"]] = user
        else:
            seeded_users[user_data["email"]] = existing

    session.flush()
    return seeded_users


if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from backend.app.database import get_database_url

    url = get_database_url()
    engine = create_engine(url)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db_session:
        with db_session.begin():
            res = seed_users(db_session)
            print(f"Seeded {len(res)} users: {[u.email for u in res.values()]}")
