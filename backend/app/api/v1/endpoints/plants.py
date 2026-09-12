from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.plant import PlantResponse, PlantDetailResponse, PlantCreate
from app.services import crud

router = APIRouter()

@router.get("", response_model=List[PlantResponse], summary="List all renewable plants")
def get_plants(
    plant_type: Optional[str] = Query(None, description="Filter by 'solar', 'wind', or 'hybrid'"),
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    state_id: Optional[int] = Query(None, description="Filter by state ID"),
    status: Optional[str] = Query(None, description="Filter by status: 'active', 'curtailed', etc."),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Retrieve list of registered solar, wind, and hybrid plants across India."""
    return crud.get_plants(
        db=db,
        plant_type=plant_type,
        region_id=region_id,
        state_id=state_id,
        status=status,
        skip=skip,
        limit=limit
    )

@router.get("/{plant_id}", response_model=PlantDetailResponse, summary="Get plant details by ID")
def get_plant_detail(
    plant_id: int,
    db: Session = Depends(get_db)
):
    """Get full details of a specific generation plant including region and state information."""
    plant = crud.get_plant_by_id(db=db, plant_id=plant_id)
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with ID {plant_id} not found"
        )
    
    # Enrich with region name and latest weather/alerts
    weather_list = crud.get_weather_for_plant(db=db, plant_id=plant_id, limit=1)
    latest_weather = weather_list[0] if weather_list else None
    
    alerts = crud.get_alerts(db=db, plant_id=plant_id, status="active")
    farm_fc = crud.get_farm_forecast(db=db, plant_id=plant_id, horizon_hours=1)
    curr_fc_mw = farm_fc.forecast_points[0].predicted_mw if farm_fc and farm_fc.forecast_points else None

    return PlantDetailResponse(
        id=plant.id,
        name=plant.name,
        code=plant.code,
        plant_type=plant.plant_type,
        capacity_mw=plant.capacity_mw,
        latitude=plant.latitude,
        longitude=plant.longitude,
        elevation_m=plant.elevation_m,
        technology=plant.technology,
        commissioning_year=plant.commissioning_year,
        operator_name=plant.operator_name,
        status=plant.status,
        region_id=plant.region_id,
        state_id=plant.state_id,
        created_at=plant.created_at,
        updated_at=plant.updated_at,
        region_name=plant.region.name if plant.region else None,
        state_name=plant.state.name if plant.state else None,
        current_forecast_mw=curr_fc_mw,
        current_weather_ghi=latest_weather.ghi if latest_weather else None,
        current_wind_speed=latest_weather.wind_speed_100m if latest_weather else None,
        active_alerts_count=len(alerts)
    )

@router.post("", response_model=PlantResponse, status_code=status.HTTP_201_CREATED, summary="Register a new renewable plant")
def create_plant(
    plant_in: PlantCreate,
    db: Session = Depends(get_db)
):
    """Register a new renewable energy generation facility."""
    existing = crud.get_plant_by_code(db=db, code=plant_in.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plant with code '{plant_in.code}' already exists"
        )
    return crud.create_plant(db=db, plant_in=plant_in)
