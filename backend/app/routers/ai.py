"""API router for AI tactical evacuation briefings."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies import get_current_user, get_user_scenario
from backend.app.errors import ConflictError, NotFoundError
from backend.app.models.affected_settlement import AffectedSettlement
from backend.app.models.case_study import CaseStudy
from backend.app.models.enums import RunStatus
from backend.app.models.flood_result import FloodResult
from backend.app.models.scenario import Scenario
from backend.app.models.settlement import Settlement
from backend.app.models.simulation_run import SimulationRun
from backend.app.models.user import User
from backend.app.schemas.ai import AIBriefingRequest, AIBriefingResponse
from backend.app.services.ai_briefing import generate_ai_briefing

logger = logging.getLogger("floodpath.api")

router = APIRouter(tags=["AI Intelligence"])


@router.post(
    "/scenarios/{scenario_id}/ai-briefing",
    response_model=AIBriefingResponse,
    status_code=status.HTTP_200_OK,
)
async def create_scenario_ai_briefing(
    scenario_id: UUID,
    payload: Optional[AIBriefingRequest] = None,
    scenario: Scenario = Depends(get_user_scenario),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIBriefingResponse:
    """Generate an AI tactical evacuation and disaster situation briefing for a completed scenario run."""
    # Find latest simulation run
    latest_run = db.execute(
        select(SimulationRun)
        .where(SimulationRun.scenario_id == scenario.id)
        .order_by(desc(SimulationRun.created_at))
        .limit(1)
    ).scalar_one_or_none()

    if latest_run is None:
        raise NotFoundError(
            message=f"No simulation run found for scenario '{scenario.id}'. Run simulation first.",
            error_code="RUN_NOT_FOUND",
        )

    if latest_run.status != RunStatus.SUCCEEDED:
        raise ConflictError(
            message=(
                f"Simulation run is in '{latest_run.status.value}' state. "
                "AI briefing requires a 'succeeded' simulation run."
            ),
            error_code="SIMULATION_NOT_READY",
        )

    # Fetch peak depth from flood results
    depth_results = db.execute(
        select(FloodResult.max_depth_m)
        .where(FloodResult.simulation_run_id == latest_run.id)
    ).scalars().all()
    valid_depths = [float(d) for d in depth_results if d is not None]
    peak_depth = max(valid_depths) if valid_depths else None

    # Fetch impacted settlements
    affected_rows = db.execute(
        select(AffectedSettlement, Settlement)
        .join(Settlement, AffectedSettlement.settlement_id == Settlement.id)
        .where(AffectedSettlement.simulation_run_id == latest_run.id)
        .order_by(AffectedSettlement.arrival_time_minutes.asc())
    ).all()

    affected_list = [
        {
            "settlement_id": str(aff.settlement_id),
            "name": st.name,
            "district": st.district,
            "state": st.state,
            "population": st.population,
            "arrival_time_minutes": aff.arrival_time_minutes,
            "estimated_depth_m": float(aff.estimated_depth_m) if aff.estimated_depth_m is not None else None,
        }
        for aff, st in affected_rows
    ]

    logger.info(
        f"Operator {current_user.email} requested AI briefing for scenario {scenario.id} "
        f"(affected settlements: {len(affected_list)})"
    )

    briefing = await generate_ai_briefing(
        scenario_id=scenario.id,
        scenario_name=scenario.name,
        breach_type=scenario.breach_type.value,
        dam_height_m=float(scenario.dam_height_m),
        dam_volume_m3=float(scenario.dam_volume_m3),
        simulation_radius_km=float(scenario.simulation_radius_km),
        peak_depth_m=peak_depth,
        affected_settlements=affected_list,
        request_params=payload,
    )

    return briefing


@router.post(
    "/case-studies/{case_study_id}/ai-briefing",
    response_model=AIBriefingResponse,
    status_code=status.HTTP_200_OK,
)
async def create_case_study_ai_briefing(
    case_study_id: UUID,
    payload: Optional[AIBriefingRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIBriefingResponse:
    """Generate an AI tactical evacuation briefing for a historical benchmark case study."""
    case_study = db.execute(
        select(CaseStudy).where(CaseStudy.id == case_study_id)
    ).scalar_one_or_none()

    if case_study is None:
        raise NotFoundError(
            message=f"Case study with ID '{case_study_id}' was not found",
            error_code="CASE_STUDY_NOT_FOUND",
        )

    scenario = db.execute(
        select(Scenario).where(Scenario.id == case_study.scenario_id)
    ).scalar_one_or_none()

    if scenario is None:
        raise NotFoundError(
            message=f"Benchmark scenario for case study '{case_study_id}' was not found",
            error_code="SCENARIO_NOT_FOUND",
        )

    run = db.execute(
        select(SimulationRun).where(SimulationRun.id == case_study.simulation_run_id)
    ).scalar_one_or_none()

    if run is None or run.status != RunStatus.SUCCEEDED:
        raise ConflictError(
            message="Benchmark simulation run is not in 'succeeded' state.",
            error_code="SIMULATION_NOT_READY",
        )

    # Fetch peak depth from flood results
    depth_results = db.execute(
        select(FloodResult.max_depth_m)
        .where(FloodResult.simulation_run_id == run.id)
    ).scalars().all()
    valid_depths = [float(d) for d in depth_results if d is not None]
    peak_depth = max(valid_depths) if valid_depths else None

    # Fetch impacted settlements
    affected_rows = db.execute(
        select(AffectedSettlement, Settlement)
        .join(Settlement, AffectedSettlement.settlement_id == Settlement.id)
        .where(AffectedSettlement.simulation_run_id == run.id)
        .order_by(AffectedSettlement.arrival_time_minutes.asc())
    ).all()

    affected_list = [
        {
            "settlement_id": str(aff.settlement_id),
            "name": st.name,
            "district": st.district,
            "state": st.state,
            "population": st.population,
            "arrival_time_minutes": aff.arrival_time_minutes,
            "estimated_depth_m": float(aff.estimated_depth_m) if aff.estimated_depth_m is not None else None,
        }
        for aff, st in affected_rows
    ]

    logger.info(
        f"Operator {current_user.email} requested AI briefing for case study {case_study_id} "
        f"(affected settlements: {len(affected_list)})"
    )

    briefing = await generate_ai_briefing(
        scenario_id=scenario.id,
        scenario_name=f"{scenario.name} ({case_study.event_year} Benchmark)",
        breach_type=scenario.breach_type.value,
        dam_height_m=float(scenario.dam_height_m),
        dam_volume_m3=float(scenario.dam_volume_m3),
        simulation_radius_km=float(scenario.simulation_radius_km),
        peak_depth_m=peak_depth,
        affected_settlements=affected_list,
        request_params=payload,
    )

    return briefing

