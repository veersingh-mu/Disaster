import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID

from backend.app.models.base import Base
from backend.app.models.enums import BreachType


class Scenario(Base):
    __tablename__ = "scenarios"
    __table_args__ = (
        CheckConstraint("dam_height_m > 0", name="chk_dam_height_positive"),
        CheckConstraint("dam_volume_m3 > 0", name="chk_dam_volume_positive"),
        CheckConstraint("simulation_radius_km > 0", name="chk_sim_radius_positive"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String, nullable=False)
    site_point = Column(Geometry("POINT", srid=4326), nullable=False)
    breach_type = Column(Enum(BreachType, name="breach_type"), nullable=False)
    dam_height_m = Column(Numeric(8, 2), nullable=False)
    dam_volume_m3 = Column(Numeric(14, 2), nullable=False)
    simulation_radius_km = Column(Numeric(6, 2), nullable=False, default=25.0)
    is_dem_estimated = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def latitude(self) -> float:
        from backend.app.utils.geo import extract_point_coordinates
        lat, _ = extract_point_coordinates(self.site_point)
        return lat

    @property
    def longitude(self) -> float:
        from backend.app.utils.geo import extract_point_coordinates
        _, lon = extract_point_coordinates(self.site_point)
        return lon
