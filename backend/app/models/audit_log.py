from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base
from app.models.base_model import TimestampMixin

class AuditLog(Base, TimestampMixin):
    """
    Audit log tracking security-sensitive and operational actions across the platform.
    """
    __tablename__ = "audit_logs"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_email = Column(String(255), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True) # e.g. LOGIN_SUCCESS, MODEL_RETRAIN, ALERT_ACKNOWLEDGE
    resource_type = Column(String(50), nullable=False, index=True) # e.g. auth, mlops, alerts, storage, reports
    resource_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    status = Column(String(20), default="SUCCESS", nullable=False) # SUCCESS, DENIED, FAILURE
    details_json = Column(Text, nullable=True)

    user = relationship("User", backref="audit_logs")

    def __repr__(self):
        return f"<AuditLog(action='{self.action}', user='{self.user_email}', status='{self.status}')>"
