import uuid

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from backend.app.models.base import Base


class AffectedSettlement(Base):
    __tablename__ = "affected_settlements"
    __table_args__ = (
        UniqueConstraint("simulation_run_id", "settlement_id", name="uq_run_settlement"),
        CheckConstraint("arrival_time_minutes >= 0", name="chk_arrival_nonnegative"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    settlement_id = Column(
        UUID(as_uuid=True), ForeignKey("settlements.id", ondelete="RESTRICT"), nullable=False
    )
    arrival_time_minutes = Column(Integer, nullable=False)
    estimated_depth_m = Column(Numeric(6, 2), nullable=True)
