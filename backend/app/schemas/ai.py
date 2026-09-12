"""Pydantic schemas for AI-powered tactical evacuation briefings."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AIBriefingRequest(BaseModel):
    """Optional customization parameters for the tactical evacuation briefing."""

    focus_area: Optional[str] = Field(
        None,
        description="Optional operational focus (e.g., 'immediate_evacuation', 'transport_corridors', 'resource_staging')",
    )
    urgency_level: Optional[str] = Field(
        None,
        description="Override or requested urgency emphasis: 'IMMEDIATE', 'HIGH', 'MODERATE', 'ADVISORY'",
    )
    custom_instructions: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional instructions for emergency operators (sanitized and bounded)",
    )


class SettlementTimelineItem(BaseModel):
    """Structured village impact and evacuation recommendation."""

    model_config = ConfigDict(from_attributes=True)

    settlement_id: UUID
    name: str
    district: str
    state: str
    arrival_time_minutes: int = Field(..., ge=0)
    estimated_depth_m: Optional[float] = None
    evacuation_priority: str = Field(..., description="'IMMEDIATE', 'HIGH', 'STANDBY', 'MONITOR'")
    recommended_action: str = Field(..., description="Actionable field evacuation guidance")


class AIBriefingResponse(BaseModel):
    """Structured NDMA/SEOC-compliant tactical disaster situation & evacuation briefing."""

    model_config = ConfigDict(from_attributes=True)

    scenario_id: UUID
    headline: str
    evacuation_urgency: str = Field(..., description="'IMMEDIATE', 'HIGH', 'MODERATE', 'ADVISORY'")
    executive_summary: str
    settlement_timeline: List[SettlementTimelineItem] = Field(default_factory=list)
    resource_staging_advisory: List[str] = Field(
        default_factory=list,
        description="Actionable tactical positioning guidance for NDRF, SDRF, and civil administration",
    )
    public_advisory_bulletin: str = Field(
        ...,
        description="Plain-language emergency public broadcast text suitable for siren and radio systems",
    )
    model_used: str
    is_fallback: bool = False
    generated_at: datetime
