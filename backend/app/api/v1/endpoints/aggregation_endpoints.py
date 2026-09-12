from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import Optional

from app.database.session import get_db
from app.aggregation.aggregator import aggregation_engine
from app.schemas.forecast import (
    FarmForecastResponse,
    AggregatedForecastResponse,
    NationalForecastResponse,
    HierarchicalTreeResponse
)

router = APIRouter()

@router.get(
    "/national",
    response_model=NationalForecastResponse,
    summary="National Renewable Generation Forecast",
    description="Rolls up 24h, 48h, or 72h renewable generation forecasts across all Indian grid regions with fuel mix breakdowns."
)
def get_national_forecast(
    horizon_hours: int = Query(24, ge=1, le=72, description="Forecast horizon in hours (24, 48, or 72)"),
    db: Session = Depends(get_db)
):
    try:
        return aggregation_engine.aggregate_national(db=db, horizon_hours=horizon_hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate national forecast: {str(e)}")

@router.get(
    "/region/{region_id_or_code}",
    response_model=AggregatedForecastResponse,
    summary="Regional Grid Renewable Forecast",
    description="Bottom-up aggregation of all renewable generation assets within a Regional Load Despatch Centre jurisdiction (e.g. NR, WR, SR)."
)
def get_regional_forecast(
    region_id_or_code: str = Path(..., description="Region ID (e.g. 1) or Region Code (e.g. NR, WR, SR, ER, NER)"),
    horizon_hours: int = Query(24, ge=1, le=72, description="Forecast horizon in hours (24, 48, or 72)"),
    db: Session = Depends(get_db)
):
    try:
        return aggregation_engine.aggregate_region(db=db, region_id_or_code=region_id_or_code, horizon_hours=horizon_hours)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate regional forecast: {str(e)}")

@router.get(
    "/state/{state_id_or_code}",
    response_model=AggregatedForecastResponse,
    summary="State Grid Renewable Forecast",
    description="Bottom-up aggregation of all renewable assets within a State Load Despatch Centre jurisdiction (e.g. RJ, GJ, TN, KA)."
)
def get_state_forecast(
    state_id_or_code: str = Path(..., description="State ID (e.g. 1) or State Code (e.g. RJ, GJ, TN, KA, MH)"),
    horizon_hours: int = Query(24, ge=1, le=72, description="Forecast horizon in hours (24, 48, or 72)"),
    db: Session = Depends(get_db)
):
    try:
        return aggregation_engine.aggregate_state(db=db, state_id_or_code=state_id_or_code, horizon_hours=horizon_hours)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate state forecast: {str(e)}")

@router.get(
    "/farm/{plant_id_or_code}",
    response_model=FarmForecastResponse,
    summary="Individual Plant Generation Forecast",
    description="High-resolution solar/wind/hybrid generation forecast for an individual renewable energy facility."
)
def get_farm_forecast(
    plant_id_or_code: str = Path(..., description="Plant ID (e.g. 1) or Plant Code (e.g. BHADLA_SOLAR_01)"),
    horizon_hours: int = Query(24, ge=1, le=72, description="Forecast horizon in hours (24, 48, or 72)"),
    db: Session = Depends(get_db)
):
    try:
        return aggregation_engine.aggregate_farm(db=db, plant_id_or_code=plant_id_or_code, horizon_hours=horizon_hours)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate farm forecast: {str(e)}")

@router.get(
    "/hierarchy",
    response_model=HierarchicalTreeResponse,
    summary="Grid Drill-Down Navigation Tree",
    description="Returns the full hierarchical drill-down navigation tree from National Grid to Regions, States, and Renewable Facilities."
)
def get_grid_hierarchy(db: Session = Depends(get_db)):
    try:
        return aggregation_engine.get_hierarchical_tree(db=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve grid hierarchy: {str(e)}")
