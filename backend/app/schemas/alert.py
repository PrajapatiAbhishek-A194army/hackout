from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
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
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    ack_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    recommendations: List[RecommendationResponse] = []

    model_config = ConfigDict(from_attributes=True)

class AlertStatsResponse(BaseModel):
    total_active_alerts: int
    critical_alerts: int
    warning_alerts: int
    info_alerts: int
    acknowledged_alerts: int = 0
    resolved_alerts: int = 0
    over_generation_mw: float
    under_generation_mw: float

    model_config = ConfigDict(from_attributes=True)

class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: str = "Grid Dispatcher / Operator"
    notes: Optional[str] = "Alert verified. Mitigation protocols initiated."

class AlertResolveRequest(BaseModel):
    resolution_notes: str = "System generation stabilized within nominal operating margins."
    resolved_by: Optional[str] = "Grid Dispatcher / Operator"

class AlertSuppressRequest(BaseModel):
    reason: str = "Scheduled park maintenance / controlled curtailment in progress."

class NotificationDispatchReceipt(BaseModel):
    dispatch_id: str
    alert_id: int
    title: str
    severity: str
    channels: List[str]
    delivery_status: str
    dispatched_at: datetime
    recipient_count: int
    summary_message: str

class AlertScanResult(BaseModel):
    plants_scanned: int
    new_alerts_detected: int
    critical_count: int
    warning_count: int
    alerts: List[AlertResponse]
