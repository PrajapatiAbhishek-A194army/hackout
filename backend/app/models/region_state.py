from sqlalchemy import Column, String, Float, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.base_model import TimestampMixin

class Region(Base, TimestampMixin):
    __tablename__ = "regions"

    code = Column(String(20), unique=True, index=True, nullable=False) # e.g. NR, WR, SR, ER, NER
    name = Column(String(100), nullable=False) # Northern Region, Western Region, etc.
    description = Column(Text, nullable=True)
    installed_solar_mw = Column(Float, default=0.0, nullable=False)
    installed_wind_mw = Column(Float, default=0.0, nullable=False)

    # Relationships
    states = relationship("State", back_populates="region", cascade="all, delete-orphan")
    plants = relationship("Plant", back_populates="region")

    def __repr__(self):
        return f"<Region(code='{self.code}', name='{self.name}')>"


class State(Base, TimestampMixin):
    __tablename__ = "states"

    code = Column(String(10), unique=True, index=True, nullable=False) # e.g. RJ, GJ, TN, KA, MH
    name = Column(String(100), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="CASCADE"), nullable=False, index=True)
    installed_solar_mw = Column(Float, default=0.0, nullable=False)
    installed_wind_mw = Column(Float, default=0.0, nullable=False)

    # Relationships
    region = relationship("Region", back_populates="states")
    plants = relationship("Plant", back_populates="state")

    def __repr__(self):
        return f"<State(code='{self.code}', name='{self.name}')>"
