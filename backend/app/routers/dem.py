"""Digital Elevation Model (DEM) Preview and Terrain Profiling Router."""

from fastapi import APIRouter, Query

from backend.app.schemas.dem import DEMPreviewResponse
from worker.pipeline.dem import estimate_site_geometry_from_dem

router = APIRouter(prefix="/dem", tags=["DEM"])


@router.get("/preview", response_model=DEMPreviewResponse)
def preview_dem(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180"),
    simulation_radius_km: float = Query(25.0, gt=0.0, le=500.0, description="Simulation radius in km"),
):
    """Provide terrain elevation, slope, and intelligent breach geometry estimates."""
    estimates = estimate_site_geometry_from_dem(latitude, longitude)

    return DEMPreviewResponse(
        latitude=latitude,
        longitude=longitude,
        elevation_m=estimates["elevation_m"],
        slope_degrees=estimates.get("slope_degrees"),
        estimated_dam_height_m=estimates["estimated_dam_height_m"],
        estimated_dam_volume_m3=estimates["estimated_dam_volume_m3"],
        source="SRTM 30m / USGS HydroSHEDS",
        coverage_available=True,
        resolution_m=estimates.get("resolution_m", 30),
        is_cached=estimates.get("is_cached", False),
    )
