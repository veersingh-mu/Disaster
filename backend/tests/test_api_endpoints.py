"""Integration and unit tests for all Phase 6 core API endpoints."""

import uuid
from datetime import datetime, timezone

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


from backend.app.auth.jwt import create_access_token  # noqa: E402
from backend.app.auth.service import hash_password  # noqa: E402
from backend.app.database import get_db  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models import (  # noqa: E402
    AffectedSettlement,
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
def api_test_env():
    """Setup in-memory SQLite database, mock tables, test users, and TestClient."""
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

    # Seed User A (Analyst) and User B (Analyst)
    user_a = User(
        id=uuid.uuid4(),
        email="analyst.alpha@floodpath.in",
        password_hash=hash_password("Password123!"),
        role=UserRole.ANALYST,
    )
    user_b = User(
        id=uuid.uuid4(),
        email="analyst.beta@floodpath.in",
        password_hash=hash_password("Password123!"),
        role=UserRole.ANALYST,
    )
    session.add_all([user_a, user_b])
    session.commit()

    token_a = create_access_token({"sub": str(user_a.id), "role": user_a.role.value})
    token_b = create_access_token({"sub": str(user_b.id), "role": user_b.role.value})

    # Override get_db dependency in FastAPI app
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
            "user_a": user_a,
            "user_b": user_b,
            "token_a": token_a,
            "token_b": token_b,
            "headers_a": {"Authorization": f"Bearer {token_a}"},
            "headers_b": {"Authorization": f"Bearer {token_b}"},
        }
    finally:
        app.dependency_overrides.clear()
        session.close()
        Geometry.bind_expression = orig_bind
        Geometry.column_expression = orig_col
        Geometry.result_processor = orig_res


# ---------------------------------------------------------------------------
# 1. Scenarios CRUD & Ownership Tests
# ---------------------------------------------------------------------------
class TestScenarioEndpoints:
    def test_create_scenario_success(self, api_test_env):
        client = api_test_env["client"]
        headers = api_test_env["headers_a"]

        payload = {
            "name": "Nanda Devi Outflow Study",
            "latitude": 30.3833,
            "longitude": 79.7333,
            "breach_type": "landslide_glof",
            "dam_height_m": 38.5,
            "dam_volume_m3": 25000000.0,
            "simulation_radius_km": 35.0,
            "is_dem_estimated": True,
        }
        res = client.post("/scenarios", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Nanda Devi Outflow Study"
        assert abs(data["latitude"] - 30.3833) < 1e-4
        assert abs(data["longitude"] - 79.7333) < 1e-4
        assert data["breach_type"] == "landslide_glof"
        assert data["dam_height_m"] == 38.5
        assert data["is_dem_estimated"] is True
        assert "id" in data
        assert data["user_id"] == str(api_test_env["user_a"].id)

    def test_create_scenario_validation_failure(self, api_test_env):
        client = api_test_env["client"]
        headers = api_test_env["headers_a"]

        # Invalid: negative dam height and out of bounds latitude
        payload = {
            "name": "Invalid Site",
            "latitude": 150.0,  # invalid (> 90)
            "longitude": 79.7333,
            "breach_type": "structural",
            "dam_height_m": -20.0,  # invalid (<= 0)
            "dam_volume_m3": 1000000.0,
        }
        res = client.post("/scenarios", json=payload, headers=headers)
        assert res.status_code == 422
        data = res.json()
        assert data["error_code"] == "VALIDATION_ERROR"
        assert len(data["details"]) >= 2

    def test_list_scenarios_isolation(self, api_test_env):
        client = api_test_env["client"]
        session = api_test_env["session"]
        user_a = api_test_env["user_a"]
        user_b = api_test_env["user_b"]

        sc_a = Scenario(
            id=uuid.uuid4(),
            user_id=user_a.id,
            name="Scenario A Only",
            site_point="POINT(79.0 30.0)",
            breach_type=BreachType.STRUCTURAL,
            dam_height_m=50.0,
            dam_volume_m3=1000000.0,
        )
        sc_b = Scenario(
            id=uuid.uuid4(),
            user_id=user_b.id,
            name="Scenario B Only",
            site_point="POINT(78.0 29.0)",
            breach_type=BreachType.LANDSLIDE_GLOF,
            dam_height_m=30.0,
            dam_volume_m3=500000.0,
        )
        session.add_all([sc_a, sc_b])
        session.commit()

        # User A should only see their scenario
        res_a = client.get("/scenarios", headers=api_test_env["headers_a"])
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert data_a["total"] == 1
        assert data_a["scenarios"][0]["id"] == str(sc_a.id)

        # User B should only see their scenario
        res_b = client.get("/scenarios", headers=api_test_env["headers_b"])
        assert res_b.status_code == 200
        data_b = res_b.json()
        assert data_b["total"] == 1
        assert data_b["scenarios"][0]["id"] == str(sc_b.id)

    def test_get_scenario_ownership_enforcement(self, api_test_env):
        client = api_test_env["client"]
        session = api_test_env["session"]
        user_a = api_test_env["user_a"]

        sc_a = Scenario(
            id=uuid.uuid4(),
            user_id=user_a.id,
            name="Private Scenario",
            site_point="POINT(79.5 30.5)",
            breach_type=BreachType.STRUCTURAL,
            dam_height_m=45.0,
            dam_volume_m3=800000.0,
        )
        session.add(sc_a)
        session.commit()

        # User A accesses their own scenario -> 200
        res_a = client.get(f"/scenarios/{sc_a.id}", headers=api_test_env["headers_a"])
        assert res_a.status_code == 200
        assert res_a.json()["id"] == str(sc_a.id)

        # User B attempts access -> 403 Forbidden
        res_b = client.get(f"/scenarios/{sc_a.id}", headers=api_test_env["headers_b"])
        assert res_b.status_code == 403
        data_b = res_b.json()
        assert data_b["error_code"] == "FORBIDDEN_SCENARIO_ACCESS"

    def test_update_scenario(self, api_test_env):
        client = api_test_env["client"]
        session = api_test_env["session"]
        user_a = api_test_env["user_a"]

        sc = Scenario(
            id=uuid.uuid4(),
            user_id=user_a.id,
            name="Original Name",
            site_point="POINT(79.0 30.0)",
            breach_type=BreachType.STRUCTURAL,
            dam_height_m=50.0,
            dam_volume_m3=1000000.0,
            simulation_radius_km=25.0,
        )
        session.add(sc)
        session.commit()

        update_payload = {"name": "Updated Name", "simulation_radius_km": 40.0}
        res = client.patch(f"/scenarios/{sc.id}", json=update_payload, headers=api_test_env["headers_a"])
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Updated Name"
        assert data["simulation_radius_km"] == 40.0

    def test_delete_scenario(self, api_test_env):
        client = api_test_env["client"]
        session = api_test_env["session"]
        user_a = api_test_env["user_a"]

        sc = Scenario(
            id=uuid.uuid4(),
            user_id=user_a.id,
            name="To Delete",
            site_point="POINT(79.0 30.0)",
            breach_type=BreachType.STRUCTURAL,
            dam_height_m=50.0,
            dam_volume_m3=1000000.0,
        )
        session.add(sc)
        session.commit()

        res = client.delete(f"/scenarios/{sc.id}", headers=api_test_env["headers_a"])
        assert res.status_code == 204

        # Confirm deleted
        res_check = client.get(f"/scenarios/{sc.id}", headers=api_test_env["headers_a"])
        assert res_check.status_code == 404
        assert res_check.json()["error_code"] == "SCENARIO_NOT_FOUND"


# ---------------------------------------------------------------------------
# 2. Simulation Trigger, Polling & Results Tests
# ---------------------------------------------------------------------------
class TestSimulationEndpoints:
    def test_trigger_simulation_authorization(self, api_test_env):
        client = api_test_env["client"]
        session = api_test_env["session"]
        user_a = api_test_env["user_a"]

        sc = Scenario(
            id=uuid.uuid4(),
            user_id=user_a.id,
            name="User A Scenario",
            site_point="POINT(79.0 30.0)",
            breach_type=BreachType.STRUCTURAL,
            dam_height_m=50.0,
            dam_volume_m3=1000000.0,
        )
        session.add(sc)
        session.commit()

        # Unauthenticated request -> 401 Unauthorized
        res_no_auth = client.post(f"/scenarios/{sc.id}/run")
        assert res_no_auth.status_code == 401

        # User B (cross-user) tries to trigger run on User A's scenario -> 403 Forbidden
        res_cross = client.post(f"/scenarios/{sc.id}/run", headers=api_test_env["headers_b"])
        assert res_cross.status_code == 403

    def test_trigger_simulation_success_and_status_polling(self, api_test_env):
        client = api_test_env["client"]
        session = api_test_env["session"]
        user_a = api_test_env["user_a"]

        sc = Scenario(
            id=uuid.uuid4(),
            user_id=user_a.id,
            name="Simulation Test Site",
            site_point="POINT(79.7333 30.3833)",
            breach_type=BreachType.LANDSLIDE_GLOF,
            dam_height_m=35.0,
            dam_volume_m3=20000000.0,
            simulation_radius_km=25.0,
        )
        session.add(sc)
        session.commit()

        # Trigger run
        res_run = client.post(
            f"/scenarios/{sc.id}/run",
            json={"mode": "full"},
            headers=api_test_env["headers_a"],
        )
        assert res_run.status_code == 202
        run_data = res_run.json()
        assert run_data["scenario_id"] == str(sc.id)
        assert run_data["status"] in ["pending", "running", "succeeded"]

        # Poll status
        res_status = client.get(f"/scenarios/{sc.id}/status", headers=api_test_env["headers_a"])
        assert res_status.status_code == 200
        status_data = res_status.json()
        assert status_data["scenario_id"] == str(sc.id)
        assert "progress_percent" in status_data
        assert status_data["progress_percent"] >= 0

    def test_get_scenario_results(self, api_test_env):
        client = api_test_env["client"]
        session = api_test_env["session"]
        user_a = api_test_env["user_a"]

        sc = Scenario(
            id=uuid.uuid4(),
            user_id=user_a.id,
            name="Results Test Site",
            site_point="POINT(79.7333 30.3833)",
            breach_type=BreachType.LANDSLIDE_GLOF,
            dam_height_m=35.0,
            dam_volume_m3=20000000.0,
        )
        run = SimulationRun(
            id=uuid.uuid4(),
            scenario_id=sc.id,
            status=RunStatus.SUCCEEDED,
            current_stage=PipelineStage.SUMMARY_GENERATION,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        settlement = Settlement(
            id=uuid.uuid4(),
            name="Rini Village",
            location="POINT(79.71 30.48)",
            population=1200,
            district="Chamoli",
            state="Uttarakhand",
        )
        step = FloodResult(
            id=uuid.uuid4(),
            simulation_run_id=run.id,
            time_step_minutes=15,
            flood_extent="MULTIPOLYGON(((79.7 30.4, 79.72 30.4, 79.72 30.42, 79.7 30.42, 79.7 30.4)))",
            max_depth_m=12.4,
        )
        aff = AffectedSettlement(
            id=uuid.uuid4(),
            simulation_run_id=run.id,
            settlement_id=settlement.id,
            arrival_time_minutes=14,
            estimated_depth_m=8.5,
        )
        session.add_all([sc, run, settlement, step, aff])
        session.commit()

        res = client.get(f"/scenarios/{sc.id}/results", headers=api_test_env["headers_a"])
        assert res.status_code == 200
        data = res.json()
        assert data["scenario_id"] == str(sc.id)
        assert data["simulation_run_id"] == str(run.id)
        assert data["status"] == "succeeded"
        assert len(data["time_steps"]) == 1
        assert data["time_steps"][0]["time_step_minutes"] == 15
        assert data["time_steps"][0]["max_depth_m"] == 12.4
        assert "flood_extent" in data["time_steps"][0]

        assert len(data["affected_settlements"]) == 1
        aff_item = data["affected_settlements"][0]
        assert aff_item["name"] == "Rini Village"
        assert aff_item["arrival_time_minutes"] == 14
        assert aff_item["estimated_depth_m"] == 8.5
        assert data["total_affected_settlements"] == 1
        assert data["arrival_time_first_settlement_minutes"] == 14


# ---------------------------------------------------------------------------
# 3. Case Studies Endpoints
# ---------------------------------------------------------------------------
class TestCaseStudyEndpoints:
    def test_list_case_studies_and_get_results(self, api_test_env):
        client = api_test_env["client"]
        session = api_test_env["session"]
        user_a = api_test_env["user_a"]

        sc = Scenario(
            id=uuid.uuid4(),
            user_id=user_a.id,
            name="Rishi Ganga 2021 Benchmark",
            site_point="POINT(79.7333 30.3833)",
            breach_type=BreachType.LANDSLIDE_GLOF,
            dam_height_m=35.0,
            dam_volume_m3=26000000.0,
        )
        run = SimulationRun(
            id=uuid.uuid4(),
            scenario_id=sc.id,
            status=RunStatus.SUCCEEDED,
        )
        cs = CaseStudy(
            id=uuid.uuid4(),
            scenario_id=sc.id,
            simulation_run_id=run.id,
            event_year=2021,
            description="Chamoli rock-ice avalanche and flood",
            source_reference="WRS / CWC 2021 Report",
        )
        settlement = Settlement(
            id=uuid.uuid4(),
            name="Tapovan Project",
            location="POINT(79.62 30.49)",
            population=450,
            district="Chamoli",
            state="Uttarakhand",
        )
        step = FloodResult(
            id=uuid.uuid4(),
            simulation_run_id=run.id,
            time_step_minutes=30,
            flood_extent="MULTIPOLYGON(((79.6 30.4, 79.65 30.4, 79.65 30.45, 79.6 30.45, 79.6 30.4)))",
            max_depth_m=18.2,
        )
        aff = AffectedSettlement(
            id=uuid.uuid4(),
            simulation_run_id=run.id,
            settlement_id=settlement.id,
            arrival_time_minutes=32,
            estimated_depth_m=11.0,
        )
        session.add_all([sc, run, cs, settlement, step, aff])
        session.commit()

        # List case studies
        res_list = client.get("/case-studies")
        assert res_list.status_code == 200
        list_data = res_list.json()
        assert list_data["total"] >= 1
        found = next((item for item in list_data["case_studies"] if item["id"] == str(cs.id)), None)
        assert found is not None
        assert found["name"] == "Rishi Ganga 2021 Benchmark"
        assert found["event_year"] == 2021

        # Get case study results
        res_res = client.get(f"/case-studies/{cs.id}/results")
        assert res_res.status_code == 200
        res_data = res_res.json()
        assert res_data["scenario_id"] == str(sc.id)
        assert len(res_data["time_steps"]) == 1
        assert res_data["time_steps"][0]["max_depth_m"] == 18.2
        assert len(res_data["affected_settlements"]) == 1
        assert res_data["affected_settlements"][0]["name"] == "Tapovan Project"


# ---------------------------------------------------------------------------
# 4. DEM Preview Endpoints
# ---------------------------------------------------------------------------
class TestDEMEndpoints:
    def test_dem_preview_himalayan_site(self, api_test_env):
        client = api_test_env["client"]
        res = client.get("/dem/preview", params={"latitude": 30.3833, "longitude": 79.7333})
        assert res.status_code == 200
        data = res.json()
        assert data["latitude"] == 30.3833
        assert data["longitude"] == 79.7333
        assert data["elevation_m"] > 2000.0  # High Himalayan baseline
        assert data["slope_degrees"] is not None
        assert data["estimated_dam_height_m"] > 0
        assert data["estimated_dam_volume_m3"] > 0
        assert data["coverage_available"] is True
        assert data["resolution_m"] == 30
        assert "is_cached" in data

        # Second request to same bbox should hit cache
        res2 = client.get("/dem/preview", params={"latitude": 30.3833, "longitude": 79.7333})
        assert res2.status_code == 200
        assert res2.json()["is_cached"] is True


# ---------------------------------------------------------------------------
# 5. Report & Data Exports Endpoints
# ---------------------------------------------------------------------------
class TestExportEndpoints:
    def test_create_and_download_json_export(self, api_test_env):
        client = api_test_env["client"]
        session = api_test_env["session"]
        user_a = api_test_env["user_a"]

        sc = Scenario(
            id=uuid.uuid4(),
            user_id=user_a.id,
            name="Exportable Scenario",
            site_point="POINT(79.7333 30.3833)",
            breach_type=BreachType.STRUCTURAL,
            dam_height_m=50.0,
            dam_volume_m3=15000000.0,
        )
        run = SimulationRun(
            id=uuid.uuid4(),
            scenario_id=sc.id,
            status=RunStatus.SUCCEEDED,
        )
        session.add_all([sc, run])
        session.commit()

        # Generate JSON export
        res_exp = client.post(
            f"/scenarios/{sc.id}/export",
            json={"format": "json"},
            headers=api_test_env["headers_a"],
        )
        assert res_exp.status_code == 201
        exp_data = res_exp.json()
        assert exp_data["format"] == "json"
        assert "file_url" in exp_data
        export_id = exp_data["id"]

        # List exports for scenario
        res_list = client.get(f"/scenarios/{sc.id}/exports", headers=api_test_env["headers_a"])
        assert res_list.status_code == 200
        assert len(res_list.json()) == 1

        # Fetch exported report data
        res_data = client.get(f"/exports/{export_id}/data", headers=api_test_env["headers_a"])
        assert res_data.status_code == 200
        report = res_data.json()
        assert "scenario" in report
        assert report["scenario"]["name"] == "Exportable Scenario"

    def test_generate_cap_xml_alert(self, api_test_env):
        client = api_test_env["client"]
        session = api_test_env["session"]
        user_a = api_test_env["user_a"]

        sc = Scenario(
            id=uuid.uuid4(),
            user_id=user_a.id,
            name="Emergency Breach Site",
            site_point="POINT(79.7333 30.3833)",
            breach_type=BreachType.LANDSLIDE_GLOF,
            dam_height_m=35.0,
            dam_volume_m3=20000000.0,
            simulation_radius_km=30.0,
        )
        run = SimulationRun(
            id=uuid.uuid4(),
            scenario_id=sc.id,
            status=RunStatus.SUCCEEDED,
        )
        settlement = Settlement(
            id=uuid.uuid4(),
            name="Rini Village",
            location="POINT(79.71 30.48)",
            population=1200,
            district="Chamoli",
            state="Uttarakhand",
        )
        aff = AffectedSettlement(
            id=uuid.uuid4(),
            simulation_run_id=run.id,
            settlement_id=settlement.id,
            arrival_time_minutes=14,
            estimated_depth_m=8.5,
        )
        session.add_all([sc, run, settlement, aff])
        session.commit()

        res = client.get(f"/scenarios/{sc.id}/alert/cap-xml", headers=api_test_env["headers_a"])
        assert res.status_code == 200
        assert "application/xml" in res.headers["content-type"]
        xml_text = res.text
        assert "<alert" in xml_text
        assert "urn:oasis:names:tc:emergency:cap:1.2" in xml_text
        assert "Rini Village" in xml_text
        assert "Immediate" in xml_text
        assert "Extreme" in xml_text

    def test_delete_scenario_conflict_when_used_by_case_study(self, api_test_env):
        """Deleting a scenario referenced by a historical case study returns HTTP 409 SCENARIO_IN_USE."""
        session = api_test_env["session"]
        client = api_test_env["client"]
        user_a = api_test_env["user_a"]

        sc = Scenario(
            id=uuid.uuid4(),
            user_id=user_a.id,
            name="Rishi Ganga Benchmark Dam",
            site_point="POINT(79.73 30.38)",
            breach_type=BreachType.LANDSLIDE_GLOF,
            dam_height_m=40.0,
            dam_volume_m3=25000000.0,
            simulation_radius_km=35.0,
        )
        run = SimulationRun(
            id=uuid.uuid4(),
            scenario_id=sc.id,
            status=RunStatus.SUCCEEDED,
        )
        cs = CaseStudy(
            id=uuid.uuid4(),
            scenario_id=sc.id,
            simulation_run_id=run.id,
            event_year=2021,
            description="Chamoli 2021 disaster benchmark",
        )
        session.add_all([sc, run, cs])
        session.commit()

        res = client.delete(f"/scenarios/{sc.id}", headers=api_test_env["headers_a"])
        assert res.status_code == 409
        data = res.json()
        assert data["error_code"] == "SCENARIO_IN_USE"
        assert "referenced by benchmark case study" in data["message"]

    def test_export_download_idor_protection(self, api_test_env):
        """User B cannot download export artifacts created by User A (HTTP 403 FORBIDDEN)."""
        session = api_test_env["session"]
        client = api_test_env["client"]
        user_a = api_test_env["user_a"]

        sc = Scenario(
            id=uuid.uuid4(),
            user_id=user_a.id,
            name="Confidential Government Dam",
            site_point="POINT(78.50 30.40)",
            breach_type=BreachType.STRUCTURAL,
            dam_height_m=50.0,
            dam_volume_m3=10000000.0,
            simulation_radius_km=25.0,
        )
        run = SimulationRun(
            id=uuid.uuid4(),
            scenario_id=sc.id,
            status=RunStatus.SUCCEEDED,
        )
        session.add_all([sc, run])
        session.commit()

        # User A creates an export
        create_res = client.post(
            f"/scenarios/{sc.id}/export",
            headers=api_test_env["headers_a"],
            json={"format": "json"},
        )
        assert create_res.status_code == 201
        export_id = create_res.json()["id"]

        # User B attempts to download User A's export dossier
        idor_res = client.get(
            f"/exports/{export_id}/data",
            headers=api_test_env["headers_b"],
        )
        assert idor_res.status_code == 403
        assert idor_res.json()["error_code"] == "FORBIDDEN_EXPORT_ACCESS"

        # User A successfully downloads their own export dossier
        authorized_res = client.get(
            f"/exports/{export_id}/data",
            headers=api_test_env["headers_a"],
        )
        assert authorized_res.status_code == 200

