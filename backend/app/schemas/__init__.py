# Pydantic schemas
from pydantic import BaseModel
from typing import Optional, Dict, Any

class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    database: str
    version: str = "0.1.0"
