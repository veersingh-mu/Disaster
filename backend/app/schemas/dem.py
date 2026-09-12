"""Pydantic schemas for DEM preview and elevation estimates."""
from typing import Optional

from pydantic import BaseModel, Field


class DEMPreviewRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")
    simulation_radius_km: float = Field(25.0, gt=0.0, le=500.0, description="Radius in km")


class DEMPreviewResponse(BaseModel):
    latitude: float
    longitude: float
    elevation_m: float
    slope_degrees: Optional[float] = None
    estimated_dam_height_m: float
    estimated_dam_volume_m3: float
    source: str = "SRTM 30m / OpenTopography"
    coverage_available: bool = True
    resolution_m: int = 30
    is_cached: bool = False
