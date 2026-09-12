"""Simulation Results and Scenario Report Exports API Router."""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies import get_current_user, get_user_scenario
from backend.app.errors import ForbiddenError, NotFoundError
from backend.app.models.affected_settlement import AffectedSettlement
from backend.app.models.enums import ExportFormat
from backend.app.models.export import Export
from backend.app.models.flood_result import FloodResult
from backend.app.models.scenario import Scenario
from backend.app.models.settlement import Settlement
from backend.app.models.simulation_run import SimulationRun
from backend.app.models.user import User
from backend.app.routers.scenarios import geometry_to_geojson
from backend.app.schemas.exports import ExportCreateRequest, ExportResponse

router = APIRouter(tags=["Exports"])

EXPORTS_STORAGE_DIR = os.getenv(
    "EXPORTS_STORAGE_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "exports"),
)


def ensure_exports_dir() -> str:
    os.makedirs(EXPORTS_STORAGE_DIR, exist_ok=True)
    return EXPORTS_STORAGE_DIR


@router.post(
    "/scenarios/{scenario_id}/export",
    response_model=ExportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_scenario_export(
    scenario_id: UUID,
    payload: ExportCreateRequest,
    scenario: Scenario = Depends(get_user_scenario),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate and register a downloadable export artifact (PDF / JSON) for a scenario run."""
    latest_run = db.execute(
        select(SimulationRun)
        .where(SimulationRun.scenario_id == scenario.id)
        .order_by(desc(SimulationRun.created_at))
        .limit(1)
    ).scalar_one_or_none()

    if latest_run is None:
        raise NotFoundError(
            message=f"No simulation runs found for scenario '{scenario.id}' to export",
            error_code="RUN_NOT_FOUND",
        )

    export_id = uuid.uuid4()
    format_ext = payload.format.value.lower()
    filename = f"floodpath_report_{scenario.id}_{latest_run.id}_{export_id}.{format_ext}"
    file_url = f"/exports/{filename}"

    # Generate lightweight export file to disk
    storage_dir = ensure_exports_dir()
    file_path = os.path.join(storage_dir, filename)

    if format_ext == "json":
        # Compile complete JSON payload
        flood_results = db.execute(
            select(FloodResult)
            .where(FloodResult.simulation_run_id == latest_run.id)
            .order_by(FloodResult.time_step_minutes.asc())
        ).scalars().all()

        affected_rows = db.execute(
            select(AffectedSettlement, Settlement)
            .join(Settlement, AffectedSettlement.settlement_id == Settlement.id)
            .where(AffectedSettlement.simulation_run_id == latest_run.id)
            .order_by(AffectedSettlement.arrival_time_minutes.asc())
        ).all()

        report_data = {
            "scenario": {
                "id": str(scenario.id),
                "name": scenario.name,
                "latitude": scenario.latitude,
                "longitude": scenario.longitude,
                "breach_type": scenario.breach_type.value,
                "dam_height_m": float(scenario.dam_height_m),
                "dam_volume_m3": float(scenario.dam_volume_m3),
                "simulation_radius_km": float(scenario.simulation_radius_km),
            },
            "run": {
                "id": str(latest_run.id),
                "status": latest_run.status.value,
                "started_at": latest_run.started_at.isoformat() if latest_run.started_at else None,
                "completed_at": latest_run.completed_at.isoformat() if latest_run.completed_at else None,
            },
            "time_steps": [
                {
                    "time_step_minutes": fr.time_step_minutes,
                    "max_depth_m": float(fr.max_depth_m) if fr.max_depth_m is not None else None,
                    "flood_extent": geometry_to_geojson(fr.flood_extent),
                }
                for fr in flood_results
            ],
            "affected_settlements": [
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
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
    else:
        # PDF placeholder / text report stub
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"FloodPath Dam Breach Assessment Report\nScenario: {scenario.name}\nRun: {latest_run.id}\n")

    export_record = Export(
        id=export_id,
        simulation_run_id=latest_run.id,
        user_id=current_user.id,
        file_url=file_url,
        format=payload.format,
    )
    db.add(export_record)
    db.commit()
    db.refresh(export_record)

    return export_record


@router.get("/scenarios/{scenario_id}/exports", response_model=List[ExportResponse])
def list_scenario_exports(
    scenario_id: UUID,
    scenario: Scenario = Depends(get_user_scenario),
    db: Session = Depends(get_db),
):
    """List all export files generated for a specific scenario."""
    runs = db.execute(
        select(SimulationRun.id).where(SimulationRun.scenario_id == scenario.id)
    ).scalars().all()

    if not runs:
        return []

    exports = db.execute(
        select(Export)
        .where(Export.simulation_run_id.in_(runs))
        .order_by(desc(Export.created_at))
    ).scalars().all()

    return exports


@router.get("/exports/{export_id}/data")
def download_export_data(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch stored export report data."""
    export_record = db.execute(
        select(Export).where(Export.id == export_id)
    ).scalar_one_or_none()

    if export_record is None:
        raise NotFoundError(message=f"Export with ID '{export_id}' not found", error_code="EXPORT_NOT_FOUND")

    if export_record.user_id != current_user.id:
        raise ForbiddenError(
            message="You do not have permission to access this export artifact",
            error_code="FORBIDDEN_EXPORT_ACCESS",
        )

    filename = os.path.basename(export_record.file_url)
    storage_dir = ensure_exports_dir()
    file_path = os.path.join(storage_dir, filename)

    if os.path.exists(file_path):
        if export_record.format == ExportFormat.JSON:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return JSONResponse(content=json.load(f))
            except Exception:
                pass
        return FileResponse(file_path, filename=filename)

    return {"message": "Export created", "file_url": export_record.file_url}
