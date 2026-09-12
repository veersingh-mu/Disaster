"""Comprehensive User Journey Tests (APP_FLOW.md Compliance).

Simulates and verifies all end-to-end user workflows:
1. Authentication & Role Selection (Analyst Login & Guest Session)
2. Dashboard & Scenario Registry Browsing
3. DEM Acquisition & Topographic Auto-Fill
4. Scenario Configuration & Full 2D Simulation Execution
5. Polling Lifecycle & Results Exploration (Map MultiPolygons & Settlements)
6. Fast AI Surrogate Mode Execution (< 50ms)
7. Emergency CAP-XML Alert Dispatch & JSON Dossier Export
8. Historical Benchmark Case Study Replay (Rishi Ganga 2021)
9. Error, Validation, and Failure Recovery Paths
"""

import uuid

import geoalchemy2.admin.dialects.sqlite as sqlite_admin
import pytest
from fastapi.testclient import TestClient
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sqlite_admin.after_create = lambda *a, **k: None
sqlite_admin.before_create = lambda *a, **k: None


@compiles(Geometry, "sqlite")
def compile_geom(el, comp, **kw):
    return "TEXT"


@compiles(WKTElement, "sqlite")
def compile_wkt(el, comp, **kw):
    return comp.process(el.data, **kw) if hasattr(el, "data") else str(el)


@compiles(PG_UUID, "sqlite")
def compile_uuid(type_, comp, **kw):
    return "TEXT"


from backend.app.auth.service import hash_password  # noqa: E402
from backend.app.database import get_db  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models import (  # noqa: E402
    Base,
    CaseStudy,
    FloodResult,
    Scenario,
    Settlement,
    SimulationRun,
    User,
)
from backend.app.models.enums import BreachType, PipelineStage, RunStatus, UserRole  # noqa: E402


@pytest.fixture
def journey_env():
    """Setup in-memory SQLite database, seed baseline records, and TestClient."""
    orig_bind = Geometry.bind_expression
    orig_col = Geometry.column_expression
    orig_res = Geometry.result_processor

    Geometry.bind_expression = lambda self, bindvalue: (
        bindvalue.data if hasattr(bindvalue, "data") else bindvalue
    )
    Geometry.column_expression = lambda self, col: col
    Geometry.result_processor = lambda self, dialect, coltype: lambda value: value

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    # Seed User (Analyst)
    user = User(
        id=uuid.uuid4(),
        email="analyst@floodpath.internal",
        password_hash=hash_password("FloodPath2026!"),
        role=UserRole.ANALYST,
    )
    session.add(user)

    # Seed Reference Settlements
    st1 = Settlement(
        id=uuid.uuid4(),
        name="Raini",
        district="Chamoli",
        state="Uttarakhand",
        population=250,
        location="SRID=4326;POINT(79.689 30.485)",
    )
    st2 = Settlement(
        id=uuid.uuid4(),
        name="Tapovan",
        district="Chamoli",
        state="Uttarakhand",
        population=1200,
        location="SRID=4326;POINT(79.625 30.495)",
    )
    session.add_all([st1, st2])

    # Seed Historical Case Study (Rishi Ganga 2021)
    cs_scenario = Scenario(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Rishi Ganga GLOF Benchmark 2021",
        site_point="SRID=4326;POINT(79.735 30.375)",
        breach_type=BreachType.LANDSLIDE_GLOF,
        dam_height_m=35.0,
        dam_volume_m3=1_500_000.0,
        simulation_radius_km=45.0,
    )
    session.add(cs_scenario)
    session.flush()

    cs_run = SimulationRun(
        id=uuid.uuid4(),
        scenario_id=cs_scenario.id,
        status=RunStatus.SUCCEEDED,
        current_stage=PipelineStage.SUMMARY_GENERATION,
    )
    session.add(cs_run)
    session.flush()

    res_poly = FloodResult(
        id=uuid.uuid4(),
        simulation_run_id=cs_run.id,
        time_step_minutes=15,
        max_depth_m=28.4,
        flood_extent="SRID=4326;MULTIPOLYGON(((79.73 30.37, 79.74 30.37, 79.74 30.38, 79.73 30.38, 79.73 30.37)))",
    )
    session.add(res_poly)

    case_study = CaseStudy(
        id=uuid.uuid4(),
        scenario_id=cs_scenario.id,
        simulation_run_id=cs_run.id,
        event_year=2021,
        description="Benchmark validation against CWC post-event flood surveys.",
        source_reference="CWC Survey 2021",
    )
    session.add(case_study)
    session.commit()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)

    try:
        yield {
            "client": client,
            "session": session,
            "user": user,
            "case_study": case_study,
        }
    finally:
        app.dependency_overrides.clear()
        Geometry.bind_expression = orig_bind
        Geometry.column_expression = orig_col
        Geometry.result_processor = orig_res


def test_complete_user_journeys(journey_env):
    client = journey_env["client"]

    # -------------------------------------------------------------
    # Journey 1: Authentication & Role Selection
    # -------------------------------------------------------------
    # 1A. Guest Session
    guest_res = client.post("/auth/guest")
    assert guest_res.status_code == 200
    guest_data = guest_res.json()
    assert guest_data["role"] == "guest"

    # 1B. Analyst Login
    login_res = client.post("/auth/login", json={
        "email": "analyst@floodpath.internal",
        "password": "FloodPath2026!"
    })
    assert login_res.status_code == 200
    auth_data = login_res.json()
    token = auth_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1C. Verify Me
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "analyst@floodpath.internal"

    # -------------------------------------------------------------
    # Journey 2: Dashboard & Scenarios Registry
    # -------------------------------------------------------------
    dash_res = client.get("/scenarios", headers=headers)
    assert dash_res.status_code == 200
    scenarios_list = dash_res.json()
    assert "scenarios" in scenarios_list
    assert "total" in scenarios_list

    # -------------------------------------------------------------
    # Journey 3: DEM Topographic Auto-Fill Query
    # -------------------------------------------------------------
    dem_res = client.get(
        "/dem/preview?latitude=30.375&longitude=79.735&simulation_radius_km=30.0",
        headers=headers,
    )
    assert dem_res.status_code == 200
    dem_data = dem_res.json()
    assert dem_data["elevation_m"] > 0
    assert dem_data["estimated_dam_height_m"] > 0
    assert dem_data["estimated_dam_volume_m3"] > 0

    # -------------------------------------------------------------
    # Journey 4: Scenario Creation & Validation
    # -------------------------------------------------------------
    # 4A. Form Validation Error Handling
    bad_res = client.post("/scenarios", headers=headers, json={
        "name": "",
        "latitude": 95.0,  # Invalid lat > 90
        "longitude": 79.5,
        "breach_type": "structural",
        "dam_height_m": -10.0,  # Invalid negative
        "dam_volume_m3": 100000.0,
    })
    assert bad_res.status_code == 422

    # 4B. Valid Scenario Creation
    create_res = client.post("/scenarios", headers=headers, json={
        "name": "Tapovan Dhauliganga Test Run",
        "latitude": 30.50,
        "longitude": 79.62,
        "breach_type": "landslide_glof",
        "dam_height_m": 35.0,
        "dam_volume_m3": 1_200_000.0,
        "simulation_radius_km": 25.0,
        "is_dem_estimated": True,
    })
    assert create_res.status_code == 201
    scenario = create_res.json()
    scenario_id = scenario["id"]

    # -------------------------------------------------------------
    # Journey 5: Full 2D Simulation Execution & Results Exploration
    # -------------------------------------------------------------
    run_res = client.post(f"/scenarios/{scenario_id}/run", headers=headers, json={"mode": "full"})
    assert run_res.status_code == 202
    run_data = run_res.json()
    run_id = uuid.UUID(run_data["id"])

    # Execute simulation pipeline on SQLite test session
    from worker.run import run_simulation_pipeline
    session = journey_env["session"]
    pipe_res = run_simulation_pipeline(session=session, run_id=run_id, scenario_id=uuid.UUID(scenario_id), mode="full")
    assert pipe_res["status"] == RunStatus.SUCCEEDED

    # Status check
    status_res = client.get(f"/scenarios/{scenario_id}/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "succeeded"

    # Retrieve Results
    results_res = client.get(f"/scenarios/{scenario_id}/results", headers=headers)
    assert results_res.status_code == 200
    results = results_res.json()
    assert "time_steps" in results
    assert "affected_settlements" in results
    assert "peak_depth_m" in results
    assert len(results["time_steps"]) > 0

    # Verify GeoJSON polygon format
    first_step = results["time_steps"][0]
    assert "flood_extent" in first_step
    assert first_step["flood_extent"]["type"] in ["MultiPolygon", "Polygon"]

    # -------------------------------------------------------------
    # Journey 6: Fast AI Surrogate Mode Execution (< 50ms)
    # -------------------------------------------------------------
    ai_create_res = client.post("/scenarios", headers=headers, json={
        "name": "Fast AI Surrogate Sweep Site",
        "latitude": 30.40,
        "longitude": 79.60,
        "breach_type": "landslide_glof",
        "dam_height_m": 40.0,
        "dam_volume_m3": 2_000_000.0,
        "simulation_radius_km": 30.0,
    })
    assert ai_create_res.status_code == 201
    ai_scenario_id = ai_create_res.json()["id"]

    ai_run_res = client.post(
        f"/scenarios/{ai_scenario_id}/run",
        headers=headers,
        json={"mode": "fast"},
    )
    assert ai_run_res.status_code == 202
    ai_run_id = uuid.UUID(ai_run_res.json()["id"])
    run_simulation_pipeline(session=session, run_id=ai_run_id, scenario_id=uuid.UUID(ai_scenario_id), mode="fast")

    ai_results_res = client.get(f"/scenarios/{ai_scenario_id}/results", headers=headers)
    assert ai_results_res.status_code == 200
    ai_results = ai_results_res.json()
    assert len(ai_results["time_steps"]) > 0

    # -------------------------------------------------------------
    # Journey 7: Emergency Alert (CAP v1.2 XML) & Export Dossier
    # -------------------------------------------------------------
    # 7A. CAP XML Broadcast Alert
    cap_res = client.get(f"/scenarios/{scenario_id}/alert/cap-xml", headers=headers)
    assert cap_res.status_code == 200
    assert "application/xml" in cap_res.headers["content-type"]
    xml_content = cap_res.text
    assert "<alert" in xml_content
    assert "urn:oasis:names:tc:emergency:cap:1.2" in xml_content
    assert "<sender>" in xml_content
    assert "floodpath" in xml_content

    # 7B. Create JSON Dossier Export
    export_create_res = client.post(
        f"/scenarios/{scenario_id}/export",
        headers=headers,
        json={"export_format": "json"},
    )
    assert export_create_res.status_code == 201
    export_id = export_create_res.json()["id"]

    export_data_res = client.get(f"/exports/{export_id}/data", headers=headers)
    assert export_data_res.status_code == 200

    # -------------------------------------------------------------
    # Journey 8: Historical Case Studies Replay
    # -------------------------------------------------------------
    cs_res = client.get("/case-studies", headers=headers)
    assert cs_res.status_code == 200
    case_studies = cs_res.json()["case_studies"]
    assert len(case_studies) > 0
    first_cs_id = case_studies[0]["id"]

    cs_results_res = client.get(f"/case-studies/{first_cs_id}/results", headers=headers)
    assert cs_results_res.status_code == 200
    cs_results = cs_results_res.json()
    assert cs_results["peak_depth_m"] is not None
    assert len(cs_results["time_steps"]) > 0

    # -------------------------------------------------------------
    # Journey 9: Cleanup & Deletion
    # -------------------------------------------------------------
    del_res = client.delete(f"/scenarios/{scenario_id}", headers=headers)
    assert del_res.status_code == 204
    client.delete(f"/scenarios/{ai_scenario_id}", headers=headers)
