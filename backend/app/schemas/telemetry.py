from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class LiveGridTelemetry(BaseModel):
    timestamp: datetime
    grid_frequency_hz: float = Field(..., description="National grid frequency (e.g. 50.02 Hz)")
    frequency_status: str = Field(..., description="NORMAL (49.90-50.05 Hz), HIGH, LOW")
    national_demand_mw: float = Field(..., description="Estimated All-India instant power demand (MW)")
    total_renewable_mw: float = Field(..., description="Instantaneous total renewable generation (MW)")
    total_solar_mw: float = Field(..., description="Instantaneous total solar generation (MW)")
    total_wind_mw: float = Field(..., description="Instantaneous total wind generation (MW)")
    renewable_penetration_pct: float = Field(..., description="Percentage of national demand supplied by renewables")
    bess_net_dispatch_mw: float = Field(..., description="Net BESS injection (>0 discharge, <0 charge)")
    ramp_rate_mw_per_min: float = Field(..., description="Renewable ramp delta in MW/min")
    active_alerts_count: int = Field(..., description="Count of unresolved grid alerts")

class PlantWeatherTelemetry(BaseModel):
    irradiance_ghi: float
    wind_speed_ms: float
    ambient_temp_c: float
    cloud_cover_pct: float

class LivePlantTelemetry(BaseModel):
    plant_id: int
    plant_code: str
    plant_name: str
    plant_type: str
    capacity_mw: float
    timestamp: datetime
    current_generation_mw: float
    capacity_factor_pct: float
    weather: PlantWeatherTelemetry
    bess_soc_pct: Optional[float] = None
    bess_power_mw: Optional[float] = None
    operational_status: str = Field(..., description="NORMAL, CURTAILED, WARNING, TRIPPED")

class WebSocketMessage(BaseModel):
    type: str = Field(..., description="Message type: grid_telemetry, plant_telemetry, alert_event, ack, error, pong")
    topic: str = Field(..., description="Channel topic: global_grid, alerts, plant:{id}, region:{id}")
    timestamp: datetime
    data: Dict[str, Any]

class WSSubscriptionMessage(BaseModel):
    action: str = Field(..., description="subscribe, unsubscribe, ping")
    topic: Optional[str] = Field(None, description="Target topic name")

class TelemetryStatsResponse(BaseModel):
    total_active_connections: int
    connections_by_topic: Dict[str, int]
    server_time: datetime
