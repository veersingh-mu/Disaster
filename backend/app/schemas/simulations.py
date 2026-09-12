"""Pydantic schemas for simulation runs and polling status."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import PipelineStage, RunStatus


class SimulationRunCreate(BaseModel):
    mode: str = Field("full", description="Simulation mode: 'full' physics-based solve or 'fast' ML surrogate")


class SimulationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scenario_id: UUID
    status: RunStatus
    mode: Optional[str] = "full"
    current_stage: Optional[PipelineStage] = None
    error_stage: Optional[PipelineStage] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class SimulationStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scenario_id: UUID
    run_id: UUID
    status: RunStatus
    mode: Optional[str] = "full"
    current_stage: Optional[PipelineStage] = None
    error_stage: Optional[PipelineStage] = None
    error_message: Optional[str] = None
    progress_percent: int = Field(0, ge=0, le=100, description="Estimated completion percentage")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    elapsed_seconds: Optional[float] = None
