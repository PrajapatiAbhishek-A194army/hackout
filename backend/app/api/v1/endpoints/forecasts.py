from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.forecast import (
    FarmForecastResponse,
    AggregatedForecastResponse,
    NationalForecastResponse
)
from app.services import crud

router = APIRouter()

@router.get("/farm/{plant_id}", response_model=FarmForecastResponse, summary="Get 24h-72h forecast for a specific plant")
def get_farm_forecast(
    plant_id: int,
    horizon_hours: int = Query(24, ge=1, le=72, description="Forecast horizon in hours (24, 48, or 72)"),
    db: Session = Depends(get_db)
):
    """Retrieve hourly generation forecast with uncertainty bounds (P10/P90) and capacity factor for a plant."""
    forecast = crud.get_farm_forecast(db=db, plant_id=plant_id, horizon_hours=horizon_hours)
    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast for plant ID {plant_id} not found"
        )
    return forecast

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
