from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class FeatureImportanceItem(BaseModel):
    feature_name: str
    importance_score: float  # gain
    weight: float
    cover: float
    percentage: float
    rank: int
    category: str
    description: str

    model_config = ConfigDict(from_attributes=True)

class GlobalFeatureImportanceResponse(BaseModel):
    model_type: str
    model_version: str
    total_features: int
    top_features: List[FeatureImportanceItem]
    category_importance: Dict[str, float]

    model_config = ConfigDict(from_attributes=True)

class ShapWaterfallPoint(BaseModel):
    feature_name: str
    display_name: str
    category: str
    feature_value: float
    shap_value: float
    cumulative_value: float
    direction: str  # "positive" or "negative"

    model_config = ConfigDict(from_attributes=True)

class ShapWaterfallResponse(BaseModel):
    plant_id: int
    plant_name: str
    plant_type: str
    timestamp: datetime
    base_value: float
    predicted_mw: float
    unit: str = "MW"
    waterfall_steps: List[ShapWaterfallPoint]
    top_positive_features: List[ShapWaterfallPoint]
    top_negative_features: List[ShapWaterfallPoint]

    model_config = ConfigDict(from_attributes=True)

class DriverBreakdownItem(BaseModel):
    category_id: str
    category_name: str
    impact_mw: float
    percentage_impact: float
    direction: str
    description: str
    key_features: List[str]

    model_config = ConfigDict(from_attributes=True)

class DriverBreakdownResponse(BaseModel):
    plant_id: int
    plant_name: str
    plant_type: str
    timestamp: datetime
    predicted_mw: float
    base_value: float
    net_weather_impact_mw: float
    drivers: List[DriverBreakdownItem]

    model_config = ConfigDict(from_attributes=True)

class SensitivityPoint(BaseModel):
    delta_pct: Optional[float] = None
    delta_value: Optional[float] = None
    parameter_value: float
    predicted_mw: float
    mw_delta: float
    pct_mw_change: float

    model_config = ConfigDict(from_attributes=True)

class MeteorologicalSensitivityResponse(BaseModel):
    plant_id: int
    plant_name: str
    parameter: str
    unit: str
    baseline_parameter_value: float
    baseline_predicted_mw: float
    elasticity: float
    marginal_rate_mw_per_unit: float
    curve: List[SensitivityPoint]

    model_config = ConfigDict(from_attributes=True)
