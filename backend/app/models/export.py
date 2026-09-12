import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from backend.app.models.base import Base
from backend.app.models.enums import ExportFormat


class Export(Base):
    __tablename__ = "exports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_run_id = Column(
        UUID(as_uuid=True), ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_url = Column(String, nullable=False)
    format = Column(Enum(ExportFormat, name="export_format"), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
