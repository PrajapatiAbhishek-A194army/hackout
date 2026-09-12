from sqlalchemy import Column, String, Boolean
from app.database.base import Base
from app.models.base_model import TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), default="grid_operator", nullable=False) # 'grid_operator', 'plant_owner', 'utility', 'energy_trader', 'admin'
    organization = Column(String(150), nullable=True) # e.g. 'Northern Regional Load Despatch Centre'
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role}')>"
