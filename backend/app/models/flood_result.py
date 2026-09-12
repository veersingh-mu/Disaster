import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from backend.app.models.base import Base


class FloodResult(Base):
    __tablename__ = "flood_results"
    __table_args__ = (
        UniqueConstraint("simulation_run_id", "time_step_minutes", name="uq_run_timestep"),
        CheckConstraint("time_step_minutes >= 0", name="chk_timestep_nonnegative"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    time_step_minutes = Column(Integer, nullable=False)
    flood_extent = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)
    max_depth_m = Column(Numeric(6, 2), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
