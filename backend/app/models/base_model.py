from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, func

class TimestampMixin:
    """Mixin for models requiring created_at and updated_at timestamps."""
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
