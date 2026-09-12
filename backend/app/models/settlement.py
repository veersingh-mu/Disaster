import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from backend.app.models.base import Base


class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    population = Column(Integer, nullable=True)
    state = Column(String, nullable=False)
    district = Column(String, nullable=False)
