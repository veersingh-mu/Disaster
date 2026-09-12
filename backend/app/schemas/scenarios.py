"""Pydantic schemas for Scenario endpoints."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.enums import BreachType, RunStatus


class ScenarioBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name or identifier for the scenario")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Breach site latitude (-90 to 90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Breach site longitude (-180 to 180)")
    breach_type: BreachType = Field(..., description="Type of breach: 'structural' or 'landslide_glof'")
    dam_height_m: float = Field(..., gt=0.0, description="Dam/barrier height in meters (> 0)")
    dam_volume_m3: float = Field(..., gt=0.0, description="Reservoir or lake volume in cubic meters (> 0)")
    simulation_radius_km: float = Field(25.0, gt=0.0, le=500.0, description="Simulation radius in km (default: 25)")
    is_dem_estimated: bool = Field(False, description="Flag indicating height/volume were auto-estimated from DEM")

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Scenario name cannot be empty or whitespace only")
        return stripped


class ScenarioCreate(ScenarioBase):
    pass


class ScenarioUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    simulation_radius_km: Optional[float] = Field(None, gt=0.0, le=500.0)


class ScenarioResponse(ScenarioBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    latest_run_id: Optional[UUID] = None
    latest_run_status: Optional[RunStatus] = None


class ScenarioListResponse(BaseModel):
    scenarios: List[ScenarioResponse]
    total: int
