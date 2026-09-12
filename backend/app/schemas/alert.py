from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class RecommendationResponse(BaseModel):
    id: int
    alert_id: int
    action_type: str
    title: str
    summary: str
    rationale: str
    recommended_mw: Optional[float] = None
    priority: int
    estimated_cost_saving_inr: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AlertResponse(BaseModel):
    id: int
    plant_id: Optional[int] = None
    plant_name: Optional[str] = None
    alert_type: str
    severity: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    delta_mw: Optional[float] = None
    status: str
    confidence: float
    created_at: datetime
    recommendations: List[RecommendationResponse] = []

    model_config = ConfigDict(from_attributes=True)

class AlertStatsResponse(BaseModel):
    total_active_alerts: int
    critical_alerts: int
    warning_alerts: int
    info_alerts: int
    over_generation_mw: float
    under_generation_mw: float
