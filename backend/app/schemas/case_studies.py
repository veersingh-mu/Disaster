"""Pydantic schemas for historical case studies."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.app.models.enums import BreachType


class CaseStudyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scenario_id: UUID
    simulation_run_id: UUID
    event_year: int
    description: str
    source_reference: Optional[str] = None
    created_at: datetime
    # Scenario metadata summary
    name: Optional[str] = None
    breach_type: Optional[BreachType] = None
    dam_height_m: Optional[float] = None
    dam_volume_m3: Optional[float] = None
    simulation_radius_km: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CaseStudyListResponse(BaseModel):
    case_studies: List[CaseStudyResponse]
    total: int
