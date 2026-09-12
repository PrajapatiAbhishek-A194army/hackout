import os
import uuid
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np

from app.models.plant import Plant
from app.models.region_state import Region
from app.models.report import ReportRecord
from app.schemas.report import ReportType, ReportFormat, ReportGenerateRequest, ReportMetadataResponse
from app.services.forecast_engine import forecast_engine
from app.aggregation.aggregator import aggregation_engine
from app.storage.optimizer import bess_dispatch_optimizer
from app.reports.dsm_calculator import dsm_calculator
from app.reports.generators import (
    export_to_csv, export_to_xlsx, export_to_html_report, export_to_json
)

logger = logging.getLogger("backend.reports.service")

REPORTS_ARCHIVE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "reports_archive")
)
os.makedirs(REPORTS_ARCHIVE_DIR, exist_ok=True)

class ReportService:
    """
    Central reporting and export management service.
    Orchestrates dataset compilation, multi-format export generation,
    file archiving, and database registration.
    """

    @staticmethod
    def get_mime_type(fmt: str) -> str:
        mapping = {
            "csv": "text/csv; charset=utf-8",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "html": "text/html; charset=utf-8",
            "json": "application/json; charset=utf-8"
        }
        return mapping.get(fmt.lower(), "application/octet-stream")

    @classmethod
    def generate_report(
        cls,
        db: Session,
        request: ReportGenerateRequest
    ) -> ReportRecord:
        """
        Executes report generation based on the requested type and format,
        writes file to archive, and registers in database.
        """
        report_id = str(uuid.uuid4())
        target_date = date.today()
        if request.date_str:
            try:
                target_date = datetime.strptime(request.date_str, "%Y-%m-%d").date()
            except ValueError:
                target_date = date.today()

        # -------------------------------------------------------------
        # 1. Compile Data Based on Report Type
        # -------------------------------------------------------------
        if request.report_type == ReportType.CERC_DSM:
            raw_data = cls._build_dsm_data(db, request.plant_id, target_date)
            default_title = f"CERC DSM 96-Block Regulatory Schedule - {raw_data['plant_name']}"
            sheets = {"DSM 96-Block Schedule": raw_data["time_blocks_df"]}
            primary_df = raw_data["time_blocks_df"]
            metadata = raw_data["summary"]
            tables = [{
                "title": "96 Time-Block Generation & Deviation Schedule",
                "description": "Standard 15-minute grid time-blocks evaluated against CERC permissible error bands (±10%, ±15%).",
                "dataframe": raw_data["time_blocks_df"]
            }]

        elif request.report_type == ReportType.DAILY_GENERATION:
            raw_data = cls._build_daily_generation_data(db, request.plant_id, request.horizon_hours, target_date)
            default_title = f"Daily Plant Generation & Dispatch Report - {raw_data['plant_name']}"
            sheets = {
                "Hourly Dispatch": raw_data["hourly_df"],
                "Operational Summary": pd.DataFrame([raw_data["summary"]])
            }
            primary_df = raw_data["hourly_df"]
            metadata = raw_data["summary"]
            tables = [{
                "title": f"Hourly Generation Profile ({request.horizon_hours} Hours)",
                "description": "Forecasted power output, capacity factor, baseline comparison, and calculated revenue.",
                "dataframe": raw_data["hourly_df"]
            }]

        elif request.report_type == ReportType.REGIONAL_GRID_CODE:
            raw_data = cls._build_regional_grid_data(db, request.region_id, request.horizon_hours)
            default_title = f"Regional Grid Code & SLDC Summary Report - {raw_data['region_name']}"
            sheets = {
                "Regional Summary": pd.DataFrame([raw_data["summary"]]),
                "Hourly Mix": raw_data["hourly_df"]
            }
            primary_df = raw_data["hourly_df"]
            metadata = raw_data["summary"]
            tables = [{
                "title": "Regional Renewable Generation Mix",
                "description": "Hourly aggregate solar and wind dispatch for SLDC / RLDC compliance.",
                "dataframe": raw_data["hourly_df"]
            }]

        elif request.report_type == ReportType.BESS_DISPATCH_AUDIT:
            raw_data = cls._build_bess_audit_data(db, request.plant_id, request.horizon_hours)
            default_title = f"BESS Battery Co-Optimization & Arbitrage Audit - {raw_data['plant_name']}"
            sheets = {
                "BESS Schedule": raw_data["hourly_df"],
                "Financial Summary": pd.DataFrame([raw_data["summary"]])
            }
            primary_df = raw_data["hourly_df"]
            metadata = raw_data["summary"]
            tables = [{
                "title": "BESS Dispatch, State-of-Charge & Cash-Flow Schedule",
                "description": "Hourly charging, discharging, curtailment absorption, and revenue trajectory.",
                "dataframe": raw_data["hourly_df"]
            }]
        else:
            raise ValueError(f"Unsupported report type: {request.report_type}")

        title = request.custom_title or default_title

        # -------------------------------------------------------------
        # 2. Format Export File Bytes
        # -------------------------------------------------------------
        fmt = request.format.value.lower()
        if fmt == ReportFormat.CSV.value:
            content_bytes = export_to_csv(primary_df)
            ext = "csv"
        elif fmt == ReportFormat.XLSX.value:
            content_bytes = export_to_xlsx(sheets, title=title, metadata=metadata)
            ext = "xlsx"
        elif fmt == ReportFormat.HTML.value:
            content_bytes = export_to_html_report(
                title=title,
                subtitle=f"Target Date: {target_date} • Type: {request.report_type.value.upper()}",
                metadata=metadata,
                tables=tables
            )
            ext = "html"
        elif fmt == ReportFormat.JSON.value:
            json_payload = {
                "report_id": report_id,
                "title": title,
                "report_type": request.report_type.value,
                "format": fmt,
                "generated_at": datetime.now().isoformat(),
                "metadata": metadata,
                "data": json.loads(primary_df.to_json(orient="records", date_format="iso"))
            }
            content_bytes = export_to_json(json_payload)
            ext = "json"
        else:
            raise ValueError(f"Unsupported export format: {fmt}")

        # -------------------------------------------------------------
        # 3. Archive File to Disk & Save Database Record
        # -------------------------------------------------------------
        filename = f"{request.report_type.value}_{report_id}.{ext}"
        file_path = os.path.join(REPORTS_ARCHIVE_DIR, filename)

        with open(file_path, "wb") as f:
            f.write(content_bytes)

        file_size = len(content_bytes)

        record = ReportRecord(
            report_id=report_id,
            title=title,
            report_type=request.report_type.value,
            format=fmt,
            plant_id=request.plant_id,
            region_id=request.region_id,
            file_path=file_path,
            file_size_bytes=file_size,
            parameters_json=json.dumps(request.model_dump(), default=str),
            status="completed"
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info(f"Report generated: ID={report_id}, Type={request.report_type.value}, Format={fmt}, Size={file_size} bytes")
        return record

    @classmethod
    def get_report_file(cls, db: Session, report_id: str) -> Tuple[str, str, str]:
        """
        Retrieves report file path, MIME type, and download filename.
        """
        record = db.query(ReportRecord).filter(ReportRecord.report_id == report_id).first()
        if not record:
            raise ValueError(f"Report with ID '{report_id}' not found.")

        if not os.path.exists(record.file_path):
            raise FileNotFoundError(f"Report archive file missing at {record.file_path}")

        mime_type = cls.get_mime_type(record.format)
        clean_title = "".join(c for c in record.title if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
        filename = f"{clean_title}.{record.format}"

        return record.file_path, mime_type, filename

    # -------------------------------------------------------------
    # Helper Data Builders
    # -------------------------------------------------------------

    @staticmethod
    def _build_dsm_data(db: Session, plant_id: Optional[int], target_date: date) -> Dict[str, Any]:
        if not plant_id:
            plant = db.query(Plant).first()
        else:
            plant = db.query(Plant).filter(Plant.id == plant_id).first()
        if not plant:
            raise ValueError(f"Plant ID {plant_id} not found.")

        # Generate live 24h plant forecast for actuals
        fc = forecast_engine.generate_plant_forecast(db=db, plant_id=plant.id, horizon_hours=24, save_to_db=False)
        actual_profile = [p["predicted_mw"] for p in fc["forecast_points"]]

        # Synthetic day-ahead schedule (forecast with ±5-12% market bidding deviation)
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

        df = pd.DataFrame(dsm_res["time_blocks"])
        return {
            "plant_name": plant.name,
            "summary": dsm_res["summary"],
            "time_blocks_df": df
        }

    @staticmethod
    def _build_daily_generation_data(db: Session, plant_id: Optional[int], horizon_hours: int, target_date: date) -> Dict[str, Any]:
        if not plant_id:
            plant = db.query(Plant).first()
        else:
            plant = db.query(Plant).filter(Plant.id == plant_id).first()
        if not plant:
            raise ValueError(f"Plant ID {plant_id} not found.")

        fc = forecast_engine.generate_plant_forecast(db=db, plant_id=plant.id, horizon_hours=horizon_hours, save_to_db=False)
        points = fc["forecast_points"]

        rows = []
        cap_mw = float(plant.capacity_mw)
        total_mwh = 0.0
        peak_mw = 0.0
        total_rev = 0.0

        for idx, pt in enumerate(points):
            gen = pt["predicted_mw"]
            base = pt.get("baseline_mw", round(gen * 0.96, 2))
            cuf = round((gen / cap_mw * 100.0) if cap_mw > 0 else 0.0, 2)
            total_mwh += gen
            peak_mw = max(peak_mw, gen)

            # Tariff estimation (avg Rs 3.50/kWh -> Rs 3500/MWh)
            rev = round(gen * 3500.0, 2)
            total_rev += rev

            rows.append({
                "Hour": idx + 1,
                "Timestamp": pt["timestamp"],
                "Predicted Generation (MW)": gen,
                "Baseline Generation (MW)": base,
                "Capacity Utilization (%)": cuf,
                "Confidence Lower Bound (MW)": pt.get("lower_bound_mw", round(gen * 0.90, 2)),
                "Confidence Upper Bound (MW)": pt.get("upper_bound_mw", round(gen * 1.10, 2)),
                "Confidence Score": pt.get("confidence_score", 0.92),
                "Estimated Revenue (INR)": rev
            })

        df = pd.DataFrame(rows)
        avg_cuf = round((total_mwh / (cap_mw * horizon_hours) * 100.0) if cap_mw > 0 else 0.0, 2)

        summary = {
            "plant_id": plant.id,
            "plant_name": plant.name,
            "plant_type": plant.plant_type,
            "capacity_mw": cap_mw,
            "horizon_hours": horizon_hours,
            "total_generation_mwh": round(total_mwh, 2),
            "peak_generation_mw": round(peak_mw, 2),
            "average_cuf_pct": avg_cuf,
            "total_estimated_revenue_inr": round(total_rev, 2)
        }

        return {
            "plant_name": plant.name,
            "summary": summary,
            "hourly_df": df
        }

    @staticmethod
    def _build_regional_grid_data(db: Session, region_id: Optional[int], horizon_hours: int) -> Dict[str, Any]:
        if not region_id:
            region = db.query(Region).first()
        else:
            region = db.query(Region).filter(Region.id == region_id).first()
        if not region:
            raise ValueError(f"Region ID {region_id} not found.")

        agg_res = aggregation_engine.aggregate_region(db=db, region_id_or_code=region.id, horizon_hours=horizon_hours)
        summary_meta = {
            "region_id": region.id,
            "region_name": region.name,
            "total_capacity_mw": agg_res["total_capacity_mw"],
            "installed_solar_mw": agg_res["installed_solar_mw"],
            "installed_wind_mw": agg_res["installed_wind_mw"],
            "peak_generation_mw": agg_res["peak_generation_mw"],
            "expected_total_mwh": agg_res["expected_total_mwh"],
            "capacity_factor_pct": agg_res["capacity_factor_pct"]
        }
        profile = agg_res["forecast_points"]

        rows = []
        for idx, p in enumerate(profile):
            total_gen = p["predicted_mw"]
            sol = p.get("solar_mw", 0.0)
            wnd = p.get("wind_mw", 0.0)
            rows.append({
                "Hour Index": idx + 1,
                "Timestamp": p["timestamp"],
                "Total Generation (MW)": total_gen,
                "Solar Generation (MW)": sol,
                "Wind Generation (MW)": wnd,
                "Solar Share (%)": round((sol / total_gen * 100) if total_gen > 0 else 0.0, 2),
                "Wind Share (%)": round((wnd / total_gen * 100) if total_gen > 0 else 0.0, 2)
            })

        df = pd.DataFrame(rows)
        return {
            "region_name": region.name,
            "summary": summary_meta,
            "hourly_df": df
        }

    @staticmethod
    def _build_bess_audit_data(db: Session, plant_id: Optional[int], horizon_hours: int) -> Dict[str, Any]:
        if not plant_id:
            plant = db.query(Plant).first()
        else:
            plant = db.query(Plant).filter(Plant.id == plant_id).first()
        if not plant:
            raise ValueError(f"Plant ID {plant_id} not found.")

        bess_res = bess_dispatch_optimizer.optimize_plant_storage(db=db, plant_id=plant.id, horizon_hours=horizon_hours)
        sched = bess_res["dispatch_schedule"]
        fin = bess_res["financial_summary"]

        rows = []
        for s in sched:
            rows.append({
                "Hour": s["hour_index"] + 1,
                "Timestamp": s["timestamp"],
                "Generation (MW)": s["generation_mw"],
                "Grid Limit (MW)": s["grid_limit_mw"],
                "BESS Charge (MW)": s["bess_charge_mw"],
                "BESS Discharge (MW)": s["bess_discharge_mw"],
                "Net Injected (MW)": s["net_grid_mw"],
                "Stored Energy (MWh)": s["stored_energy_mwh"],
                "State of Charge (%)": s["soc_pct"],
                "Tariff (INR/MWh)": s["tariff_inr_per_mwh"],
                "Cash Flow (INR)": s["cash_flow_inr"]
            })

        df = pd.DataFrame(rows)
        return {
            "plant_name": plant.name,
            "summary": fin,
            "hourly_df": df
        }

report_service = ReportService()
