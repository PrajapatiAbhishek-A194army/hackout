from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.weather import WeatherResponse
from app.services import crud

router = APIRouter()

@router.get("/{plant_id}", response_model=List[WeatherResponse], summary="Get weather data and telemetry for a plant")
def get_plant_weather(
    plant_id: int,
    limit: int = Query(48, ge=1, le=168, description="Number of hourly records to return"),
    db: Session = Depends(get_db)
):
    """Retrieve hourly meteorological readings (solar irradiance, wind vectors, ambient metrics) for a given plant."""
    plant = crud.get_plant_by_id(db=db, plant_id=plant_id)
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with ID {plant_id} not found"
        )
    return crud.get_weather_for_plant(db=db, plant_id=plant_id, limit=limit)
