"""Historical Case Studies API Router."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.errors import NotFoundError
from backend.app.models.affected_settlement import AffectedSettlement
from backend.app.models.case_study import CaseStudy
from backend.app.models.enums import RunStatus
from backend.app.models.flood_result import FloodResult
from backend.app.models.scenario import Scenario
from backend.app.models.settlement import Settlement
from backend.app.models.simulation_run import SimulationRun
from backend.app.routers.scenarios import geometry_to_geojson
from backend.app.schemas.case_studies import CaseStudyListResponse, CaseStudyResponse
from backend.app.schemas.results import (
    AffectedSettlementItem,
    FloodResultStep,
    ScenarioResultsResponse,
)

router = APIRouter(prefix="/case-studies", tags=["Case Studies"])


@router.get("", response_model=CaseStudyListResponse)
def list_case_studies(db: Session = Depends(get_db)):
    """List all available pre-validated historical disaster case studies."""
    rows = db.execute(
        select(CaseStudy, Scenario).join(Scenario, CaseStudy.scenario_id == Scenario.id)
    ).all()

    items: List[CaseStudyResponse] = []
    for cs, sc in rows:
        items.append(
            CaseStudyResponse(
                id=cs.id,
                scenario_id=cs.scenario_id,
                simulation_run_id=cs.simulation_run_id,
                event_year=cs.event_year,
                description=cs.description,
                source_reference=cs.source_reference,
                created_at=cs.created_at,
                name=sc.name,
                breach_type=sc.breach_type,
                dam_height_m=float(sc.dam_height_m),
                dam_volume_m3=float(sc.dam_volume_m3),
                simulation_radius_km=float(sc.simulation_radius_km),
                latitude=sc.latitude,
                longitude=sc.longitude,
            )
        )

    return CaseStudyListResponse(case_studies=items, total=len(items))


@router.get("/{case_study_id}/results", response_model=ScenarioResultsResponse)
def get_case_study_results(case_study_id: UUID, db: Session = Depends(get_db)):
    """Retrieve pre-computed results for a historical benchmark case study."""
    case_study = db.execute(
        select(CaseStudy).where(CaseStudy.id == case_study_id)
    ).scalar_one_or_none()

    if case_study is None:
        raise NotFoundError(
            message=f"Case study with ID '{case_study_id}' was not found",
            error_code="CASE_STUDY_NOT_FOUND",
        )

    run = db.execute(
        select(SimulationRun).where(SimulationRun.id == case_study.simulation_run_id)
    ).scalar_one_or_none()

    status_val = run.status if run else RunStatus.SUCCEEDED

    # Fetch time-stepped flood extent polygons
    flood_results = db.execute(
        select(FloodResult)
        .where(FloodResult.simulation_run_id == case_study.simulation_run_id)
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

    # Fetch affected settlements joined with settlement details
    affected_rows = db.execute(
        select(AffectedSettlement, Settlement)
        .join(Settlement, AffectedSettlement.settlement_id == Settlement.id)
        .where(AffectedSettlement.simulation_run_id == case_study.simulation_run_id)
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

    return ScenarioResultsResponse(
        scenario_id=case_study.scenario_id,
        simulation_run_id=case_study.simulation_run_id,
        status=status_val,
        time_steps=time_steps,
        affected_settlements=settlement_items,
        total_affected_settlements=len(settlement_items),
        peak_depth_m=peak_depth,
        arrival_time_first_settlement_minutes=first_arrival,
    )
