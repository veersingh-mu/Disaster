"""Common schema definitions for FloodPath API."""
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class ErrorDetail(BaseModel):
    """Detailed error info for field-level validation errors."""
    field: Optional[str] = None
    message: str


class ErrorResponse(BaseModel):
    """Standardized structured error response format."""
    error_code: str
    message: str
    details: Optional[List[ErrorDetail]] = None


class Coordinates(BaseModel):
    """Geographic coordinate pair in WGS84 (SRID 4326)."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if v < -90.0 or v > 90.0:
            raise ValueError("Latitude must be between -90 and 90 degrees")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if v < -180.0 or v > 180.0:
            raise ValueError("Longitude must be between -180 and 180 degrees")
        return v

    def to_wkt(self) -> str:
        """Return WKT representation: POINT(lon lat)."""
        return f"POINT({self.longitude} {self.latitude})"


class GeoJSONPoint(BaseModel):
    type: str = "Point"
    coordinates: List[float] = Field(..., min_length=2, max_length=3, description="[longitude, latitude]")

    @field_validator("coordinates")
    @classmethod
    def validate_coords(cls, v: List[float]) -> List[float]:
        lon, lat = v[0], v[1]
        if lon < -180.0 or lon > 180.0:
            raise ValueError("Longitude must be between -180 and 180 degrees")
        if lat < -90.0 or lat > 90.0:
            raise ValueError("Latitude must be between -90 and 90 degrees")
        return v


class GeoJSONMultiPolygon(BaseModel):
    type: str = "MultiPolygon"
    coordinates: List[Any] = Field(..., description="MultiPolygon coordinate rings")
