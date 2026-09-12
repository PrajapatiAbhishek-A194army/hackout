from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database.session import get_db
from app.storage.optimizer import bess_dispatch_optimizer, BESSDispatchOptimizer
from app.storage.battery_model import BatteryStorageConfig
from app.schemas.storage import (
    BESSOptimizationResponse,
    BESSSimulateRequest,
    BESSConfig
)

router = APIRouter()

@router.post(
    "/optimize/{plant_id}",
    response_model=BESSOptimizationResponse,
    summary="Optimize BESS Dispatch for Renewable Plant",
    description="Co-optimizes battery storage charge/discharge scheduling for a renewable plant to maximize price arbitrage and curtailment reduction."
)
def optimize_plant_storage(
    plant_id: int = Path(..., description="Renewable plant facility ID"),
    horizon_hours: int = Query(24, ge=1, le=72, description="Forecast horizon in hours (24, 48, 72)"),
    bess_power_mw: Optional[float] = Query(None, description="Battery power capacity in MW (defaults to 20% plant capacity)"),
    bess_energy_mwh: Optional[float] = Query(None, description="Battery energy storage volume in MWh (defaults to 4-hour duration)"),
    grid_limit_factor: float = Query(0.80, ge=0.3, le=1.0, description="Evacuation limit as fraction of plant capacity (default 0.80)"),
    db: Session = Depends(get_db)
):
    try:
        return bess_dispatch_optimizer.optimize_plant_storage(
            db=db,
            plant_id=plant_id,
            horizon_hours=horizon_hours,
            bess_power_mw=bess_power_mw,
            bess_energy_mwh=bess_energy_mwh,
            grid_limit_factor=grid_limit_factor
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage optimization failed: {str(e)}")

@router.get(
    "/profiles/{plant_id}",
    response_model=BESSOptimizationResponse,
    summary="Get Plant BESS Dispatch Profile & Arbitrage",
    description="Retrieves simulated BESS dispatch profiles, dynamic SoC curves, merchant arbitrage cash flows, and avoided curtailment."
)
def get_plant_storage_profile(
    plant_id: int = Path(..., description="Renewable plant facility ID"),
    horizon_hours: int = Query(24, ge=1, le=72),
    grid_limit_factor: float = Query(0.80, ge=0.3, le=1.0),
    db: Session = Depends(get_db)
):
    try:
        return bess_dispatch_optimizer.optimize_plant_storage(
            db=db,
            plant_id=plant_id,
            horizon_hours=horizon_hours,
            grid_limit_factor=grid_limit_factor
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage profile retrieval failed: {str(e)}")

@router.post(
    "/simulate",
    response_model=BESSOptimizationResponse,
    summary="Generic Custom BESS Simulator",
    description="Simulates battery storage dispatch, SoC tracking, and arbitrage for any arbitrary generation profile and tariff curve."
)
def simulate_custom_storage(
    payload: BESSSimulateRequest
):
    try:
        config = BatteryStorageConfig(
            power_capacity_mw=payload.bess_power_mw,
            energy_capacity_mwh=payload.bess_energy_mwh,
            round_trip_efficiency=payload.round_trip_efficiency,
            min_soc_pct=payload.min_soc_pct,
            max_soc_pct=payload.max_soc_pct,
            initial_soc_pct=payload.initial_soc_pct,
            degradation_cost_inr_per_kwh=payload.degradation_cost_inr_per_kwh
        )

        res = BESSDispatchOptimizer.optimize_dispatch(
            generation_profile=payload.generation_profile_mw,
            grid_capacity_limit_mw=payload.grid_capacity_limit_mw,
            bess_config=config,
            tariffs_inr_per_mwh=payload.tariffs_inr_per_mwh
        )

        return BESSOptimizationResponse(
            plant_id=None,
            plant_name="Custom Simulated Facility",
            plant_type="hybrid",
            plant_capacity_mw=max(payload.generation_profile_mw) if payload.generation_profile_mw else 0.0,
            horizon_hours=res["horizon_hours"],
            bess_config=BESSConfig(
                power_capacity_mw=config.power_capacity_mw,
                energy_capacity_mwh=config.energy_capacity_mwh,
                round_trip_efficiency=config.round_trip_efficiency,
                min_soc_pct=config.min_soc_pct,
                max_soc_pct=config.max_soc_pct,
                initial_soc_pct=config.initial_soc_pct,
                degradation_cost_inr_per_kwh=config.degradation_cost_inr_per_kwh
            ),
            financial_summary=res["financial_summary"],
            dispatch_schedule=res["dispatch_schedule"]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Simulation failed: {str(e)}")
