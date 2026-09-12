from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class StateBase(BaseModel):
    code: str
    name: str
    region_id: int
    installed_solar_mw: float = 0.0
    installed_wind_mw: float = 0.0

class StateResponse(StateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RegionBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    installed_solar_mw: float = 0.0
    installed_wind_mw: float = 0.0

class RegionResponse(RegionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    states: List[StateResponse] = []

    model_config = ConfigDict(from_attributes=True)
