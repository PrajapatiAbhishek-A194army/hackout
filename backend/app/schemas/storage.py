from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class BESSConfig(BaseModel):
    power_capacity_mw: float = Field(100.0, description="Rated charging/discharging power (MW)")
    energy_capacity_mwh: float = Field(400.0, description="Usable energy storage capacity (MWh)")
    round_trip_efficiency: float = Field(0.90, ge=0.5, le=1.0, description="AC-to-AC round-trip efficiency")
    min_soc_pct: float = Field(10.0, ge=0.0, le=50.0, description="Minimum state of charge to prevent cell degradation (%)")
    max_soc_pct: float = Field(90.0, ge=50.0, le=100.0, description="Maximum state of charge boundary (%)")
    initial_soc_pct: float = Field(20.0, ge=0.0, le=100.0, description="Starting state of charge at beginning of horizon (%)")
    degradation_cost_inr_per_kwh: float = Field(0.80, description="Battery wear cost per kWh cycled (INR)")

    model_config = ConfigDict(from_attributes=True)

class HourlyDispatchPoint(BaseModel):
    hour_index: int
    timestamp: datetime
    generation_mw: float
    grid_limit_mw: float
    bess_charge_mw: float
    bess_discharge_mw: float
    net_grid_mw: float
    curtailment_unmitigated_mw: float
    curtailment_mitigated_mw: float
    stored_energy_mwh: float
    soc_pct: float
    tariff_inr_per_mwh: float
    cash_flow_inr: float

    model_config = ConfigDict(from_attributes=True)

class BESSFinancialSummary(BaseModel):
    gross_charging_cost_inr: float
    gross_discharge_revenue_inr: float
    arbitrage_gross_profit_inr: float
    battery_degradation_cost_inr: float
    net_arbitrage_profit_inr: float
    total_charged_mwh: float
    total_discharged_mwh: float
    avoided_curtailment_mwh: float
    curtailment_reduction_pct: float
    avoided_curtailment_value_inr: float
    total_combined_economic_benefit_inr: float
    equivalent_full_cycles: float

    model_config = ConfigDict(from_attributes=True)

class BESSOptimizationResponse(BaseModel):
    plant_id: Optional[int] = None
    plant_name: Optional[str] = None
    plant_type: Optional[str] = None
    plant_capacity_mw: Optional[float] = None
    horizon_hours: int
    bess_config: BESSConfig
    financial_summary: BESSFinancialSummary
    dispatch_schedule: List[HourlyDispatchPoint]

    model_config = ConfigDict(from_attributes=True)

class BESSSimulateRequest(BaseModel):
    generation_profile_mw: List[float]
    grid_capacity_limit_mw: float
    bess_power_mw: float = 100.0
    bess_energy_mwh: float = 400.0
    round_trip_efficiency: float = 0.90
    min_soc_pct: float = 10.0
    max_soc_pct: float = 90.0
    initial_soc_pct: float = 20.0
    degradation_cost_inr_per_kwh: float = 0.80
    tariffs_inr_per_mwh: Optional[List[float]] = None
