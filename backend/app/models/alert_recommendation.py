from sqlalchemy import Column, Float, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.base_model import TimestampMixin

class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"

    plant_id = Column(Integer, ForeignKey("plants.id", ondelete="SET NULL"), nullable=True, index=True)
    alert_type = Column(String(50), nullable=False) # 'over_generation', 'under_generation', 'ramp_warning', 'forecast_change'
    severity = Column(String(20), default="warning", nullable=False) # 'info', 'warning', 'critical'
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)

    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False)
    delta_mw = Column(Float, nullable=True) # MW excess, deficit, or ramp delta
    status = Column(String(20), default="active", nullable=False) # 'active', 'acknowledged', 'resolved', 'suppressed'
    confidence = Column(Float, default=0.85, nullable=False)

    # Acknowledgment & Resolution tracking
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    ack_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Relationships
    plant = relationship("Plant", back_populates="alerts")
    recommendations = relationship("Recommendation", back_populates="alert", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Alert(type='{self.alert_type}', severity='{self.severity}', delta_mw={self.delta_mw})>"


class Recommendation(Base, TimestampMixin):
    __tablename__ = "recommendations"

    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(50), nullable=False) # 'storage_charge', 'storage_discharge', 'controlled_curtailment', 'backup_dispatch', 'power_procurement'
    title = Column(String(200), nullable=False)
    summary = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False) # Explainable AI reasoning
    recommended_mw = Column(Float, nullable=True)
    priority = Column(Integer, default=1, nullable=False) # 1 = highest
    estimated_cost_saving_inr = Column(Float, nullable=True)

    # Relationships
    alert = relationship("Alert", back_populates="recommendations")

    def __repr__(self):
        return f"<Recommendation(action='{self.action_type}', recommended_mw={self.recommended_mw})>"
