from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class WeatherBase(BaseModel):
    plant_id: int
    timestamp: datetime
    ghi: Optional[float] = None
    dni: Optional[float] = None
    dhi: Optional[float] = None
    temperature_c: Optional[float] = None
    relative_humidity: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    surface_pressure_hpa: Optional[float] = None
    wind_speed_10m: Optional[float] = None
    wind_speed_100m: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    source: str = "open_meteo"

class WeatherCreate(WeatherBase):
    pass

class WeatherResponse(WeatherBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
