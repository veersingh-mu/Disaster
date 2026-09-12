"""Seed historical case studies with backing scenario, simulation run, flood results, and affected settlements."""

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
for p in [BASE_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.models.affected_settlement import AffectedSettlement  # noqa: E402
from backend.app.models.case_study import CaseStudy  # noqa: E402
from backend.app.models.enums import BreachType, PipelineStage, RunStatus  # noqa: E402
from backend.app.models.flood_result import FloodResult  # noqa: E402
from backend.app.models.scenario import Scenario  # noqa: E402
from backend.app.models.simulation_run import SimulationRun  # noqa: E402
from backend.seed.seed_settlements import seed_settlements  # noqa: E402
from backend.seed.seed_system_user import SYSTEM_USER_ID, seed_users  # noqa: E402

RISHI_GANGA_SCENARIO_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
RISHI_GANGA_RUN_ID = uuid.UUID("30000000-0000-0000-0000-000000000001")
RISHI_GANGA_CASE_STUDY_ID = uuid.UUID("40000000-0000-0000-0000-000000000001")


def create_polygon_wkt(lon_min: float, lat_min: float, lon_max: float, lat_max: float) -> str:
    """Helper to generate a valid GeoJSON/WKT MultiPolygon."""
    return (
        f"SRID=4326;MULTIPOLYGON((("
        f"{lon_min} {lat_min}, "
        f"{lon_max} {lat_min}, "
        f"{lon_max} {lat_max}, "
        f"{lon_min} {lat_max}, "
        f"{lon_min} {lat_min}"
        f")))"
    )


def seed_case_studies(session: Session) -> CaseStudy:
    """Seeds the Rishi Ganga 2021 historical benchmark case study."""
    # Ensure system user and settlements exist
    seed_users(session)
    settlements = seed_settlements(session)

    # 1. Backing Scenario
    scenario = session.execute(
        select(Scenario).where(Scenario.id == RISHI_GANGA_SCENARIO_ID)
    ).scalar_one_or_none()

    if scenario is None:
        site_point_wkt = "SRID=4326;POINT(79.7333 30.3833)"
        scenario = Scenario(
            id=RISHI_GANGA_SCENARIO_ID,
            user_id=SYSTEM_USER_ID,
            name="Rishi Ganga 2021 Rock-Ice Avalanche & GLOF",
            site_point=WKTElement(site_point_wkt, srid=4326),
            breach_type=BreachType.LANDSLIDE_GLOF,
            dam_height_m=36.00,
            dam_volume_m3=27000000.00,
            simulation_radius_km=45.00,
            is_dem_estimated=False,
        )
        session.add(scenario)
        session.flush()

    # 2. Simulation Run (Succeeded)
    run = session.execute(
        select(SimulationRun).where(SimulationRun.id == RISHI_GANGA_RUN_ID)
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if run is None:
        run = SimulationRun(
            id=RISHI_GANGA_RUN_ID,
            scenario_id=RISHI_GANGA_SCENARIO_ID,
            status=RunStatus.SUCCEEDED,
            current_stage=PipelineStage.SUMMARY_GENERATION,
            error_stage=None,
            error_message=None,
            started_at=now - timedelta(minutes=4),
            completed_at=now - timedelta(minutes=1),
        )
        session.add(run)
        session.flush()

    # 3. Time-stepped Flood Results
    # Corridors tracing from Upper Moraine down to Dhauliganga and Alaknanda
    time_steps = [
        {"minutes": 0, "max_depth": 28.5, "bbox": (79.720, 30.375, 79.740, 30.390)},
        {"minutes": 15, "max_depth": 22.0, "bbox": (79.700, 30.400, 79.730, 30.440)},
        {"minutes": 30, "max_depth": 17.5, "bbox": (79.670, 30.440, 79.715, 30.490)},
        {"minutes": 45, "max_depth": 14.0, "bbox": (79.610, 30.480, 79.680, 30.510)},
        {"minutes": 60, "max_depth": 11.2, "bbox": (79.560, 30.520, 79.630, 30.560)},
        {"minutes": 90, "max_depth": 8.0, "bbox": (79.500, 30.500, 79.570, 30.560)},
        {"minutes": 120, "max_depth": 5.5, "bbox": (79.420, 30.420, 79.510, 30.530)},
        {"minutes": 180, "max_depth": 3.8, "bbox": (79.340, 30.390, 79.440, 30.440)},
        {"minutes": 240, "max_depth": 2.6, "bbox": (79.200, 30.250, 79.350, 30.400)},
        {"minutes": 330, "max_depth": 1.7, "bbox": (78.970, 30.240, 79.220, 30.300)},
    ]

    for step in time_steps:
        existing_step = session.execute(
            select(FloodResult).where(
                FloodResult.simulation_run_id == RISHI_GANGA_RUN_ID,
                FloodResult.time_step_minutes == step["minutes"],
            )
        ).scalar_one_or_none()

        if existing_step is None:
            wkt_geom = create_polygon_wkt(*step["bbox"])
            fr = FloodResult(
                simulation_run_id=RISHI_GANGA_RUN_ID,
                time_step_minutes=step["minutes"],
                flood_extent=WKTElement(wkt_geom, srid=4326),
                max_depth_m=step["max_depth"],
            )
            session.add(fr)

    # 4. Affected Settlements
    arrival_schedule = [
        {"name": "Rini Village", "arrival_min": 18, "depth_m": 14.50},
        {"name": "Tapovan", "arrival_min": 42, "depth_m": 11.20},
        {"name": "Joshimath", "arrival_min": 72, "depth_m": 7.80},
        {"name": "Helang", "arrival_min": 95, "depth_m": 5.40},
        {"name": "Pipalkoti", "arrival_min": 130, "depth_m": 3.80},
        {"name": "Chamoli", "arrival_min": 185, "depth_m": 2.90},
        {"name": "Nandprayag", "arrival_min": 220, "depth_m": 2.20},
        {"name": "Karnaprayag", "arrival_min": 260, "depth_m": 1.80},
        {"name": "Rudraprayag", "arrival_min": 330, "depth_m": 1.40},
    ]

    for item in arrival_schedule:
        settlement = settlements.get(item["name"])
        if settlement:
            existing_aff = session.execute(
                select(AffectedSettlement).where(
                    AffectedSettlement.simulation_run_id == RISHI_GANGA_RUN_ID,
                    AffectedSettlement.settlement_id == settlement.id,
                )
            ).scalar_one_or_none()

            if existing_aff is None:
                aff = AffectedSettlement(
                    simulation_run_id=RISHI_GANGA_RUN_ID,
                    settlement_id=settlement.id,
                    arrival_time_minutes=item["arrival_min"],
                    estimated_depth_m=item["depth_m"],
                )
                session.add(aff)

    # 5. Case Study Entry
    case_study = session.execute(
        select(CaseStudy).where(CaseStudy.id == RISHI_GANGA_CASE_STUDY_ID)
    ).scalar_one_or_none()

    if case_study is None:
        case_study = CaseStudy(
            id=RISHI_GANGA_CASE_STUDY_ID,
            scenario_id=RISHI_GANGA_SCENARIO_ID,
            simulation_run_id=RISHI_GANGA_RUN_ID,
            event_year=2021,
            description=(
                "Catastrophic detachment of approximately 27 million cubic meters of glacier ice "
                "and rock from Ronti Peak at 5,500m elevation. The massive pulverized mass transformed "
                "into a hyper-concentrated slurry surge traversing the Rishi Ganga and Dhauliganga "
                "gorges, directly impacting the Rishi Ganga Hydroelectric Project and Tapovan "
                "Vishnugad Dam site."
            ),
            source_reference="Science 373(6552):300-306 (2021); Shugar et al. / NDMA Chamoli Post-Event Field Report",
        )
        session.add(case_study)

    session.flush()
    return case_study


if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from backend.app.database import get_database_url

    url = get_database_url()
    engine = create_engine(url)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db_session:
        with db_session.begin():
            cs = seed_case_studies(db_session)
            print(f"Seeded Case Study: {cs.event_year} - {cs.id}")
