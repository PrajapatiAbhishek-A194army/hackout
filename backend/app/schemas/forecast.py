from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class ForecastPoint(BaseModel):
    timestamp: datetime
    predicted_mw: float
    solar_mw: Optional[float] = 0.0
    wind_mw: Optional[float] = 0.0
    confidence_score: float
    lower_bound_mw: float
    upper_bound_mw: float
    actual_mw: Optional[float] = None
    horizon_hours: int = 24

    model_config = ConfigDict(from_attributes=True)

class PlantSummary(BaseModel):
    plant_id: int
    plant_code: str
    plant_name: str
    plant_type: str
    state_code: Optional[str] = None
    capacity_mw: float
    peak_mw: float
    expected_total_mwh: float
    capacity_factor_pct: float
    average_confidence: float

class FarmForecastResponse(BaseModel):
    level: str = "farm"
    plant_id: int
    plant_code: str
    plant_name: str
    plant_type: str
    capacity_mw: float
    region_id: int
    region_code: str
    region_name: str
    state_id: int
    state_code: str
    state_name: str
    latitude: float
    longitude: float
    elevation_m: Optional[float] = None
    technology: Optional[str] = None
    commissioning_year: Optional[int] = None
    operator_name: Optional[str] = None
    horizon_hours: int
    peak_generation_mw: float
    peak_generation_timestamp: Optional[datetime] = None
    average_generation_mw: float
    expected_total_mwh: float
    solar_total_mwh: float
    wind_total_mwh: float
    capacity_factor_pct: float
    average_confidence: float
    ramp_events_count: int
    ramp_events: List[Dict[str, Any]] = []
    forecast_points: List[ForecastPoint]

    model_config = ConfigDict(from_attributes=True)

class AggregatedForecastResponse(BaseModel):
    level: str  # 'region' or 'state'
    entity_id: int
    entity_code: str
    entity_name: str
    region_code: Optional[str] = None
    region_name: Optional[str] = None
    horizon_hours: int
    total_capacity_mw: float
    installed_solar_mw: float
    installed_wind_mw: float
    plants_count: int
    peak_generation_mw: float
    peak_generation_timestamp: Optional[datetime] = None
    average_generation_mw: float
    expected_total_mwh: float
    solar_total_mwh: float
    wind_total_mwh: float
    solar_contribution_pct: float
    wind_contribution_pct: float
    capacity_factor_pct: float
    average_confidence: float
    plants_breakdown: List[Dict[str, Any]] = []
    forecast_points: List[ForecastPoint]

    model_config = ConfigDict(from_attributes=True)

class NationalForecastResponse(BaseModel):
    level: str = "national"
    country: str = "India"
    grid_operator: str = "NLDC / POSOCO / Grid-India"
    horizon_hours: int
    total_capacity_mw: float
    installed_solar_mw: float
    installed_wind_mw: float
    active_plants_count: int
    national_peak_mw: float
    national_peak_timestamp: Optional[datetime] = None
    average_generation_mw: float
    expected_total_mwh: float
    expected_daily_generation_mwh: float
    solar_total_mwh: float
    wind_total_mwh: float
    solar_contribution_pct: float
    wind_contribution_pct: float
    capacity_factor_pct: float
    average_confidence: float
    grid_balancing_risk: str
    max_hourly_ramp_mw: float
    regional_summaries: List[Dict[str, Any]]
    state_summaries: List[Dict[str, Any]]
    forecast_points: List[ForecastPoint]

    model_config = ConfigDict(from_attributes=True)

class HierarchyPlantNode(BaseModel):
    id: int
    code: str
    name: str
    plant_type: str
    capacity_mw: float
    latitude: float
    longitude: float
    technology: Optional[str] = None
    status: str

class HierarchyStateNode(BaseModel):
    id: int
    code: str
    name: str
    total_capacity_mw: float
    plants_count: int
    plants: List[HierarchyPlantNode]

class HierarchyRegionNode(BaseModel):
    id: int
    code: str
    name: str
    total_capacity_mw: float
    states_count: int
    states: List[HierarchyStateNode]

class HierarchicalTreeResponse(BaseModel):
    level: str = "national"
    country: str = "India"
    code: str = "IND"
    name: str
    total_capacity_mw: float
    regions_count: int
    regions: List[HierarchyRegionNode]
