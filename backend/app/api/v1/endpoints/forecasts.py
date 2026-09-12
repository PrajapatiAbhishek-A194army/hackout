from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.forecast import (
    FarmForecastResponse,
    AggregatedForecastResponse,
    NationalForecastResponse
)
from app.services import crud
from app.services.forecast_engine import forecast_engine
from app.models.plant import Plant

router = APIRouter()

@router.get("/farm/{plant_id}", response_model=FarmForecastResponse, summary="Get 24h-72h forecast for a specific plant")
def get_farm_forecast(
    plant_id: int,
    horizon_hours: int = Query(24, ge=1, le=72, description="Forecast horizon in hours (24, 48, or 72)"),
    db: Session = Depends(get_db)
):
    """Retrieve hourly generation forecast with uncertainty bounds (P10/P90) and capacity factor for a plant."""
    forecast = crud.get_farm_forecast(db=db, plant_id=plant_id, horizon_hours=horizon_hours)
    # If no stored forecast or fewer points than requested horizon, generate dynamically via ML Forecast Engine
    if not forecast or len(forecast.forecast_points) < horizon_hours:
        plant = db.query(Plant).filter(Plant.id == plant_id).first()
        if not plant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plant with ID {plant_id} not found"
            )
        forecast_engine.generate_plant_forecast(db, plant_id, horizon_hours=horizon_hours, save_to_db=True)
        forecast = crud.get_farm_forecast(db=db, plant_id=plant_id, horizon_hours=horizon_hours)

    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast for plant ID {plant_id} not found"
        )
    return forecast

@router.post("/generate/{plant_id}", summary="Generate and persist 24h, 48h, or 72h forecast using XGBoost")
def trigger_plant_forecast(
    plant_id: int,
    horizon_hours: int = Query(24, ge=1, le=72, description="Forecast horizon: 24, 48, or 72 hours"),
    db: Session = Depends(get_db)
):
    """
    Execute ML Forecast Engine for a specific plant:
    Uses trained Solar/Wind XGBoost models, computes P10/P90 bounds, detects ramp events,
    and commits predictions to the database.
    """
    try:
        return forecast_engine.generate_plant_forecast(
            db=db,
            plant_id=plant_id,
            horizon_hours=horizon_hours,
            save_to_db=True
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )

@router.get("/horizons/{plant_id}", summary="Compare 24h vs 48h vs 72h multi-horizon forecasts")
def get_multi_horizon_comparison(
    plant_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate and contrast generation profiles across 24h, 48h, and 72h horizons,
    displaying confidence score decay and expected daily MWh output.
    """
    try:
        return forecast_engine.generate_multi_horizon(db=db, plant_id=plant_id)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )

@router.post("/generate-all", summary="Batch generate multi-horizon forecasts for all plants")
def trigger_all_plants_forecast(
    horizon_hours: int = Query(72, ge=24, le=72, description="Horizon: 24, 48, or 72 hours"),
    db: Session = Depends(get_db)
):
    """
    Batch generate and persist 72-hour forecasts across all registered
    Indian solar, wind, and hybrid parks.
    """
    results = forecast_engine.generate_all_plants_forecast(db=db, horizon_hours=horizon_hours)
    return {
        "status": "completed",
        "total_plants": len(results),
        "horizon_hours": horizon_hours,
        "results": [
            {
                "plant_id": r["plant_id"],
                "plant_name": r["plant_name"],
                "capacity_mw": r["capacity_mw"],
                "peak_mw": r["peak_generation_mw"],
                "cf_pct": r["capacity_factor_pct"],
                "ramp_events": r["ramp_events_count"]
            }
            for r in results
        ]
    }

@router.get("/region/{region_id}", response_model=AggregatedForecastResponse, summary="Get aggregated regional forecast")
def get_region_forecast(
    region_id: int,
    horizon_hours: int = Query(24, ge=1, le=72, description="Forecast horizon in hours"),
    db: Session = Depends(get_db)
):
    """Retrieve aggregated regional generation forecast summing all active renewable plants in the region."""
    forecast = crud.get_aggregated_forecast(db=db, level="region", entity_id=region_id, horizon_hours=horizon_hours)
    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regional forecast for region ID {region_id} not found"
        )
    return forecast

@router.get("/state/{state_id}", response_model=AggregatedForecastResponse, summary="Get aggregated state forecast")
def get_state_forecast(
    state_id: int,
    horizon_hours: int = Query(24, ge=1, le=72, description="Forecast horizon in hours"),
    db: Session = Depends(get_db)
):
    """Retrieve aggregated state generation forecast summing all active solar and wind farms in the state."""
    forecast = crud.get_aggregated_forecast(db=db, level="state", entity_id=state_id, horizon_hours=horizon_hours)
    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"State forecast for state ID {state_id} not found"
        )
    return forecast

@router.get("/national", response_model=NationalForecastResponse, summary="Get all-India national aggregated forecast")
def get_national_forecast(
    horizon_hours: int = Query(24, ge=1, le=72, description="Forecast horizon in hours"),
    db: Session = Depends(get_db)
):
    """Retrieve all-India aggregated forecast, peak generation time, and solar vs wind contribution breakdown."""
    return crud.get_national_forecast(db=db, horizon_hours=horizon_hours)
