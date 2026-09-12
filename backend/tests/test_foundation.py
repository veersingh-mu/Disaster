"""Tests for Phase 4: Backend Foundation.

Covers:
1. Pydantic request/response validation boundary tests
2. Standardized structured error responses (422, 404, 403, 500)
3. Structured JSON logging with request ID tracking
4. Row-level ownership authorization dependency
5. Simulation job queue enqueuing and worker processing smoke test
"""

import json
import logging
import os
import sys
import uuid

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
for p in [BASE_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.dependencies import get_user_scenario  # noqa: E402
from backend.app.errors import (  # noqa: E402
    ForbiddenError,
    NotFoundError,
    register_exception_handlers,
)
from backend.app.logging import (  # noqa: E402
    JSONFormatter,
    RequestIdLoggingMiddleware,
    request_id_ctx_var,
)
from backend.app.main import app  # noqa: E402
from backend.app.models import Base, Scenario, User  # noqa: E402
from backend.app.models.enums import (  # noqa: E402
    BreachType,
    ExportFormat,
    PipelineStage,
    RunStatus,
    UserRole,
)
from backend.app.queue import AsyncInMemoryJobQueue, SimulationJob  # noqa: E402
from backend.app.schemas import (  # noqa: E402
    Coordinates,
    DEMPreviewRequest,
    ExportCreateRequest,
    ScenarioCreate,
)
from worker.main import process_job  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Pydantic Boundary Validation Tests
# ---------------------------------------------------------------------------
class TestSchemaBoundaries:
    def test_scenario_create_valid(self):
        payload = {
            "name": "Tehri Dam High Risk",
            "latitude": 30.3783,
            "longitude": 78.4803,
            "breach_type": "structural",
            "dam_height_m": 260.5,
            "dam_volume_m3": 4000000000.0,
            "simulation_radius_km": 50.0,
            "is_dem_estimated": False,
        }
        obj = ScenarioCreate(**payload)
        assert obj.name == "Tehri Dam High Risk"
        assert obj.latitude == 30.3783
        assert obj.breach_type == BreachType.STRUCTURAL
        assert obj.dam_height_m == 260.5

    def test_scenario_create_latitude_bounds(self):
        base = {
            "name": "Test Site",
            "longitude": 78.0,
            "breach_type": "structural",
            "dam_height_m": 10.0,
            "dam_volume_m3": 1000.0,
        }
        # Below -90
        with pytest.raises(PydanticValidationError) as exc:
            ScenarioCreate(latitude=-90.1, **base)
        assert "latitude" in str(exc.value).lower()

        # Above 90
        with pytest.raises(PydanticValidationError) as exc:
            ScenarioCreate(latitude=90.1, **base)
        assert "latitude" in str(exc.value).lower()

    def test_scenario_create_longitude_bounds(self):
        base = {
            "name": "Test Site",
            "latitude": 30.0,
            "breach_type": "structural",
            "dam_height_m": 10.0,
            "dam_volume_m3": 1000.0,
        }
        with pytest.raises(PydanticValidationError) as exc:
            ScenarioCreate(longitude=-180.1, **base)
        assert "longitude" in str(exc.value).lower()

        with pytest.raises(PydanticValidationError) as exc:
            ScenarioCreate(longitude=180.1, **base)
        assert "longitude" in str(exc.value).lower()

    def test_scenario_create_dam_height_must_be_positive(self):
        base = {
            "name": "Test Site",
            "latitude": 30.0,
            "longitude": 78.0,
            "breach_type": "structural",
            "dam_volume_m3": 1000.0,
        }
        # Zero height rejected
        with pytest.raises(PydanticValidationError):
            ScenarioCreate(dam_height_m=0.0, **base)

        # Negative height rejected
        with pytest.raises(PydanticValidationError):
            ScenarioCreate(dam_height_m=-5.0, **base)

    def test_scenario_create_dam_volume_must_be_positive(self):
        base = {
            "name": "Test Site",
            "latitude": 30.0,
            "longitude": 78.0,
            "breach_type": "structural",
            "dam_height_m": 25.0,
        }
        # Zero volume rejected
        with pytest.raises(PydanticValidationError):
            ScenarioCreate(dam_volume_m3=0.0, **base)

        # Negative volume rejected
        with pytest.raises(PydanticValidationError):
            ScenarioCreate(dam_volume_m3=-100.0, **base)

    def test_scenario_create_empty_name_rejected(self):
        base = {
            "latitude": 30.0,
            "longitude": 78.0,
            "breach_type": "structural",
            "dam_height_m": 25.0,
            "dam_volume_m3": 1000.0,
        }
        with pytest.raises(PydanticValidationError):
            ScenarioCreate(name="   ", **base)

    def test_scenario_create_invalid_breach_type(self):
        base = {
            "name": "Test Site",
            "latitude": 30.0,
            "longitude": 78.0,
            "dam_height_m": 25.0,
            "dam_volume_m3": 1000.0,
        }
        with pytest.raises(PydanticValidationError):
            ScenarioCreate(breach_type="nuclear_blast", **base)

    def test_coordinates_wkt_format(self):
        coord = Coordinates(latitude=30.3783, longitude=78.4803)
        assert coord.to_wkt() == "POINT(78.4803 30.3783)"

    def test_dem_preview_request_validation(self):
        req = DEMPreviewRequest(latitude=30.0, longitude=78.0)
        assert req.simulation_radius_km == 25.0

        with pytest.raises(PydanticValidationError):
            DEMPreviewRequest(latitude=100.0, longitude=78.0)

    def test_export_create_request_validation(self):
        req = ExportCreateRequest(format=ExportFormat.JSON)
        assert req.format == ExportFormat.JSON

        with pytest.raises(PydanticValidationError):
            ExportCreateRequest(format="mp4")


# ---------------------------------------------------------------------------
# 2. Structured Error Handling Tests
# ---------------------------------------------------------------------------
class TestStructuredErrorHandling:
    @pytest.fixture
    def error_client(self):
        test_app = FastAPI()
        register_exception_handlers(test_app)
        test_app.add_middleware(RequestIdLoggingMiddleware)

        router = APIRouter()

        @router.post("/test/validate")
        def route_validate(scenario: ScenarioCreate):
            return {"status": "ok", "name": scenario.name}

        @router.get("/test/not-found")
        def route_not_found():
            raise NotFoundError(message="Requested scenario does not exist", error_code="SCENARIO_NOT_FOUND")

        @router.get("/test/forbidden")
        def route_forbidden():
            raise ForbiddenError(message="Cannot access another user's scenario", error_code="FORBIDDEN_SCENARIO_ACCESS")

        @router.get("/test/crash")
        def route_crash():
            raise RuntimeError("Unexpected simulated hardware fault")

        test_app.include_router(router)
        return TestClient(test_app, raise_server_exceptions=False)

    def test_validation_error_returns_structured_422(self, error_client):
        # Missing required fields and negative dam height
        response = error_client.post(
            "/test/validate",
            json={"name": "Bad Dam", "dam_height_m": -10},
        )
        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "message" in data
        assert isinstance(data["details"], list)
        assert len(data["details"]) > 0

    def test_not_found_error_returns_structured_404(self, error_client):
        response = error_client.get("/test/not-found")
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "SCENARIO_NOT_FOUND"
        assert data["message"] == "Requested scenario does not exist"

    def test_forbidden_error_returns_structured_403(self, error_client):
        response = error_client.get("/test/forbidden")
        assert response.status_code == 403
        data = response.json()
        assert data["error_code"] == "FORBIDDEN_SCENARIO_ACCESS"
        assert data["message"] == "Cannot access another user's scenario"

    def test_unhandled_crash_returns_structured_500(self, error_client):
        response = error_client.get("/test/crash")
        assert response.status_code == 500
        data = response.json()
        assert data["error_code"] == "INTERNAL_SERVER_ERROR"
        assert "unexpected" in data["message"].lower()


# ---------------------------------------------------------------------------
# 3. Request ID & Logging Tests
# ---------------------------------------------------------------------------
class TestRequestIdAndLogging:
    def test_request_id_assigned_automatically(self):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        req_id = response.headers["X-Request-ID"]
        assert len(req_id) > 10

    def test_request_id_preserved_from_client_header(self):
        client = TestClient(app)
        custom_id = "sih-demo-req-9999"
        response = client.get("/health", headers={"X-Request-ID": custom_id})
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == custom_id

    def test_json_formatter_structure(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="floodpath.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="Breach calculation completed",
            args=(),
            exc_info=None,
        )
        token = request_id_ctx_var.set("test-request-uuid")
        try:
            output = formatter.format(record)
            data = json.loads(output)
            assert data["level"] == "INFO"
            assert data["message"] == "Breach calculation completed"
            assert data["request_id"] == "test-request-uuid"
            assert "timestamp" in data
        finally:
            request_id_ctx_var.reset(token)


# ---------------------------------------------------------------------------
# 4. Row-Level Ownership Authorization Tests
# ---------------------------------------------------------------------------
class TestRowLevelOwnership:
    @pytest.fixture
    def mock_db_session(self):
        import geoalchemy2.admin.dialects.sqlite as sqlite_admin
        from geoalchemy2 import Geometry
        from geoalchemy2.elements import WKTElement
        from sqlalchemy.dialects.postgresql import UUID as PG_UUID
        from sqlalchemy.ext.compiler import compiles
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
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        user_a = User(
            id=uuid.uuid4(),
            email="analyst.a@floodpath.internal",
            password_hash="hash",
            role=UserRole.ANALYST,
        )
        user_b = User(
            id=uuid.uuid4(),
            email="analyst.b@floodpath.internal",
            password_hash="hash",
            role=UserRole.ANALYST,
        )
        session.add_all([user_a, user_b])
        session.commit()

        scenario_a = Scenario(
            id=uuid.uuid4(),
            user_id=user_a.id,
            name="Scenario belonging to User A",
            site_point="POINT(78.0 30.0)",
            breach_type=BreachType.STRUCTURAL,
            dam_height_m=50.0,
            dam_volume_m3=100000.0,
            simulation_radius_km=25.0,
        )
        session.add(scenario_a)
        session.commit()

        try:
            yield {
                "session": session,
                "user_a": user_a,
                "user_b": user_b,
                "scenario_a": scenario_a,
            }
        finally:
            session.close()
            Geometry.bind_expression = orig_bind
            Geometry.column_expression = orig_col
            Geometry.result_processor = orig_res

    def test_owner_can_access_own_scenario(self, mock_db_session):
        session = mock_db_session["session"]
        user_a = mock_db_session["user_a"]
        scenario_a = mock_db_session["scenario_a"]

        retrieved = get_user_scenario(
            scenario_id=scenario_a.id,
            current_user=user_a,
            db=session,
        )
        assert retrieved.id == scenario_a.id
        assert retrieved.name == "Scenario belonging to User A"

    def test_other_user_forbidden_from_accessing_scenario(self, mock_db_session):
        session = mock_db_session["session"]
        user_b = mock_db_session["user_b"]
        scenario_a = mock_db_session["scenario_a"]

        with pytest.raises(ForbiddenError) as exc:
            get_user_scenario(
                scenario_id=scenario_a.id,
                current_user=user_b,
                db=session,
            )
        assert exc.value.error_code == "FORBIDDEN_SCENARIO_ACCESS"
        assert exc.value.status_code == 403

    def test_nonexistent_scenario_raises_404(self, mock_db_session):
        session = mock_db_session["session"]
        user_a = mock_db_session["user_a"]
        random_id = uuid.uuid4()

        with pytest.raises(NotFoundError) as exc:
            get_user_scenario(
                scenario_id=random_id,
                current_user=user_a,
                db=session,
            )
        assert exc.value.error_code == "SCENARIO_NOT_FOUND"
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# 5. Async Simulation Job Queue & Worker Smoke Test
# ---------------------------------------------------------------------------
class TestJobQueueAndWorker:
    @pytest.mark.asyncio
    async def test_queue_enqueue_dequeue(self):
        queue = AsyncInMemoryJobQueue()
        assert queue.is_empty() is True
        assert queue.qsize() == 0

        job = SimulationJob(
            run_id=uuid.uuid4(),
            scenario_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            mode="full",
            request_id="req-test-123",
        )

        await queue.enqueue(job)
        assert queue.is_empty() is False
        assert queue.qsize() == 1

        dequeued = await queue.dequeue(timeout=1.0)
        assert dequeued is not None
        assert dequeued.run_id == job.run_id
        assert dequeued.request_id == "req-test-123"
        assert queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_worker_processes_job_successfully(self):
        job = SimulationJob(
            run_id=uuid.uuid4(),
            scenario_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            mode="full",
            request_id="trace-worker-job-test",
        )

        result = await process_job(job)
        assert result["run_id"] == job.run_id
        assert result["status"] == RunStatus.SUCCEEDED
        assert result["completed_stage"] == PipelineStage.SUMMARY_GENERATION
