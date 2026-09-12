import uuid
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base
from app.models.base_model import TimestampMixin

class ReportRecord(Base, TimestampMixin):
    """
    Tracks generated reports, file formats, archive locations, and parameters.
    """
    __tablename__ = "reports"

    report_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    report_type = Column(String(64), index=True, nullable=False) # cerc_dsm, daily_generation, regional_grid_code, bess_dispatch_audit
    format = Column(String(32), nullable=False) # csv, xlsx, html, json
    plant_id = Column(Integer, ForeignKey("plants.id"), nullable=True, index=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True, index=True)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, nullable=False, default=0)
    parameters_json = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="completed") # completed, failed, generating

    plant = relationship("Plant", backref="reports")
    region = relationship("Region", backref="reports")
