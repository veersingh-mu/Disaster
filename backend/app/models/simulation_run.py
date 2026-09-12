import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from backend.app.models.base import Base
from backend.app.models.enums import PipelineStage, RunStatus

pipeline_stage_enum = Enum(PipelineStage, name="pipeline_stage")


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(RunStatus, name="run_status"), nullable=False, default=RunStatus.PENDING, index=True
    )
    current_stage = Column(pipeline_stage_enum, nullable=True)
    error_stage = Column(pipeline_stage_enum, nullable=True)
    error_message = Column(String, nullable=True)
    mode = Column(String, nullable=True, default="full")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
