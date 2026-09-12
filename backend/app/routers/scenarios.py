"""Scenarios and Simulation Run Management API Router."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from geoalchemy2.elements import WKTElement
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies import get_current_user, get_user_scenario, require_analyst
from backend.app.errors import ConflictError, NotFoundError
from backend.app.logging import get_request_id
from backend.app.models.affected_settlement import AffectedSettlement
from backend.app.models.case_study import CaseStudy
from backend.app.models.enums import PipelineStage, RunStatus
from backend.app.models.export import Export
from backend.app.models.flood_result import FloodResult
from backend.app.models.scenario import Scenario
from backend.app.models.settlement import Settlement
from backend.app.models.simulation_run import SimulationRun
from backend.app.models.user import User
from backend.app.queue import SimulationJob, get_job_queue
from backend.app.schemas.results import (
    AffectedSettlementItem,
    FloodResultStep,
    ScenarioResultsResponse,
)
from backend.app.schemas.scenarios import (
    ScenarioCreate,
    ScenarioListResponse,
    ScenarioResponse,
    ScenarioUpdate,
)
from backend.app.schemas.simulations import (
    SimulationRunCreate,
    SimulationRunResponse,
    SimulationStatusResponse,
)
from worker.main import process_job

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


def geometry_to_geojson(geom: Any) -> Dict[str, Any]:
    """Convert a GeoAlchemy2 / WKT / WKB geometry to GeoJSON dict."""
    if geom is None:
        return {"type": "MultiPolygon", "coordinates": []}
    if isinstance(geom, dict):
        return geom
    try:
        import shapely.geometry
        from geoalchemy2.shape import to_shape

        shape = to_shape(geom)
        return shapely.geometry.mapping(shape)
    except Exception:
        pass

    try:
        import shapely.geometry
        import shapely.wkt

        wkt_str = str(getattr(geom, "data", geom))
        if ";" in wkt_str:
            wkt_str = wkt_str.split(";", 1)[1]
        shape = shapely.wkt.loads(wkt_str)
        return shapely.geometry.mapping(shape)
    except Exception:
        pass

    return {"type": "MultiPolygon", "coordinates": []}


def format_scenario_response(
    scenario: Scenario, latest_run: Optional[SimulationRun] = None
) -> ScenarioResponse:
    """Format a Scenario ORM instance into ScenarioResponse schema."""
    from worker.run import extract_point_coordinates

    lat, lon = extract_point_coordinates(scenario.site_point)
    return ScenarioResponse(
        id=scenario.id,
        user_id=scenario.user_id,
        name=scenario.name,
        latitude=lat,
        longitude=lon,
        breach_type=scenario.breach_type,
        dam_height_m=float(scenario.dam_height_m),
        dam_volume_m3=float(scenario.dam_volume_m3),
        simulation_radius_km=float(scenario.simulation_radius_km),
        is_dem_estimated=scenario.is_dem_estimated,
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
        latest_run_id=latest_run.id if latest_run else None,
        latest_run_status=latest_run.status if latest_run else None,
    )


def compute_progress_percent(status_val: RunStatus, current_stage: Optional[PipelineStage]) -> int:
    """Derive progress percentage from run status and current stage."""
    if status_val == RunStatus.SUCCEEDED:
        return 100
    if status_val == RunStatus.FAILED:
        return 0
    if status_val == RunStatus.PENDING:
        return 5

    # RUNNING stage breakdown
    if current_stage == PipelineStage.DEM_FETCH:
        return 15
    elif current_stage == PipelineStage.BREACH_ESTIMATION:
        return 35
    elif current_stage == PipelineStage.FLOOD_ROUTING:
        return 70
    elif current_stage == PipelineStage.SUMMARY_GENERATION:
        return 90
    return 10


@router.post("", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
def create_scenario(
    payload: ScenarioCreate,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    """Create a new dam/lake breach simulation scenario."""
    point_geom = WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326)
    scenario = Scenario(
        user_id=current_user.id,
        name=payload.name,
        site_point=point_geom,
        breach_type=payload.breach_type,
        dam_height_m=payload.dam_height_m,
        dam_volume_m3=payload.dam_volume_m3,
        simulation_radius_km=payload.simulation_radius_km,
        is_dem_estimated=payload.is_dem_estimated,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return format_scenario_response(scenario)


@router.get("", response_model=ScenarioListResponse)
def list_scenarios(
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all scenarios created by the authenticated user, ordered by creation date."""
    query = (
        select(Scenario)
        .where(Scenario.user_id == current_user.id)
        .order_by(desc(Scenario.created_at))
    )
    all_scenarios = db.execute(query).scalars().all()
    total = len(all_scenarios)
    page_scenarios = all_scenarios[skip : skip + limit]

    scenario_responses: List[ScenarioResponse] = []
    for sc in page_scenarios:
        latest_run = db.execute(
            select(SimulationRun)
            .where(SimulationRun.scenario_id == sc.id)
            .order_by(desc(SimulationRun.created_at))
            .limit(1)
        ).scalar_one_or_none()
        scenario_responses.append(format_scenario_response(sc, latest_run=latest_run))

    return ScenarioListResponse(scenarios=scenario_responses, total=total)


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario: Scenario = Depends(get_user_scenario),
    db: Session = Depends(get_db),
):
    """Retrieve details of a scenario, enforcing row-level ownership."""
    latest_run = db.execute(
        select(SimulationRun)
        .where(SimulationRun.scenario_id == scenario.id)
        .order_by(desc(SimulationRun.created_at))
        .limit(1)
    ).scalar_one_or_none()
    return format_scenario_response(scenario, latest_run=latest_run)


@router.patch("/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(
    payload: ScenarioUpdate,
    scenario: Scenario = Depends(get_user_scenario),
    db: Session = Depends(get_db),
):
    """Update editable parameters of an existing scenario."""
    if payload.name is not None:
        scenario.name = payload.name
    if payload.simulation_radius_km is not None:
        scenario.simulation_radius_km = payload.simulation_radius_km
    scenario.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(scenario)

    latest_run = db.execute(
        select(SimulationRun)
        .where(SimulationRun.scenario_id == scenario.id)
        .order_by(desc(SimulationRun.created_at))
        .limit(1)
    ).scalar_one_or_none()
    return format_scenario_response(scenario, latest_run=latest_run)


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scenario(
    scenario: Scenario = Depends(get_user_scenario),
    db: Session = Depends(get_db),
):
    """Delete a scenario and cascade deletion to associated runs and artifacts."""
    # Prevent deleting benchmark scenarios referenced by case studies
    case_study = db.execute(
        select(CaseStudy).where(CaseStudy.scenario_id == scenario.id)
    ).scalar_one_or_none()

    if case_study is not None:
        raise ConflictError(
            message=f"Scenario '{scenario.name}' is referenced by benchmark case study '{case_study.id}' and cannot be deleted.",
            error_code="SCENARIO_IN_USE",
        )

    # Explicitly clean up child records for engines without FK cascade (e.g. SQLite tests)
    runs = db.execute(
        select(SimulationRun).where(SimulationRun.scenario_id == scenario.id)
    ).scalars().all()
    for run in runs:
        db.execute(
            AffectedSettlement.__table__.delete().where(AffectedSettlement.simulation_run_id == run.id)
        )
        db.execute(
            FloodResult.__table__.delete().where(FloodResult.simulation_run_id == run.id)
        )
        db.execute(
            Export.__table__.delete().where(Export.simulation_run_id == run.id)
        )
        db.delete(run)

    db.delete(scenario)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{scenario_id}/run", response_model=SimulationRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_simulation_run(
    payload: Optional[SimulationRunCreate] = None,
    scenario: Scenario = Depends(get_user_scenario),
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    """Enqueue a simulation run for the scenario and start worker processing."""
    mode = payload.mode if payload else "full"

    run = SimulationRun(
        scenario_id=scenario.id,
        status=RunStatus.PENDING,
        mode=mode,
        current_stage=PipelineStage.DEM_FETCH,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    job = SimulationJob(
        run_id=run.id,
        scenario_id=scenario.id,
        user_id=current_user.id,
        mode=mode,
        request_id=get_request_id(),
    )

    queue = get_job_queue()
    await queue.enqueue(job)

    # Launch background worker execution for fast single-process & test environments
    asyncio.create_task(process_job(job))

    return run


@router.get("/{scenario_id}/status", response_model=SimulationStatusResponse)
def get_simulation_status(
    scenario: Scenario = Depends(get_user_scenario),
    db: Session = Depends(get_db),
):
    """Poll simulation execution stage, progress percentage, and elapsed runtime."""
    latest_run = db.execute(
        select(SimulationRun)
        .where(SimulationRun.scenario_id == scenario.id)
        .order_by(desc(SimulationRun.created_at))
        .limit(1)
    ).scalar_one_or_none()

    if latest_run is None:
        raise NotFoundError(
            message=f"No simulation runs found for scenario '{scenario.id}'",
            error_code="RUN_NOT_FOUND",
        )

    progress = compute_progress_percent(latest_run.status, latest_run.current_stage)

    elapsed: Optional[float] = None
    if latest_run.started_at is not None:
        start_time = latest_run.started_at
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        end_time = latest_run.completed_at or datetime.now(timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        elapsed = round((end_time - start_time).total_seconds(), 2)

    return SimulationStatusResponse(
        scenario_id=scenario.id,
        run_id=latest_run.id,
        status=latest_run.status,
        mode=latest_run.mode or "full",
        current_stage=latest_run.current_stage,
        error_stage=latest_run.error_stage,
        error_message=latest_run.error_message,
        progress_percent=progress,
        started_at=latest_run.started_at,
        completed_at=latest_run.completed_at,
        elapsed_seconds=elapsed,
    )


@router.get("/{scenario_id}/results", response_model=ScenarioResultsResponse)
def get_scenario_results(
    scenario: Scenario = Depends(get_user_scenario),
    db: Session = Depends(get_db),
):
    """Retrieve full simulation results including time-stepped flood extents and affected settlements."""
    latest_run = db.execute(
        select(SimulationRun)
        .where(SimulationRun.scenario_id == scenario.id)
        .order_by(desc(SimulationRun.created_at))
        .limit(1)
    ).scalar_one_or_none()

    if latest_run is None:
        raise NotFoundError(
            message=f"No simulation runs found for scenario '{scenario.id}'",
            error_code="RUN_NOT_FOUND",
        )

    # Query time-stepped flood extents
    flood_results = db.execute(
        select(FloodResult)
        .where(FloodResult.simulation_run_id == latest_run.id)
        .order_by(FloodResult.time_step_minutes.asc())
    ).scalars().all()

    time_steps = [
        FloodResultStep(
            id=fr.id,
            time_step_minutes=fr.time_step_minutes,
            flood_extent=geometry_to_geojson(fr.flood_extent),
            max_depth_m=float(fr.max_depth_m) if fr.max_depth_m is not None else None,
        )
        for fr in flood_results
    ]

    # Query affected settlements joined with settlement details
    affected_rows = db.execute(
        select(AffectedSettlement, Settlement)
        .join(Settlement, AffectedSettlement.settlement_id == Settlement.id)
        .where(AffectedSettlement.simulation_run_id == latest_run.id)
        .order_by(AffectedSettlement.arrival_time_minutes.asc())
    ).all()

    settlement_items = [
        AffectedSettlementItem(
            settlement_id=aff.settlement_id,
            name=st.name,
            district=st.district,
            state=st.state,
            population=st.population,
            arrival_time_minutes=aff.arrival_time_minutes,
            estimated_depth_m=float(aff.estimated_depth_m) if aff.estimated_depth_m is not None else None,
        )
        for aff, st in affected_rows
    ]

    depths = [ts.max_depth_m for ts in time_steps if ts.max_depth_m is not None]
    peak_depth = max(depths) if depths else None
    first_arrival = settlement_items[0].arrival_time_minutes if settlement_items else None

    is_surr = (latest_run.mode == "fast")
    summary = None
    if is_surr:
        summary = (
            "[⚡ FAST AI SURROGATE MODE - ML Inference]\n"
            "Generated using FloodPath-Surrogate-Himalaya-v1 (~15ms solve, 100x+ speedup)."
        )

    return ScenarioResultsResponse(
        scenario_id=scenario.id,
        simulation_run_id=latest_run.id,
        status=latest_run.status,
        mode=latest_run.mode or "full",
        is_surrogate=is_surr,
        summary_text=summary,
        time_steps=time_steps,
        affected_settlements=settlement_items,
        total_affected_settlements=len(settlement_items),
        peak_depth_m=peak_depth,
        arrival_time_first_settlement_minutes=first_arrival,
    )
