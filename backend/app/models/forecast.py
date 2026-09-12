from sqlalchemy import Column, Float, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.base_model import TimestampMixin

class Forecast(Base, TimestampMixin):
    __tablename__ = "forecasts"

    plant_id = Column(Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)
    forecast_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    horizon_hours = Column(Integer, default=24, nullable=False) # 24, 48, 72

    predicted_mw = Column(Float, nullable=False)
    confidence_score = Column(Float, default=0.90, nullable=False) # 0.00 to 1.00
    lower_bound_mw = Column(Float, nullable=False) # P10 confidence interval
    upper_bound_mw = Column(Float, nullable=False) # P90 confidence interval

    actual_mw = Column(Float, nullable=True) # Actual observed generation when available
    model_version = Column(String(50), default="v1.0-xgb", nullable=False)

    # Relationships
    plant = relationship("Plant", back_populates="forecasts")

    def __repr__(self):
        return f"<Forecast(plant_id={self.plant_id}, time='{self.forecast_timestamp}', predicted_mw={self.predicted_mw})>"
