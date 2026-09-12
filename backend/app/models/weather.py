from sqlalchemy import Column, Float, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.base_model import TimestampMixin

class Weather(Base, TimestampMixin):
    __tablename__ = "weather"

    plant_id = Column(Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Solar Irradiance Metrics (W/m²)
    ghi = Column(Float, nullable=True) # Global Horizontal Irradiance
    dni = Column(Float, nullable=True) # Direct Normal Irradiance
    dhi = Column(Float, nullable=True) # Diffuse Horizontal Irradiance

    # Atmospheric & Ambient Conditions
    temperature_c = Column(Float, nullable=True) # Ambient air temperature in °C
    relative_humidity = Column(Float, nullable=True) # %
    cloud_cover_pct = Column(Float, nullable=True) # 0 to 100%
    surface_pressure_hpa = Column(Float, nullable=True) # hPa

    # Wind Vectors
    wind_speed_10m = Column(Float, nullable=True) # m/s at 10m elevation
    wind_speed_100m = Column(Float, nullable=True) # m/s at turbine hub height (100m)
    wind_direction_deg = Column(Float, nullable=True) # 0 - 360 degrees

    source = Column(String(50), default="open_meteo", nullable=False) # 'open_meteo', 'nasa_power', 'sensor', 'synthetic'

    # Relationships
    plant = relationship("Plant", back_populates="weather_records")

    def __repr__(self):
        return f"<Weather(plant_id={self.plant_id}, time='{self.timestamp}', ghi={self.ghi}, wind_100m={self.wind_speed_100m})>"
