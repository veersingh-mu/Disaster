"""Seed Himalayan settlements reference data."""

import os
import sys
import uuid
from typing import Dict

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
for p in [BASE_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.models.settlement import Settlement  # noqa: E402

HIMALAYAN_SETTLEMENTS = [
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000001"),
        "name": "Rini Village",
        "latitude": 30.4855,
        "longitude": 79.7122,
        "population": 420,
        "state": "Uttarakhand",
        "district": "Chamoli",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000002"),
        "name": "Tapovan",
        "latitude": 30.4952,
        "longitude": 79.6251,
        "population": 1150,
        "state": "Uttarakhand",
        "district": "Chamoli",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000003"),
        "name": "Joshimath",
        "latitude": 30.5583,
        "longitude": 79.5670,
        "population": 16700,
        "state": "Uttarakhand",
        "district": "Chamoli",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000004"),
        "name": "Helang",
        "latitude": 30.5281,
        "longitude": 79.5083,
        "population": 850,
        "state": "Uttarakhand",
        "district": "Chamoli",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000005"),
        "name": "Pipalkoti",
        "latitude": 30.4320,
        "longitude": 79.4312,
        "population": 2400,
        "state": "Uttarakhand",
        "district": "Chamoli",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000006"),
        "name": "Chamoli",
        "latitude": 30.4074,
        "longitude": 79.3518,
        "population": 21400,
        "state": "Uttarakhand",
        "district": "Chamoli",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000007"),
        "name": "Nandprayag",
        "latitude": 30.3312,
        "longitude": 79.3245,
        "population": 1600,
        "state": "Uttarakhand",
        "district": "Chamoli",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000008"),
        "name": "Karnaprayag",
        "latitude": 30.2581,
        "longitude": 79.2173,
        "population": 8200,
        "state": "Uttarakhand",
        "district": "Chamoli",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000009"),
        "name": "Rudraprayag",
        "latitude": 30.2854,
        "longitude": 78.9812,
        "population": 9300,
        "state": "Uttarakhand",
        "district": "Rudraprayag",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000010"),
        "name": "Srinagar Garhwal",
        "latitude": 30.2224,
        "longitude": 78.7845,
        "population": 37900,
        "state": "Uttarakhand",
        "district": "Pauri Garhwal",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000011"),
        "name": "Devprayag",
        "latitude": 30.1462,
        "longitude": 78.5991,
        "population": 2150,
        "state": "Uttarakhand",
        "district": "Tehri Garhwal",
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000012"),
        "name": "Rishikesh",
        "latitude": 30.0869,
        "longitude": 78.2676,
        "population": 102000,
        "state": "Uttarakhand",
        "district": "Dehradun",
    },
]


def seed_settlements(session: Session) -> Dict[str, Settlement]:
    """Seeds settlements reference data if not present."""
    seeded = {}
    with session.no_autoflush:
        for item in HIMALAYAN_SETTLEMENTS:
            existing = session.execute(
                select(Settlement).where(Settlement.id == item["id"])
            ).scalar_one_or_none()

            wkt_point = f"SRID=4326;POINT({item['longitude']} {item['latitude']})"
            if existing is None:
                settlement = Settlement(
                    id=item["id"],
                    name=item["name"],
                    location=WKTElement(wkt_point, srid=4326),
                    population=item["population"],
                    state=item["state"],
                    district=item["district"],
                )
                session.add(settlement)
                seeded[item["name"]] = settlement
            else:
                seeded[item["name"]] = existing

    session.flush()
    return seeded


if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from backend.app.database import get_database_url

    url = get_database_url()
    engine = create_engine(url)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db_session:
        with db_session.begin():
            res = seed_settlements(db_session)
            print(f"Seeded {len(res)} settlements: {list(res.keys())}")
