"""Unit and Integration Tests for ML Surrogate Inundation Model."""

from uuid import uuid4

from geoalchemy2.elements import WKTElement

from backend.app.models.enums import BreachType, RunStatus
from backend.app.models.scenario import Scenario
from backend.app.models.settlement import Settlement
from backend.app.models.simulation_run import SimulationRun
from backend.tests.test_api_endpoints import api_test_env  # noqa: F401
from worker.ml.surrogate import MLSurrogateModel
from worker.run import run_simulation_pipeline


def test_ml_surrogate_model_unit():
    """Verify ML surrogate model provides fast, realistic predictions."""
    model = MLSurrogateModel()

    # Breach prediction checks
    breach = model.predict_breach(dam_height_m=50.0, dam_volume_m3=2000000.0, breach_type="glacial_lake_outburst")
    assert breach.peak_discharge_m3s > 500.0
    assert breach.breach_width_m > 20.0
    assert breach.breach_formation_time_hours > 0.05
    assert breach.breach_bottom_width_m > 10.0

    settlements = [
        {
            "id": uuid4(),
            "name": "Raini",
            "district": "Chamoli",
            "state": "Uttarakhand",
            "population": 250,
            "latitude": 30.485,
            "longitude": 79.695,
        },
        {
            "id": uuid4(),
            "name": "Tapovan",
            "district": "Chamoli",
            "state": "Uttarakhand",
            "population": 900,
            "latitude": 30.495,
            "longitude": 79.625,
        },
    ]

    result = model.predict(
        dam_height_m=50.0,
        dam_volume_m3=2000000.0,
        breach_type="glacial_lake_outburst",
        origin_lat=30.3833,
        origin_lon=79.7333,
        simulation_radius_km=45.0,
        settlements_list=settlements,
    )

    assert result.breach_params.peak_discharge_m3s > 0
    assert len(result.time_steps) == 10
    assert result.time_steps[0].time_step_minutes == 0
    assert result.time_steps[-1].time_step_minutes == 330
    assert result.telemetry.solve_mode == "fast_surrogate"
    assert result.telemetry.inference_time_ms < 100.0  # Must be sub-100ms
    assert len(result.time_steps[0].polygon_coordinates) > 0
    assert "MULTIPOLYGON" in result.time_steps[0].wkt_geometry


def test_surrogate_pipeline_execution(api_test_env):  # noqa: F811
    """Test worker pipeline execution in fast surrogate mode with database persistence."""
    session = api_test_env["session"]
    user = api_test_env["user_a"]

    scenario = Scenario(
        user_id=user.id,
        name="Surrogate Test Lake",
        site_point=WKTElement("POINT(79.7333 30.3833)", srid=4326),
        breach_type=BreachType.LANDSLIDE_GLOF,
        dam_height_m=45.0,
        dam_volume_m3=1800000.0,
        simulation_radius_km=30.0,
    )
    session.add(scenario)
    session.flush()

    settlement = Settlement(
        name="Surrogate Test Village",
        district="Chamoli",
        state="Uttarakhand",
        location=WKTElement("POINT(79.65 30.45)", srid=4326),
        population=450,
    )
    session.add(settlement)
    session.flush()

    run = SimulationRun(
        scenario_id=scenario.id,
        status=RunStatus.PENDING,
        mode="fast",
    )
    session.add(run)
    session.commit()

    output = run_simulation_pipeline(
        session=session,
        run_id=run.id,
        scenario_id=scenario.id,
        mode="fast",
    )

    assert output["status"] == RunStatus.SUCCEEDED
    assert output["mode"] == "fast"
    assert output["is_surrogate"] is True
    assert output["total_duration_s"] < 2.0  # extremely fast execution

    # Verify run record in DB
    session.refresh(run)
    assert run.status == RunStatus.SUCCEEDED
    assert run.mode == "fast"
    assert run.completed_at is not None


def test_api_fast_surrogate_run_and_results(api_test_env):  # noqa: F811
    """Test full API lifecycle with mode='fast'."""
    client = api_test_env["client"]
    token = api_test_env["token_a"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create scenario
    create_resp = client.post(
        "/scenarios",
        json={
            "name": "Rapid What-If Test Scenario",
            "latitude": 30.3833,
            "longitude": 79.7333,
            "breach_type": "structural",
            "dam_height_m": 40.0,
            "dam_volume_m3": 1500000.0,
            "simulation_radius_km": 25.0,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    sc_id = create_resp.json()["id"]

    # 2. Trigger run in fast mode
    run_resp = client.post(
        f"/scenarios/{sc_id}/run",
        json={"mode": "fast"},
        headers=headers,
    )
    assert run_resp.status_code == 202
    run_data = run_resp.json()
    assert run_data["mode"] == "fast"

    # In single-process test environment, run simulation synchronously on session
    session = api_test_env["session"]
    run_simulation_pipeline(
        session=session,
        run_id=run_data["id"],
        scenario_id=sc_id,
        mode="fast",
    )

    # 3. Check status
    status_resp = client.get(
        f"/scenarios/{sc_id}/status",
        headers=headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["mode"] == "fast"

    # 4. Check results endpoint
    results_resp = client.get(
        f"/scenarios/{sc_id}/results",
        headers=headers,
    )
    assert results_resp.status_code == 200
    res_data = results_resp.json()
    assert res_data["mode"] == "fast"
    assert res_data["is_surrogate"] is True
    assert len(res_data["time_steps"]) > 0
    assert res_data["summary_text"] is not None
