from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.data_pipeline import data_pipeline, PlantMetadataManager, OpenMeteoClient, NasaPowerClient
from app.models.plant import Plant
from app.models.weather import Weather

router = APIRouter()

@router.post("/trigger/{plant_id}", summary="Trigger data ingestion pipeline for a plant")
def trigger_pipeline_for_plant(
    plant_id: int,
    forecast_days: int = Query(3, ge=1, le=7, description="Number of forecast days (1 to 7)"),
    db: Session = Depends(get_db)
):
    """
    Fetch numerical weather predictions (Open-Meteo), validate physical parameters,
    and persist clean meteorological telemetry for the plant into the database.
    """
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with ID {plant_id} not found"
        )

    result = data_pipeline.run_for_plant(
        db=db,
        plant_id=plant_id,
        forecast_days=forecast_days,
        save_to_db=True
    )
    return result

@router.post("/trigger-all", summary="Trigger data ingestion pipeline for all registered plants")
def trigger_pipeline_all(
    forecast_days: int = Query(3, ge=1, le=7, description="Number of forecast days (1 to 7)"),
    db: Session = Depends(get_db)
):
    """
    Execute batch weather data ingestion and validation across all active renewable energy parks.
    """
    results = data_pipeline.run_for_all_plants(
        db=db,
        forecast_days=forecast_days,
        save_to_db=True
    )
    return {
        "status": "completed",
        "total_plants_processed": len(results),
        "results": results
    }

@router.get("/status/{plant_id}", summary="Get data pipeline telemetry and validation status for a plant")
def get_pipeline_status(
    plant_id: int,
    db: Session = Depends(get_db)
):
    """
    Inspect pipeline health, latest ingested records count, and metadata parameters for a given plant.
    """
    metadata = PlantMetadataManager.get_plant_metadata(db, plant_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with ID {plant_id} not found"
        )

    total_records = db.query(Weather).filter(Weather.plant_id == plant_id).count()
    latest_record = db.query(Weather).filter(Weather.plant_id == plant_id).order_by(Weather.timestamp.desc()).first()

    return {
        "plant_id": plant_id,
        "plant_name": metadata["name"],
        "plant_type": metadata["plant_type"],
        "coordinates": {"lat": metadata["latitude"], "lon": metadata["longitude"]},
        "total_weather_records": total_records,
        "latest_weather_timestamp": latest_record.timestamp if latest_record else None,
        "latest_ghi": latest_record.ghi if latest_record else None,
        "latest_wind_100m": latest_record.wind_speed_100m if latest_record else None,
        "engineering_benchmarks": metadata["engineering_params"]
    }
