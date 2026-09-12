"""Pydantic schemas for report and data exports."""
from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from backend.app.models.enums import ExportFormat


class ExportCreateRequest(BaseModel):
    format: ExportFormat = Field(
        ExportFormat.PDF,
        validation_alias=AliasChoices("format", "export_format"),
        description="Export format: 'pdf' or 'json'",
    )


class ExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    simulation_run_id: UUID
    user_id: UUID
    file_url: str
    format: ExportFormat
    created_at: datetime
