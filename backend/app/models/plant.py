from sqlalchemy import Column, String, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.base_model import TimestampMixin

class Plant(Base, TimestampMixin):
    __tablename__ = "plants"

    name = Column(String(150), index=True, nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=False) # e.g. BHADLA_SOLAR_01
    plant_type = Column(String(20), index=True, nullable=False) # 'solar', 'wind', 'hybrid'
    capacity_mw = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation_m = Column(Float, nullable=True)
    technology = Column(String(150), nullable=True) # e.g. 'Bifacial Mono-PERC with Single-Axis Tracker'
    commissioning_year = Column(Integer, nullable=True)
    operator_name = Column(String(150), nullable=True)
    status = Column(String(20), default="active", nullable=False) # 'active', 'maintenance', 'curtailed', 'offline'

    # Foreign Keys
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False, index=True)
    state_id = Column(Integer, ForeignKey("states.id"), nullable=False, index=True)

    # Relationships
    region = relationship("Region", back_populates="plants")
    state = relationship("State", back_populates="plants")
    forecasts = relationship("Forecast", back_populates="plant", cascade="all, delete-orphan")
    weather_records = relationship("Weather", back_populates="plant", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="plant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Plant(name='{self.name}', type='{self.plant_type}', capacity_mw={self.capacity_mw})>"
