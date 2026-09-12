from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class ForecastPoint(BaseModel):
    timestamp: datetime
    predicted_mw: float
    confidence_score: float
    lower_bound_mw: float
    upper_bound_mw: float
    actual_mw: Optional[float] = None
    horizon_hours: int = 24

    model_config = ConfigDict(from_attributes=True)

class FarmForecastResponse(BaseModel):
    plant_id: int
    plant_name: str
    plant_type: str
    capacity_mw: float
    horizon_hours: int
    peak_generation_mw: float
    average_generation_mw: float
    capacity_factor_pct: float
    forecast_points: List[ForecastPoint]

class AggregatedForecastResponse(BaseModel):
    level: str # 'region' or 'state'
    entity_id: int
    entity_name: str
    entity_code: str
    total_capacity_mw: float
    horizon_hours: int
    solar_peak_mw: float
    wind_peak_mw: float
    total_peak_mw: float
    forecast_points: List[ForecastPoint]

class NationalForecastResponse(BaseModel):
    horizon_hours: int
    total_capacity_mw: float
    national_peak_mw: float
    expected_daily_generation_mwh: float
    solar_contribution_pct: float
    wind_contribution_pct: float
    forecast_points: List[ForecastPoint]
