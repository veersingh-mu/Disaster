"""Master seed script to populate users, settlements, and benchmark case studies."""

import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
for p in [BASE_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.database import get_database_url  # noqa: E402
from backend.seed.seed_case_studies import seed_case_studies  # noqa: E402
from backend.seed.seed_settlements import seed_settlements  # noqa: E402
from backend.seed.seed_system_user import seed_users  # noqa: E402


def run_all_seeds(db_url: str | None = None) -> dict:
    url = db_url or get_database_url()
    engine = create_engine(url)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        with session.begin():
            users = seed_users(session)
            settlements = seed_settlements(session)
            case_study = seed_case_studies(session)
            event_year = case_study.event_year

    return {
        "users_count": len(users),
        "settlements_count": len(settlements),
        "case_study_year": event_year,
    }


if __name__ == "__main__":
    result = run_all_seeds()
    print("Seed process completed successfully:")
    print(result)
