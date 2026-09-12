# Pydantic schemas export
from pydantic import BaseModel
from typing import Optional, Dict, Any

class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    database: str
    version: str = "0.1.0"

from app.schemas.region_state import StateBase, StateResponse, RegionBase, RegionResponse
from app.schemas.plant import PlantBase, PlantCreate, PlantUpdate, PlantResponse, PlantDetailResponse
from app.schemas.weather import WeatherBase, WeatherCreate, WeatherResponse
from app.schemas.forecast import ForecastPoint, FarmForecastResponse, AggregatedForecastResponse, NationalForecastResponse, HierarchicalTreeResponse
from app.schemas.alert import RecommendationResponse, AlertResponse, AlertStatsResponse

__all__ = [
    "HealthResponse",
    "StateBase",
    "StateResponse",
    "RegionBase",
    "RegionResponse",
    "PlantBase",
    "PlantCreate",
    "PlantUpdate",
    "PlantResponse",
    "PlantDetailResponse",
    "WeatherBase",
    "WeatherCreate",
    "WeatherResponse",
    "ForecastPoint",
    "FarmForecastResponse",
    "AggregatedForecastResponse",
    "NationalForecastResponse",
    "HierarchicalTreeResponse",
    "RecommendationResponse",
    "AlertResponse",
    "AlertStatsResponse",
]
