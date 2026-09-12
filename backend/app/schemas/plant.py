from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class PlantBase(BaseModel):
    name: str
    code: str
    plant_type: str # 'solar', 'wind', 'hybrid'
    capacity_mw: float
    latitude: float
    longitude: float
    elevation_m: Optional[float] = None
    technology: Optional[str] = None
    commissioning_year: Optional[int] = None
    operator_name: Optional[str] = None
    status: str = "active"
    region_id: int
    state_id: int

class PlantCreate(PlantBase):
    pass

class PlantUpdate(BaseModel):
    name: Optional[str] = None
    capacity_mw: Optional[float] = None
    status: Optional[str] = None
    technology: Optional[str] = None

class PlantResponse(PlantBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PlantDetailResponse(PlantResponse):
    region_name: Optional[str] = None
    state_name: Optional[str] = None
    current_forecast_mw: Optional[float] = None
    current_weather_ghi: Optional[float] = None
    current_wind_speed: Optional[float] = None
    active_alerts_count: int = 0
