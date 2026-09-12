from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
import pandas as pd

from app.database.session import get_db
from app.models.plant import Plant
from app.models.weather import Weather
from app.data_pipeline.metadata_manager import PlantMetadataManager
from app.ml.features import FeatureEngineer, SOLAR_FEATURES, WIND_FEATURES

router = APIRouter()

@router.get("/schema", summary="Get feature dictionary and technical specifications")
def get_features_schema():
    """Retrieve full definitions and groupings of engineered solar and wind features."""
    return {
        "solar_features_count": len(SOLAR_FEATURES),
        "wind_features_count": len(WIND_FEATURES),
        "solar_features": SOLAR_FEATURES,
        "wind_features": WIND_FEATURES,
        "feature_categories": {
            "meteorological": ["ghi", "dni", "dhi", "effective_ghi", "wind_power_density", "air_density_kg_m3"],
            "temporal_cyclical": ["hour_sin", "hour_cos", "day_sin", "day_cos", "month_sin", "month_cos"],
            "lags_and_dynamics": ["ghi_lag_1", "ghi_ramp_1h", "wind_100m_lag_1", "wind_ramp_1h", "rolling_means"],
            "site_engineering": ["capacity_mw", "latitude", "longitude", "elevation_m", "tilt_angle_deg", "hub_height_m"]
        }
    }

@router.post("/extract/{plant_id}", summary="Extract engineered feature matrix for a plant")
def extract_plant_features(
    plant_id: int,
    limit: int = Query(48, ge=1, le=168, description="Number of recent weather hours to transform"),
    db: Session = Depends(get_db)
):
    """
    Extract production-ready feature matrix from stored meteorological telemetry
    for a given renewable plant.
    """
    metadata = PlantMetadataManager.get_plant_metadata(db, plant_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with ID {plant_id} not found"
        )

    # Fetch weather records
    weather_records = db.query(Weather).filter(
        Weather.plant_id == plant_id
    ).order_by(Weather.timestamp.desc()).limit(limit).all()

    if not weather_records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No weather records found for plant {plant_id}. Run data pipeline first."
        )

    # Order ascending for sequential time-series feature engineering
    weather_records.reverse()

    data = []
    for w in weather_records:
        data.append({
            "timestamp": w.timestamp,
            "temperature_c": w.temperature_c,
            "relative_humidity": w.relative_humidity,
            "surface_pressure_hpa": w.surface_pressure_hpa,
            "cloud_cover_pct": w.cloud_cover_pct,
            "ghi": w.ghi,
            "dni": w.dni,
            "dhi": w.dhi,
            "wind_speed_10m": w.wind_speed_10m,
            "wind_speed_100m": w.wind_speed_100m,
            "wind_direction_deg": w.wind_direction_deg
        })

    df = pd.DataFrame(data)
    X_solar, X_wind = FeatureEngineer.create_feature_matrix(df, metadata)

    plant_type = metadata["plant_type"]
    target_matrix = X_solar if plant_type == "solar" else (X_wind if plant_type == "wind" else X_solar)

    return {
        "plant_id": plant_id,
        "plant_name": metadata["name"],
        "plant_type": plant_type,
        "records_transformed": len(target_matrix),
        "features_count": target_matrix.shape[1],
        "feature_names": list(target_matrix.columns),
        "sample_features": target_matrix.tail(5).to_dict(orient="records")
    }
