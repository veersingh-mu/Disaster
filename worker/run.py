"""Simulation pipeline execution and database persistence runner."""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.affected_settlement import AffectedSettlement
from backend.app.models.enums import PipelineStage, RunStatus
from backend.app.models.flood_result import FloodResult
from backend.app.models.scenario import Scenario
from backend.app.models.settlement import Settlement
from backend.app.models.simulation_run import SimulationRun
from backend.app.utils.geo import extract_point_coordinates
from worker.ml.surrogate import MLSurrogateModel
from worker.pipeline.breach import calculate_breach_parameters
from worker.pipeline.dem import fetch_dem_profile
from worker.pipeline.impact import assess_settlement_impacts, generate_plain_language_summary
from worker.pipeline.routing import simulate_flood_routing

logger = logging.getLogger("floodpath.pipeline")


def run_simulation_pipeline(
    session: Session,
    run_id: Any,
    scenario_id: Optional[UUID] = None,
    mode: str = "full",
) -> Dict[str, Any]:
    """Orchestrate the end-to-end simulation pipeline and persist results."""
    run_uuid = run_id if isinstance(run_id, UUID) else UUID(str(run_id))
    run_id = run_uuid
    run = session.execute(
        select(SimulationRun).where(SimulationRun.id == run_id)
    ).scalar_one_or_none()

    if run is None:
        raise ValueError(f"SimulationRun with id {run_id} not found.")

    scenario = session.execute(
        select(Scenario).where(Scenario.id == run.scenario_id)
    ).scalar_one_or_none()

    if scenario is None:
        raise ValueError(f"Scenario with id {run.scenario_id} not found.")

    start_time = time.perf_counter()
    run.status = RunStatus.RUNNING
    run.started_at = datetime.now(timezone.utc)
    run.error_stage = None
    run.error_message = None
    session.flush()

    current_stage: Optional[PipelineStage] = None
    stage_timings: Dict[str, float] = {}

    try:
        origin_lat, origin_lon = extract_point_coordinates(scenario.site_point)
        radius_km = float(scenario.simulation_radius_km or 45.0)

        # -------------------------------------------------------------
        # Fast AI Surrogate Path (< 50ms inference)
        # -------------------------------------------------------------
        if mode == "fast":
            logger.info(f"Executing Fast AI Surrogate Mode for run {run_id}")
            run.mode = "fast"
            run.current_stage = PipelineStage.SUMMARY_GENERATION
            session.flush()

            # Query reference settlements
            all_settlements = session.execute(select(Settlement)).scalars().all()
            settlements_dicts = []
            for s in all_settlements:
                s_lat, s_lon = extract_point_coordinates(s.location)
                settlements_dicts.append({
                    "id": s.id,
                    "name": s.name,
                    "district": s.district,
                    "state": s.state,
                    "population": s.population,
                    "latitude": s_lat,
                    "longitude": s_lon,
                })

            surrogate = MLSurrogateModel()
            surrogate_res = surrogate.predict(
                dam_height_m=float(scenario.dam_height_m),
                dam_volume_m3=float(scenario.dam_volume_m3),
                breach_type=scenario.breach_type,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                simulation_radius_km=radius_km,
                settlements_list=settlements_dicts,
            )

            # Clear existing flood results for this run if any
            existing_results = session.execute(
                select(FloodResult).where(FloodResult.simulation_run_id == run_id)
            ).scalars().all()
            for res in existing_results:
                session.delete(res)

            # Insert surrogate flood extents
            for step in surrogate_res.time_steps:
                fr = FloodResult(
                    simulation_run_id=run_id,
                    time_step_minutes=step.time_step_minutes,
                    flood_extent=WKTElement(step.wkt_geometry, srid=4326),
                    max_depth_m=step.max_depth_m,
                )
                session.add(fr)

            # Clear existing affected settlements for this run
            existing_affected = session.execute(
                select(AffectedSettlement).where(AffectedSettlement.simulation_run_id == run_id)
            ).scalars().all()
            for aff in existing_affected:
                session.delete(aff)

            # Insert surrogate affected settlements
            for aff in surrogate_res.affected_settlements:
                row = AffectedSettlement(
                    simulation_run_id=run_id,
                    settlement_id=aff.settlement_id,
                    arrival_time_minutes=aff.arrival_time_minutes,
                    estimated_depth_m=aff.estimated_depth_m,
                )
                session.add(row)

            total_duration_s = round(time.perf_counter() - start_time, 3)
            run.status = RunStatus.SUCCEEDED
            run.completed_at = datetime.now(timezone.utc)
            session.commit()

            logger.info(
                f"Surrogate simulation run {run_id} completed in {total_duration_s}s "
                f"({surrogate_res.telemetry.inference_time_ms}ms inference). "
                f"Impacted settlements: {len(surrogate_res.affected_settlements)}."
            )

            return {
                "run_id": run_id,
                "status": RunStatus.SUCCEEDED,
                "mode": "fast",
                "is_surrogate": True,
                "total_duration_s": total_duration_s,
                "surrogate_telemetry": surrogate_res.telemetry,
                "num_time_steps": len(surrogate_res.time_steps),
                "num_affected_settlements": len(surrogate_res.affected_settlements),
                "summary": surrogate_res.summary_text,
                "breach_parameters": surrogate_res.breach_params,
            }

        # -------------------------------------------------------------
        # Full Physics 2D Hydrodynamic Mode
        # -------------------------------------------------------------
        run.mode = "full"
        # Stage 1: DEM Fetch & Conditioning
        # -------------------------------------------------------------
        current_stage = PipelineStage.DEM_FETCH
        run.current_stage = current_stage
        session.flush()
        t0 = time.perf_counter()
        logger.info(f"Starting {current_stage.value} for run {run_id}")

        dem_profile = fetch_dem_profile(origin_lat, origin_lon, radius_km=radius_km)
        stage_timings["dem_fetch"] = round(time.perf_counter() - t0, 3)

        # -------------------------------------------------------------
        # Stage 2: Empirical Breach Estimation
        # -------------------------------------------------------------
        current_stage = PipelineStage.BREACH_ESTIMATION
        run.current_stage = current_stage
        session.flush()
        t0 = time.perf_counter()
        logger.info(f"Starting {current_stage.value} for run {run_id}")

        dam_height = float(scenario.dam_height_m)
        dam_volume = float(scenario.dam_volume_m3)
        breach_params = calculate_breach_parameters(
            dam_height_m=dam_height,
            dam_volume_m3=dam_volume,
            breach_type=scenario.breach_type,
        )
        stage_timings["breach_estimation"] = round(time.perf_counter() - t0, 3)

        # -------------------------------------------------------------
        # Stage 3: 2D Flood Routing Simulation
        # -------------------------------------------------------------
        current_stage = PipelineStage.FLOOD_ROUTING
        run.current_stage = current_stage
        session.flush()
        t0 = time.perf_counter()
        logger.info(f"Starting {current_stage.value} for run {run_id}")

        routing_outputs = simulate_flood_routing(
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            breach=breach_params,
            dem=dem_profile,
            simulation_radius_km=radius_km,
        )

        # Clear existing flood results for this run if any
        existing_results = session.execute(
            select(FloodResult).where(FloodResult.simulation_run_id == run_id)
        ).scalars().all()
        for res in existing_results:
            session.delete(res)

        # Insert new time-stepped flood results
        for step in routing_outputs:
            fr = FloodResult(
                simulation_run_id=run_id,
                time_step_minutes=step.time_step_minutes,
                flood_extent=WKTElement(step.wkt_geometry, srid=4326),
                max_depth_m=step.max_depth_m,
            )
            session.add(fr)

        stage_timings["flood_routing"] = round(time.perf_counter() - t0, 3)

        # -------------------------------------------------------------
        # Stage 4: Summary & Impact Generation
        # -------------------------------------------------------------
        current_stage = PipelineStage.SUMMARY_GENERATION
        run.current_stage = current_stage
        session.flush()
        t0 = time.perf_counter()
        logger.info(f"Starting {current_stage.value} for run {run_id}")

        # Fetch settlements reference table
        all_settlements = session.execute(select(Settlement)).scalars().all()
        settlements_dicts = []
        for s in all_settlements:
            s_lat, s_lon = extract_point_coordinates(s.location)
            settlements_dicts.append({
                "id": s.id,
                "name": s.name,
                "district": s.district,
                "state": s.state,
                "population": s.population,
                "latitude": s_lat,
                "longitude": s_lon,
            })

        affected = assess_settlement_impacts(
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            time_steps=routing_outputs,
            settlements_list=settlements_dicts,
        )

        # Clear existing affected settlements for this run
        existing_affected = session.execute(
            select(AffectedSettlement).where(AffectedSettlement.simulation_run_id == run_id)
        ).scalars().all()
        for aff in existing_affected:
            session.delete(aff)

        for aff in affected:
            row = AffectedSettlement(
                simulation_run_id=run_id,
                settlement_id=aff.settlement_id,
                arrival_time_minutes=aff.arrival_time_minutes,
                estimated_depth_m=aff.estimated_depth_m,
            )
            session.add(row)

        summary_text = generate_plain_language_summary(
            affected,
            peak_depth_m=routing_outputs[0].max_depth_m if routing_outputs else 0.0,
        )
        stage_timings["summary_generation"] = round(time.perf_counter() - t0, 3)

        # -------------------------------------------------------------
        # Success Finalization
        # -------------------------------------------------------------
        total_duration_s = round(time.perf_counter() - start_time, 2)
        run.status = RunStatus.SUCCEEDED
        run.completed_at = datetime.now(timezone.utc)
        session.commit()

        logger.info(
            f"Simulation run {run_id} completed successfully in {total_duration_s}s. "
            f"Affected settlements: {len(affected)}."
        )

        return {
            "run_id": run_id,
            "status": RunStatus.SUCCEEDED,
            "stage_timings": stage_timings,
            "total_duration_s": total_duration_s,
            "num_time_steps": len(routing_outputs),
            "num_affected_settlements": len(affected),
            "summary": summary_text,
            "breach_parameters": breach_params,
        }

    except Exception as exc:
        session.rollback()
        logger.error(
            f"Simulation run {run_id} failed at stage {current_stage}: {exc}",
            exc_info=True,
        )
        # Update failed status in a fresh transaction
        try:
            failed_run = session.execute(
                select(SimulationRun).where(SimulationRun.id == run_id)
            ).scalar_one_or_none()
            if failed_run:
                failed_run.status = RunStatus.FAILED
                failed_run.error_stage = current_stage
                failed_run.error_message = str(exc)
                failed_run.completed_at = datetime.now(timezone.utc)
                session.commit()
        except Exception as inner_err:
            logger.error(f"Failed to record failure state for run {run_id}: {inner_err}")

        raise
