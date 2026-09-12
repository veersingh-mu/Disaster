import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from backend.app.models.base import Base


class CaseStudy(Base):
    __tablename__ = "case_studies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    simulation_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("simulation_runs.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    event_year = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    source_reference = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
