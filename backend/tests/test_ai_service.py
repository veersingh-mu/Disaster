"""Tests for AI Evacuation & Tactical Disaster Briefing Service.

Validates all Technical Requirements:
- Server-side API key handling (keys never exposed)
- Input validation (valid scenario, completed simulation runs)
- Handling of successful AI responses (parsed into structured schema)
- Handling of timeouts (httpx.TimeoutException)
- Handling of API failures (HTTP 500, HTTP 429, HTTP 401)
- Handling of malformed responses (corrupted JSON, missing candidates)
- Fallback operation when no API key is provided
- URL and logging sanitization to prevent leaking secret keys
"""

import json
import uuid
from unittest.mock import AsyncMock, patch

import geoalchemy2.admin.dialects.sqlite as sqlite_admin
import httpx
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

Geometry.bind_expression = lambda self, bindvalue: (
    bindvalue.data if hasattr(bindvalue, "data") else bindvalue
)
Geometry.column_expression = lambda self, col: col
Geometry.result_processor = lambda self, dialect, coltype: lambda value: value


@compiles(Geometry, "sqlite")
def compile_geometry_sqlite(type_, compiler, **kw):
    return "TEXT"


@compiles(WKTElement, "sqlite")
def compile_wkt(el, comp, **kw):
    return comp.process(el.data, **kw) if hasattr(el, "data") else str(el)


@compiles(PG_UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "TEXT"


from sqlalchemy.schema import CreateIndex  # noqa: E402


@compiles(CreateIndex, "sqlite")
def compile_create_index_sqlite(element, compiler, **kw):
    name = getattr(element.element, "name", "") or ""
    if any(k in name for k in ["flood_extent", "site_point", "location"]):
        return "-- skip spatial index in sqlite"
    return compiler.visit_create_index(element, **kw)


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
from backend.app.models.enums import BreachType, RunStatus, UserRole  # noqa: E402
from backend.app.services.ai_briefing import (  # noqa: E402
    _mask_sensitive_query_params,
    generate_ai_briefing,
)


@pytest.fixture
def db_session():
    """Create a fresh in-memory SQLite database for AI service testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """FastAPI TestClient with overridden database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(db_session):
    """Create a test user and return JWT bearer authentication headers."""
    user = User(
        id=uuid.uuid4(),
        email="tactical-officer@floodpath.gov.in",
        password_hash=hash_password("TacticalSecure123!"),
        role=UserRole.ANALYST,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}, user


@pytest.fixture
def seeded_scenario(db_session, auth_headers):
    """Create a valid scenario with completed simulation run and impacted settlements."""
    _, user = auth_headers

    scenario = Scenario(
        id=uuid.uuid4(),
        name="Alaknanda Test Basin",
        site_point="SRID=4326;POINT(79.62 30.50)",
        breach_type=BreachType.LANDSLIDE_GLOF,
        dam_height_m=45.0,
        dam_volume_m3=2_500_000.0,
        simulation_radius_km=30.0,
        user_id=user.id,
    )
    db_session.add(scenario)
    db_session.flush()

    # Create completed simulation run
    run = SimulationRun(
        id=uuid.uuid4(),
        scenario_id=scenario.id,
        status=RunStatus.SUCCEEDED,
    )
    db_session.add(run)
    db_session.flush()

    # Add flood result with max depth
    flood_res = FloodResult(
        id=uuid.uuid4(),
        simulation_run_id=run.id,
        time_step_minutes=30,
        max_depth_m=8.5,
        flood_extent="SRID=4326;MULTIPOLYGON(((79.62 30.50, 79.63 30.50, 79.63 30.51, 79.62 30.50)))",
    )
    db_session.add(flood_res)

    # Add settlement and affected settlement record
    settlement = Settlement(
        id=uuid.uuid4(),
        name="Joshimath Valley Point",
        district="Chamoli",
        state="Uttarakhand",
        location="SRID=4326;POINT(79.56 30.55)",
        population=3800,
    )
    db_session.add(settlement)
    db_session.flush()

    affected = AffectedSettlement(
        simulation_run_id=run.id,
        settlement_id=settlement.id,
        arrival_time_minutes=25,
        estimated_depth_m=6.8,
    )
    db_session.add(affected)
    db_session.commit()

    return scenario, run


# ==============================================================================
# 1. URL & Secret Sanitization Tests
# ==============================================================================

def test_mask_sensitive_query_params():
    """Verify API keys are completely stripped from URL strings."""
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=AIzaSySecretApiKey12345"
    masked = _mask_sensitive_query_params(url)
    assert "AIzaSySecretApiKey12345" not in masked
    assert "key=***REDACTED***" in masked


# ==============================================================================
# 2. Input Validation Tests
# ==============================================================================

def test_ai_briefing_nonexistent_scenario(client, auth_headers):
    """Calling AI briefing for a non-existent scenario returns HTTP 404."""
    headers, _ = auth_headers
    random_id = uuid.uuid4()
    response = client.post(f"/scenarios/{random_id}/ai-briefing", headers=headers)
    assert response.status_code == 404
    assert response.json()["error_code"] in ["SCENARIO_NOT_FOUND", "NOT_FOUND"]


def test_ai_briefing_unrun_scenario(client, auth_headers, db_session):
    """Calling AI briefing for a scenario with no completed runs returns HTTP 404/409."""
    headers, user = auth_headers
    scenario = Scenario(
        id=uuid.uuid4(),
        name="Unrun Scenario",
        site_point="SRID=4326;POINT(79.62 30.50)",
        breach_type=BreachType.LANDSLIDE_GLOF,
        dam_height_m=30.0,
        dam_volume_m3=1_000_000.0,
        simulation_radius_km=25.0,
        user_id=user.id,
    )
    db_session.add(scenario)
    db_session.commit()

    response = client.post(f"/scenarios/{scenario.id}/ai-briefing", headers=headers)
    assert response.status_code == 404
    assert response.json()["error_code"] == "RUN_NOT_FOUND"


def test_ai_briefing_incomplete_run(client, auth_headers, db_session):
    """Calling AI briefing when simulation is running or queued returns HTTP 409 SIMULATION_NOT_READY."""
    headers, user = auth_headers
    scenario = Scenario(
        id=uuid.uuid4(),
        name="In-Progress Scenario",
        site_point="SRID=4326;POINT(79.62 30.50)",
        breach_type=BreachType.LANDSLIDE_GLOF,
        dam_height_m=30.0,
        dam_volume_m3=1_000_000.0,
        simulation_radius_km=25.0,
        user_id=user.id,
    )
    db_session.add(scenario)
    db_session.flush()

    run = SimulationRun(
        id=uuid.uuid4(),
        scenario_id=scenario.id,
        status=RunStatus.RUNNING,
    )
    db_session.add(run)
    db_session.commit()

    response = client.post(f"/scenarios/{scenario.id}/ai-briefing", headers=headers)
    assert response.status_code == 409
    assert response.json()["error_code"] == "SIMULATION_NOT_READY"


# ==============================================================================
# 3. Successful AI Request Tests (Mocked Live Gemini API)
# ==============================================================================

@pytest.mark.asyncio
async def test_ai_briefing_successful_live_gemini(monkeypatch):
    """Verify successful parsing of structured Gemini API response."""
    scenario_id = uuid.uuid4()
    mock_gemini_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "headline": "FLASH FLOOD EMERGENCY: Rapid valley surge underway",
                                "evacuation_urgency": "IMMEDIATE",
                                "executive_summary": "Breach at Test Dam generates high velocity wave front reaching Joshimath in 25 min.",
                                "settlement_timeline": [
                                    {
                                        "settlement_id": str(uuid.uuid4()),
                                        "name": "Joshimath",
                                        "district": "Chamoli",
                                        "state": "Uttarakhand",
                                        "arrival_time_minutes": 25,
                                        "estimated_depth_m": 6.8,
                                        "evacuation_priority": "IMMEDIATE",
                                        "recommended_action": "Evacuate valley floor immediately to contour > 1800m.",
                                    }
                                ],
                                "resource_staging_advisory": [
                                    "Deploy 2 NDRF companies to upper transit point.",
                                    "Close NH-58 riverside road segment.",
                                ],
                                "public_advisory_bulletin": "URGENT EVACUATION ORDER: Move to higher ground now.",
                            })
                        }
                    ]
                }
            }
        ]
    }

    monkeypatch.setenv("GEMINI_API_KEY", "test_mock_gemini_key_12345")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.6-flash")

    mock_response = httpx.Response(
        status_code=200,
        content=json.dumps(mock_gemini_payload).encode("utf-8"),
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        briefing = await generate_ai_briefing(
            scenario_id=scenario_id,
            scenario_name="Rishi Ganga Glacial Lake",
            breach_type="landslide_glof",
            dam_height_m=35.0,
            dam_volume_m3=1_500_000.0,
            simulation_radius_km=30.0,
            peak_depth_m=7.2,
            affected_settlements=[{"name": "Joshimath", "arrival_time_minutes": 25}],
        )

        assert briefing.scenario_id == scenario_id
        assert briefing.evacuation_urgency == "IMMEDIATE"
        assert briefing.is_fallback is False
        assert briefing.model_used == "gemini-3.6-flash"
        assert len(briefing.settlement_timeline) == 1
        assert briefing.settlement_timeline[0].name == "Joshimath"
        assert len(briefing.resource_staging_advisory) == 2


# ==============================================================================
# 4. Failed AI Request Tests (Timeout, HTTP Errors, Malformed Response)
# ==============================================================================

@pytest.mark.asyncio
async def test_ai_briefing_timeout_handling(monkeypatch):
    """Verify that a network timeout gracefully falls back to deterministic rule engine."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_mock_gemini_key_12345")
    scenario_id = uuid.uuid4()

    with patch("httpx.AsyncClient.post", side_effect=httpx.ReadTimeout("Connection timed out")):
        briefing = await generate_ai_briefing(
            scenario_id=scenario_id,
            scenario_name="Tehri Valley Test",
            breach_type="overtopping",
            dam_height_m=50.0,
            dam_volume_m3=5_000_000.0,
            simulation_radius_km=40.0,
            peak_depth_m=9.0,
            affected_settlements=[{"name": "Tehri Downstream", "arrival_time_minutes": 20}],
        )

        assert briefing.scenario_id == scenario_id
        assert briefing.is_fallback is True
        assert "timed out" in briefing.model_used.lower()
        assert briefing.evacuation_urgency == "IMMEDIATE"
        assert len(briefing.settlement_timeline) > 0


@pytest.mark.asyncio
async def test_ai_briefing_http_500_failure(monkeypatch):
    """Verify that an upstream HTTP 500 error from the AI provider falls back cleanly."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_mock_gemini_key_12345")
    scenario_id = uuid.uuid4()

    mock_500_response = httpx.Response(
        status_code=500,
        content=b'{"error": {"code": 500, "message": "Internal AI server error"}}',
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_500_response

        briefing = await generate_ai_briefing(
            scenario_id=scenario_id,
            scenario_name="South Lhonak Surge",
            breach_type="moraine_dam_failure",
            dam_height_m=40.0,
            dam_volume_m3=3_000_000.0,
            simulation_radius_km=25.0,
            peak_depth_m=6.5,
            affected_settlements=[{"name": "Chungthang", "arrival_time_minutes": 45}],
        )

        assert briefing.scenario_id == scenario_id
        assert briefing.is_fallback is True
        assert "status 500" in briefing.model_used.lower()
        assert len(briefing.settlement_timeline) == 1
        assert briefing.settlement_timeline[0].name == "Chungthang"


@pytest.mark.asyncio
async def test_ai_briefing_http_429_rate_limited(monkeypatch):
    """Verify that an upstream HTTP 429 rate limit falls back gracefully."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_mock_gemini_key_12345")
    scenario_id = uuid.uuid4()

    mock_429_response = httpx.Response(
        status_code=429,
        content=b'{"error": {"code": 429, "message": "Rate limit exceeded"}}',
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_429_response

        briefing = await generate_ai_briefing(
            scenario_id=scenario_id,
            scenario_name="Rate Limit Test",
            breach_type="piping",
            dam_height_m=20.0,
            dam_volume_m3=500_000.0,
            simulation_radius_km=15.0,
            peak_depth_m=4.0,
            affected_settlements=[],
        )

        assert briefing.scenario_id == scenario_id
        assert briefing.is_fallback is True
        assert "status 429" in briefing.model_used.lower()


@pytest.mark.asyncio
async def test_ai_briefing_malformed_json(monkeypatch):
    """Verify that malformed/corrupted JSON from upstream AI provider falls back cleanly."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_mock_gemini_key_12345")
    scenario_id = uuid.uuid4()

    mock_malformed_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "This is plain conversational text without valid JSON {...malformed"
                        }
                    ]
                }
            }
        ]
    }

    mock_response = httpx.Response(
        status_code=200,
        content=json.dumps(mock_malformed_payload).encode("utf-8"),
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        briefing = await generate_ai_briefing(
            scenario_id=scenario_id,
            scenario_name="Malformed Output Test",
            breach_type="landslide_glof",
            dam_height_m=30.0,
            dam_volume_m3=1_000_000.0,
            simulation_radius_km=20.0,
            peak_depth_m=5.0,
            affected_settlements=[{"name": "Tapovan", "arrival_time_minutes": 15}],
        )

        assert briefing.scenario_id == scenario_id
        assert briefing.is_fallback is True
        assert "malformed" in briefing.model_used.lower()


# ==============================================================================
# 5. Full End-to-End API Router Verification
# ==============================================================================

def test_api_router_ai_briefing_endpoint(client, auth_headers, seeded_scenario):
    """Complete integration test of POST /scenarios/{id}/ai-briefing via HTTP client."""
    headers, _ = auth_headers
    scenario, _ = seeded_scenario

    response = client.post(
        f"/scenarios/{scenario.id}/ai-briefing",
        headers=headers,
        json={"focus_area": "immediate_evacuation"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["scenario_id"] == str(scenario.id)
    assert data["evacuation_urgency"] in ["IMMEDIATE", "HIGH", "MODERATE", "ADVISORY"]
    assert "headline" in data
    assert "executive_summary" in data
    assert len(data["settlement_timeline"]) > 0
    assert len(data["resource_staging_advisory"]) > 0
    assert "public_advisory_bulletin" in data
    assert "model_used" in data
    assert "test_mock_gemini_key" not in json.dumps(data)


# ==============================================================================
# 6. Authentication & Authorization Failure Tests
# ==============================================================================

def test_ai_briefing_unauthenticated(client, seeded_scenario):
    """Calling AI briefing without credentials returns HTTP 401 UNAUTHORIZED."""
    scenario, _ = seeded_scenario
    response = client.post(f"/scenarios/{scenario.id}/ai-briefing")
    assert response.status_code == 401
    assert response.json()["error_code"] == "UNAUTHORIZED"


def test_ai_briefing_invalid_token(client, seeded_scenario):
    """Calling AI briefing with an invalid token returns HTTP 401 UNAUTHORIZED."""
    scenario, _ = seeded_scenario
    headers = {"Authorization": "Bearer malformed.or.expired.jwt.token"}
    response = client.post(f"/scenarios/{scenario.id}/ai-briefing", headers=headers)
    assert response.status_code == 401
    assert response.json()["error_code"] == "UNAUTHORIZED"


def test_ai_briefing_cross_tenant_forbidden(client, db_session, seeded_scenario):
    """User B cannot generate briefings for User A's private scenario (HTTP 403)."""
    scenario, _ = seeded_scenario

    # Create a separate user B
    user_b = User(
        id=uuid.uuid4(),
        email="unauthorized-analyst@floodpath.gov.in",
        password_hash=hash_password("Pass1234!"),
        role=UserRole.ANALYST,
    )
    db_session.add(user_b)
    db_session.commit()

    token_b = create_access_token(data={"sub": str(user_b.id), "role": user_b.role.value})
    headers_b = {"Authorization": f"Bearer {token_b}"}

    response = client.post(f"/scenarios/{scenario.id}/ai-briefing", headers=headers_b)
    assert response.status_code == 403
    assert response.json()["error_code"] == "FORBIDDEN_SCENARIO_ACCESS"


# ==============================================================================
# 7. Invalid Input & Validation Error Tests
# ==============================================================================

def test_ai_briefing_invalid_uuid_format(client, auth_headers):
    """Passing a non-UUID scenario_id string returns HTTP 422 VALIDATION_ERROR."""
    headers, _ = auth_headers
    response = client.post("/scenarios/not-a-valid-uuid-format/ai-briefing", headers=headers)
    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_ai_briefing_payload_exceeds_max_length(client, auth_headers, seeded_scenario):
    """Passing custom_instructions > 500 characters returns HTTP 422 VALIDATION_ERROR."""
    headers, _ = auth_headers
    scenario, _ = seeded_scenario

    long_instructions = "A" * 501
    response = client.post(
        f"/scenarios/{scenario.id}/ai-briefing",
        headers=headers,
        json={"custom_instructions": long_instructions},
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"


# ==============================================================================
# 8. Empty Input Tests (Empty Body, Zero Affected Settlements)
# ==============================================================================

def test_ai_briefing_empty_json_body(client, auth_headers, seeded_scenario):
    """Passing an empty JSON object `{}` defaults cleanly and returns HTTP 200."""
    headers, _ = auth_headers
    scenario, _ = seeded_scenario

    response = client.post(
        f"/scenarios/{scenario.id}/ai-briefing",
        headers=headers,
        json={},
    )
    assert response.status_code == 200
    assert response.json()["scenario_id"] == str(scenario.id)


def test_ai_briefing_no_body(client, auth_headers, seeded_scenario):
    """Posting with no request body defaults cleanly and returns HTTP 200."""
    headers, _ = auth_headers
    scenario, _ = seeded_scenario

    response = client.post(
        f"/scenarios/{scenario.id}/ai-briefing",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["scenario_id"] == str(scenario.id)


def test_ai_briefing_zero_affected_settlements(client, auth_headers, db_session):
    """A scenario with 0 affected settlements returns HTTP 200 with ADVISORY status."""
    headers, user = auth_headers

    scenario = Scenario(
        id=uuid.uuid4(),
        name="Contained Flood Scenario",
        site_point="SRID=4326;POINT(79.62 30.50)",
        breach_type=BreachType.STRUCTURAL,
        dam_height_m=15.0,
        dam_volume_m3=200_000.0,
        simulation_radius_km=10.0,
        user_id=user.id,
    )
    db_session.add(scenario)
    db_session.flush()

    run = SimulationRun(
        id=uuid.uuid4(),
        scenario_id=scenario.id,
        status=RunStatus.SUCCEEDED,
    )
    db_session.add(run)
    db_session.commit()

    response = client.post(f"/scenarios/{scenario.id}/ai-briefing", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["evacuation_urgency"] == "ADVISORY"
    assert len(data["settlement_timeline"]) == 0
    assert "no direct settlement impact" in data["headline"].lower() or "monitoring" in data["headline"].lower()


# ==============================================================================
# 9. Upstream AI Failures (HTTP 401, Empty Candidates)
# ==============================================================================

@pytest.mark.asyncio
async def test_ai_briefing_http_401_invalid_key(monkeypatch):
    """An upstream HTTP 401 (invalid/revoked API key) falls back cleanly to deterministic engine."""
    monkeypatch.setenv("GEMINI_API_KEY", "revoked_or_invalid_key")
    scenario_id = uuid.uuid4()

    mock_401_response = httpx.Response(
        status_code=401,
        content=b'{"error": {"code": 401, "message": "API key not valid. Please pass a valid API key."}}',
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_401_response

        briefing = await generate_ai_briefing(
            scenario_id=scenario_id,
            scenario_name="Security Auth Test Dam",
            breach_type="overtopping",
            dam_height_m=25.0,
            dam_volume_m3=800_000.0,
            simulation_radius_km=15.0,
            peak_depth_m=3.5,
            affected_settlements=[{"name": "Downstream Hamlet", "arrival_time_minutes": 50}],
        )

        assert briefing.scenario_id == scenario_id
        assert briefing.is_fallback is True
        assert "status 401" in briefing.model_used.lower()
        assert len(briefing.settlement_timeline) == 1


@pytest.mark.asyncio
async def test_ai_briefing_empty_candidates_fallback(monkeypatch):
    """An upstream response with empty candidates array falls back cleanly."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock_key")
    scenario_id = uuid.uuid4()

    mock_empty_resp = httpx.Response(
        status_code=200,
        content=b'{"candidates": []}',
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_empty_resp

        briefing = await generate_ai_briefing(
            scenario_id=scenario_id,
            scenario_name="Empty Candidate Test",
            breach_type="piping",
            dam_height_m=20.0,
            dam_volume_m3=500_000.0,
            simulation_radius_km=10.0,
            peak_depth_m=2.5,
            affected_settlements=[],
        )

        assert briefing.is_fallback is True
        assert "empty candidate" in briefing.model_used.lower()


# ==============================================================================
# 10. Database Failure & Exception Handling Tests
# ==============================================================================

def test_ai_briefing_database_failure_handling(client, auth_headers, seeded_scenario):
    """Database exception during scenario run query is caught safely without leaking secrets."""
    headers, _ = auth_headers
    scenario, _ = seeded_scenario

    with TestClient(app, raise_server_exceptions=False) as safe_client:
        with patch("backend.app.routers.ai.generate_ai_briefing", side_effect=Exception("Simulated database connection pool exhaustion")):
            response = safe_client.post(f"/scenarios/{scenario.id}/ai-briefing", headers=headers)
            assert response.status_code == 500
            data = response.json()
            assert data["error_code"] == "INTERNAL_SERVER_ERROR"
            assert "password" not in json.dumps(data).lower()
            assert "secret" not in json.dumps(data).lower()


# ==============================================================================
# 11. Edge Cases (Failed Run, Null Peak Depth, Non-UUID Settlement ID)
# ==============================================================================

def test_ai_briefing_failed_simulation_run(client, auth_headers, db_session):
    """Calling AI briefing for a simulation that ended in 'failed' status returns HTTP 409."""
    headers, user = auth_headers

    scenario = Scenario(
        id=uuid.uuid4(),
        name="Failed Run Scenario",
        site_point="SRID=4326;POINT(79.62 30.50)",
        breach_type=BreachType.LANDSLIDE_GLOF,
        dam_height_m=35.0,
        dam_volume_m3=1_200_000.0,
        simulation_radius_km=20.0,
        user_id=user.id,
    )
    db_session.add(scenario)
    db_session.flush()

    run = SimulationRun(
        id=uuid.uuid4(),
        scenario_id=scenario.id,
        status=RunStatus.FAILED,
    )
    db_session.add(run)
    db_session.commit()

    response = client.post(f"/scenarios/{scenario.id}/ai-briefing", headers=headers)
    assert response.status_code == 409
    assert response.json()["error_code"] == "SIMULATION_NOT_READY"


def test_ai_briefing_missing_peak_depth(client, auth_headers, db_session):
    """Simulation run with no max_depth_m records succeeds with safe default depth."""
    headers, user = auth_headers

    scenario = Scenario(
        id=uuid.uuid4(),
        name="No Depth Records Scenario",
        site_point="SRID=4326;POINT(79.62 30.50)",
        breach_type=BreachType.STRUCTURAL,
        dam_height_m=20.0,
        dam_volume_m3=500_000.0,
        simulation_radius_km=15.0,
        user_id=user.id,
    )
    db_session.add(scenario)
    db_session.flush()

    run = SimulationRun(
        id=uuid.uuid4(),
        scenario_id=scenario.id,
        status=RunStatus.SUCCEEDED,
    )
    db_session.add(run)
    db_session.commit()

    response = client.post(f"/scenarios/{scenario.id}/ai-briefing", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["evacuation_urgency"] == "ADVISORY"


def test_ai_briefing_non_uuid_settlement_id_graceful_handling():
    """Settlement items with string or non-UUID ids parse gracefully without crashing."""
    from backend.app.services.ai_briefing import generate_expert_fallback_briefing

    scenario_id = uuid.uuid4()
    briefing = generate_expert_fallback_briefing(
        scenario_id=scenario_id,
        scenario_name="Robust ID Parsing Scenario",
        breach_type="structural",
        dam_height_m=20.0,
        dam_volume_m3=500_000.0,
        peak_depth_m=4.5,
        affected_settlements=[
            {"settlement_id": "non-uuid-village-string-123", "name": "Settlement Alpha", "arrival_time_minutes": 20},
            {"settlement_id": None, "name": "Settlement Beta", "arrival_time_minutes": 60},
        ],
    )

    assert len(briefing.settlement_timeline) == 2
    assert isinstance(briefing.settlement_timeline[0].settlement_id, uuid.UUID)
    assert isinstance(briefing.settlement_timeline[1].settlement_id, uuid.UUID)
    assert briefing.settlement_timeline[0].name == "Settlement Alpha"


# ==============================================================================
# 12. Historical Benchmark Case Study AI Briefing Tests
# ==============================================================================

def test_case_study_ai_briefing_success(client, auth_headers, db_session):
    """Generating an AI briefing for a historical benchmark case study returns HTTP 200."""
    headers, user = auth_headers

    scenario = Scenario(
        id=uuid.uuid4(),
        name="Rishi Ganga Historical Benchmark",
        site_point="SRID=4326;POINT(79.71 30.48)",
        breach_type=BreachType.LANDSLIDE_GLOF,
        dam_height_m=40.0,
        dam_volume_m3=1_800_000.0,
        simulation_radius_km=35.0,
        user_id=user.id,
    )
    db_session.add(scenario)
    db_session.flush()

    run = SimulationRun(
        id=uuid.uuid4(),
        scenario_id=scenario.id,
        status=RunStatus.SUCCEEDED,
    )
    db_session.add(run)
    db_session.flush()

    case_study = CaseStudy(
        id=uuid.uuid4(),
        scenario_id=scenario.id,
        simulation_run_id=run.id,
        event_year=2021,
        description="Chamoli 2021 GLOF disaster benchmark",
    )
    db_session.add(case_study)
    db_session.commit()

    response = client.post(f"/case-studies/{case_study.id}/ai-briefing", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["scenario_id"] == str(scenario.id)
    assert "2021 Benchmark" in data["headline"] or "2021 Benchmark" in data["executive_summary"]


def test_case_study_ai_briefing_not_found(client, auth_headers):
    """Calling AI briefing for a non-existent case study returns HTTP 404 CASE_STUDY_NOT_FOUND."""
    headers, _ = auth_headers
    non_existent = uuid.uuid4()
    response = client.post(f"/case-studies/{non_existent}/ai-briefing", headers=headers)
    assert response.status_code == 404
    assert response.json()["error_code"] == "CASE_STUDY_NOT_FOUND"
