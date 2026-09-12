"""Pydantic schemas for simulation flood results and impact analysis."""
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import RunStatus


class FloodResultStep(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    time_step_minutes: int = Field(..., ge=0, description="Elapsed time in minutes from breach initiation")
    flood_extent: Dict[str, Any] = Field(..., description="GeoJSON MultiPolygon or Geometry object")
    max_depth_m: Optional[float] = Field(None, description="Maximum water depth in meters at this time step")


class AffectedSettlementItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    settlement_id: UUID
    name: str
    district: str
    state: str
    population: Optional[int] = None
    arrival_time_minutes: int = Field(..., ge=0, description="Flood wave arrival time in minutes")
    estimated_depth_m: Optional[float] = Field(None, description="Estimated maximum flood depth at settlement in meters")


class ScenarioResultsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scenario_id: UUID
    simulation_run_id: UUID
    status: RunStatus
    mode: Optional[str] = "full"
    is_surrogate: bool = False
    solve_time_ms: Optional[float] = None
    summary_text: Optional[str] = None
    time_steps: List[FloodResultStep] = Field(default_factory=list)
    affected_settlements: List[AffectedSettlementItem] = Field(default_factory=list)
    total_affected_settlements: int = 0
    peak_depth_m: Optional[float] = None
    arrival_time_first_settlement_minutes: Optional[int] = None
