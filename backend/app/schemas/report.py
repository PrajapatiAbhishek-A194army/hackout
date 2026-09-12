from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class ReportFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"
    HTML = "html"
    JSON = "json"

class ReportType(str, Enum):
    CERC_DSM = "cerc_dsm"
    DAILY_GENERATION = "daily_generation"
    REGIONAL_GRID_CODE = "regional_grid_code"
    BESS_DISPATCH_AUDIT = "bess_dispatch_audit"

class ReportGenerateRequest(BaseModel):
    report_type: ReportType = Field(..., description="Type of regulatory or operational report to generate")
    format: ReportFormat = Field(default=ReportFormat.CSV, description="Export file format: csv, xlsx, html, json")
    plant_id: Optional[int] = Field(None, description="Plant ID if plant-specific report")
    region_id: Optional[int] = Field(None, description="Region ID if regional report")
    horizon_hours: int = Field(default=24, ge=1, le=168, description="Horizon length in hours (default: 24)")
    date_str: Optional[str] = Field(None, description="Target date in YYYY-MM-DD format (default: current date)")
    custom_title: Optional[str] = Field(None, description="Custom title for the generated document")

class ReportMetadataResponse(BaseModel):
    report_id: str
    title: str
    report_type: str
    format: str
    plant_id: Optional[int] = None
    region_id: Optional[int] = None
    file_size_bytes: int
    download_url: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class ReportHistoryResponse(BaseModel):
    total_count: int
    reports: List[ReportMetadataResponse]

class DSMTimeBlockItem(BaseModel):
    time_block: int = Field(..., ge=1, le=96, description="Block index 1 through 96")
    time_range: str = Field(..., description="e.g. '00:00 - 00:15'")
    available_capacity_mw: float = Field(..., description="AvC in MW declared to SLDC")
    scheduled_generation_mw: float = Field(..., description="Day-ahead schedule submitted to grid in MW")
    actual_generation_mw: float = Field(..., description="Actual / ML forecasted injection in MW")
    deviation_mw: float = Field(..., description="Actual - Scheduled MW")
    deviation_pct: float = Field(..., description="Absolute percentage deviation relative to AvC")
    deviation_band: str = Field(..., description="within_10_pct, between_10_and_15_pct, beyond_15_pct")
    penalty_rate_inr_per_mwh: float = Field(..., description="Effective regulatory DSM penalty rate in INR/MWh")
    deviation_charge_inr: float = Field(..., description="Calculated DSM charge/penalty in INR for the 15-min block")

class DSMFinancialSummary(BaseModel):
    plant_id: int
    plant_name: str
    plant_type: str
    capacity_mw: float
    date: str
    total_scheduled_mwh: float
    total_actual_mwh: float
    net_deviation_mwh: float
    mean_absolute_percentage_error: float
    blocks_within_permissible_band: int # <= 10% error
    blocks_moderate_deviation: int # 10% - 15% error
    blocks_critical_violation: int # > 15% error
    total_deviation_charges_inr: float
    compliance_rating: str # 'EXCELLENT', 'COMPLIANT', 'HIGH_PENALTY_RISK'

class DSMReportResponse(BaseModel):
    summary: DSMFinancialSummary
    time_blocks: List[DSMTimeBlockItem]
