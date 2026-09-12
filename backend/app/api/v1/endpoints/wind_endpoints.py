import os
import json
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
import pandas as pd

from app.database.session import get_db
from app.models.plant import Plant
from app.models.weather import Weather
from app.models.model_run import ModelRun
from app.data_pipeline.metadata_manager import PlantMetadataManager
from app.ml.features import FeatureEngineer
from app.ml.wind_model import WindForecaster
from app.ml.train_wind import train_and_register_wind_model

router = APIRouter()

# Global predictor cache
_wind_model_cache: Optional[WindForecaster] = None

def get_wind_model() -> WindForecaster:
    global _wind_model_cache
    if _wind_model_cache is not None:
        return _wind_model_cache

    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    model_path = os.path.join(backend_dir, "trained_models", "wind_xgboost_v1.joblib")

    if os.path.exists(model_path):
        _wind_model_cache = WindForecaster.load(model_path)
        return _wind_model_cache
    else:
        # If not trained yet, train on-the-fly
        _wind_model_cache = train_and_register_wind_model(days=90)
        return _wind_model_cache

@router.post("/train", summary="Train and register Wind XGBoost model")
def train_wind_model(
    days: int = Query(90, ge=30, le=365, description="Number of historical days to synthesize for training")
):
    """
    Train a new production XGBoost Wind Forecaster, evaluate on 20% test split,
    persist artifact to disk, and update the database model registry.
    """
    global _wind_model_cache
    forecaster = train_and_register_wind_model(days=days)
    _wind_model_cache = forecaster

    return {
        "status": "success",
        "model_name": "wind_xgboost_ensemble",
        "version": "v1.0.0-wind-xgb",
        "metrics": forecaster.metrics,
        "top_features": list(forecaster.feature_importance.items())[:8]
    }

@router.get("/metrics", summary="Get active Wind model metrics and feature importance")
def get_wind_metrics(db: Session = Depends(get_db)):
    """Retrieve performance scores and aerodynamic feature importances for the active wind model."""
    run = db.query(ModelRun).filter(
        ModelRun.model_type == "wind",
        ModelRun.is_active == True
    ).order_by(ModelRun.training_date.desc()).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active wind model found in registry"
        )

    return {
        "model_name": run.model_name,
        "version": run.version,
        "training_date": run.training_date,
        "mae_mw": run.mae_mw,
        "rmse_mw": run.rmse_mw,
        "r2_score": run.r2_score,
        "parameters": json.loads(run.parameters) if run.parameters else {},
        "feature_importance": json.loads(run.feature_importance) if run.feature_importance else {},
        "model_path": run.model_path
    }

@router.post("/predict/{plant_id}", summary="Predict hourly wind generation with uncertainty intervals")
def predict_wind_generation(
    plant_id: int,
    horizon_hours: int = Query(24, ge=1, le=72, description="Forecast horizon in hours (24, 48, 72)"),
    db: Session = Depends(get_db)
):
    """
    Execute inference with active Wind XGBoost model for a given plant:
    Applies aerodynamic features, predicts expected MW, P10 lower bound, P90 upper bound,
    and confidence scores. Enforces physical cut-in and cut-out turbine boundaries.
    """
    metadata = PlantMetadataManager.get_plant_metadata(db, plant_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with ID {plant_id} not found"
        )

    if metadata["plant_type"] not in ("wind", "hybrid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plant {metadata['name']} is a {metadata['plant_type']} plant; use appropriate forecaster."
        )

    # Fetch weather records for plant
    records = db.query(Weather).filter(
        Weather.plant_id == plant_id
    ).order_by(Weather.timestamp.asc()).limit(horizon_hours).all()

    if not records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No weather records found for plant {plant_id}. Run data pipeline first."
        )

    weather_data = [
        {
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
        }
        for w in records
    ]
    df_weather = pd.DataFrame(weather_data)

    # Feature transformation
    _, X_wind = FeatureEngineer.create_feature_matrix(df_weather, metadata)

    # Run inference
    forecaster = get_wind_model()
    cap = float(metadata["capacity_mw"]) * (0.4 if metadata["plant_type"] == "hybrid" else 1.0)
    intervals_df = forecaster.predict_with_intervals(X_wind, capacity_mw=cap)

    points = []
    for i, row in intervals_df.iterrows():
        points.append({
            "timestamp": df_weather["timestamp"].iloc[i],
            "predicted_mw": row["predicted_mw"],
            "lower_bound_mw": row["lower_bound_mw"],
            "upper_bound_mw": row["upper_bound_mw"],
            "confidence_score": row["confidence_score"]
        })

    mw_vals = [p["predicted_mw"] for p in points]
    peak_mw = max(mw_vals) if mw_vals else 0.0
    avg_mw = sum(mw_vals) / len(mw_vals) if mw_vals else 0.0

    return {
        "plant_id": plant_id,
        "plant_name": metadata["name"],
        "plant_type": metadata["plant_type"],
        "effective_capacity_mw": cap,
        "horizon_hours": horizon_hours,
        "peak_predicted_mw": round(peak_mw, 2),
        "average_predicted_mw": round(avg_mw, 2),
        "capacity_factor_pct": round(avg_mw / cap * 100, 2) if cap > 0 else 0.0,
        "forecast_points": points
    }
