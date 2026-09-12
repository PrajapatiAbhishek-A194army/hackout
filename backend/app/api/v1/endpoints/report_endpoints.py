import os
import logging
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.report import ReportRecord
from app.models.plant import Plant
from app.schemas.report import (
    ReportFormat, ReportType, ReportGenerateRequest,
    ReportMetadataResponse, ReportHistoryResponse, DSMReportResponse
)
from app.reports.service import report_service
from app.reports.dsm_calculator import dsm_calculator
from app.services.forecast_engine import forecast_engine
import numpy as np

logger = logging.getLogger("backend.api.reports")

router = APIRouter()

@router.get("/types", response_model=dict)
def get_report_types():
    """
    Returns available report types, descriptions, and supported export file formats.
    """
    return {
        "supported_formats": [f.value for f in ReportFormat],
        "report_types": [
            {
                "type": ReportType.CERC_DSM.value,
                "name": "CERC Deviation Settlement Mechanism (DSM)",
                "description": "Standard Indian 96 time-block regulatory schedule with Available Capacity (AvC), percentage error bands (±10%, ±15%), and graded DSM charges in INR.",
                "scope": "plant"
            },
            {
                "type": ReportType.DAILY_GENERATION.value,
                "name": "Daily Plant Generation & Dispatch Report",
                "description": "Hourly forecasted generation, baseline comparisons, Capacity Utilization Factor (CUF %), and revenue estimation.",
                "scope": "plant"
            },
            {
                "type": ReportType.REGIONAL_GRID_CODE.value,
                "name": "Regional Grid Code & SLDC Summary",
                "description": "Aggregated regional solar and wind profile for SLDC and RLDC dispatch planning.",
                "scope": "region"
            },
            {
                "type": ReportType.BESS_DISPATCH_AUDIT.value,
                "name": "BESS Battery Co-Optimization Audit",
                "description": "BESS state-of-charge schedule, avoided curtailment, battery cycle degradation, and price arbitrage net revenue.",
                "scope": "plant"
            }
        ]
    }

@router.post("/generate", response_model=ReportMetadataResponse)
def generate_report(
    request: ReportGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Triggers on-demand generation and archival of an operational or regulatory report.
    Returns file metadata and download link.
    """
    try:
        record = report_service.generate_report(db=db, request=request)
        return ReportMetadataResponse(
            report_id=record.report_id,
            title=record.title,
            report_type=record.report_type,
            format=record.format,
            plant_id=record.plant_id,
            region_id=record.region_id,
            file_size_bytes=record.file_size_bytes,
            download_url=f"/api/v1/reports/download/{record.report_id}",
            status=record.status,
            created_at=record.created_at
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to generate report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Report generation error: {str(e)}")

@router.get("/download/{report_id}")
def download_report(
    report_id: str = Path(..., description="UUID of the generated report"),
    db: Session = Depends(get_db)
):
    """
    Downloads or streams the archived report file (CSV, XLSX, HTML, JSON).
    """
    try:
        file_path, mime_type, filename = report_service.get_report_file(db, report_id)
        return FileResponse(
            path=file_path,
            media_type=mime_type,
            filename=filename
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")

@router.get("/dsm/{plant_id}", response_model=DSMReportResponse)
def get_dsm_report(
    plant_id: int = Path(..., description="Plant ID"),
    date_str: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (default: today)"),
    db: Session = Depends(get_db)
):
    """
    Direct endpoint for frontend visualization: returns full 96-time block DSM schedule
    and financial summary in JSON format.
    """
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail=f"Plant {plant_id} not found.")

    target_date = date.today()
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            target_date = date.today()

    fc = forecast_engine.generate_plant_forecast(db=db, plant_id=plant.id, horizon_hours=24, save_to_db=False)
    actual_profile = [p["predicted_mw"] for p in fc["forecast_points"]]

    np.random.seed(plant.id + 42)
    sched_noise = np.random.normal(1.0, 0.06, len(actual_profile))
    schedule_profile = [round(max(0.0, a * factor), 2) for a, factor in zip(actual_profile, sched_noise)]

    dsm_res = dsm_calculator.calculate_dsm(
        plant_id=plant.id,
        plant_name=plant.name,
        plant_type=plant.plant_type,
        capacity_mw=float(plant.capacity_mw),
        target_date=target_date,
        hourly_schedule_mw=schedule_profile,
        hourly_actual_mw=actual_profile
    )

    return dsm_res

@router.get("/history", response_model=ReportHistoryResponse)
def list_report_history(
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Lists historical generated reports ordered by creation time.
    """
    records = db.query(ReportRecord).order_by(ReportRecord.created_at.desc()).limit(limit).all()
    items = []
    for r in records:
        items.append(
            ReportMetadataResponse(
                report_id=r.report_id,
                title=r.title,
                report_type=r.report_type,
                format=r.format,
                plant_id=r.plant_id,
                region_id=r.region_id,
                file_size_bytes=r.file_size_bytes,
                download_url=f"/api/v1/reports/download/{r.report_id}",
                status=r.status,
                created_at=r.created_at
            )
        )
    return ReportHistoryResponse(total_count=len(items), reports=items)

@router.delete("/{report_id}")
def delete_report(
    report_id: str = Path(..., description="Report UUID"),
    db: Session = Depends(get_db)
):
    """
    Deletes report record and cleans up archived file.
    """
    record = db.query(ReportRecord).filter(ReportRecord.report_id == report_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Report not found")

    if os.path.exists(record.file_path):
        try:
            os.remove(record.file_path)
        except OSError as e:
            logger.warning(f"Could not delete physical file: {e}")

    db.delete(record)
    db.commit()
    return {"status": "success", "message": f"Report {report_id} deleted."}
