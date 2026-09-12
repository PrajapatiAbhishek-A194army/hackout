from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database.session import get_db
from app.explainability.explainer import explainability_engine
from app.schemas.explainability import (
    GlobalFeatureImportanceResponse,
    ShapWaterfallResponse,
    DriverBreakdownResponse,
    MeteorologicalSensitivityResponse
)

router = APIRouter()

@router.get(
    "/importance/{model_type}",
    response_model=GlobalFeatureImportanceResponse,
    summary="Global Model Feature Importance",
    description="Extracts global gain, frequency weight, and observation cover importance metrics across solar, wind, or hybrid forecasting models."
)
def get_model_feature_importance(
    model_type: str = Path(..., description="Model architecture type: 'solar', 'wind', or 'hybrid'")
):
    try:
        return explainability_engine.get_global_feature_importance(model_type=model_type)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve feature importance: {str(e)}")

@router.get(
    "/shap/{plant_id}",
    response_model=ShapWaterfallResponse,
    summary="Local TreeSHAP Waterfall Explanation",
    description="Computes exact additive TreeSHAP local attribution values for a specific plant and forecast hour, satisfying Base + Sum(SHAP) = Prediction."
)
def get_shap_waterfall(
    plant_id: int = Path(..., description="ID of the renewable energy facility"),
    horizon_hour: int = Query(12, ge=0, le=71, description="Forecast horizon hour index to explain (0-71)"),
    db: Session = Depends(get_db)
):
    try:
        return explainability_engine.compute_shap_waterfall(db=db, plant_id=plant_id, horizon_hour=horizon_hour)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute SHAP waterfall: {str(e)}")

@router.get(
    "/drivers/{plant_id}",
    response_model=DriverBreakdownResponse,
    summary="Physical Weather Driver Attribution",
    description="Aggregates local SHAP values into high-level meteorological driver categories (e.g. Solar Irradiance, Cloud Attenuation, Thermal Derating, Wind Kinetic Energy)."
)
def get_weather_drivers(
    plant_id: int = Path(..., description="ID of the renewable energy facility"),
    horizon_hour: int = Query(12, ge=0, le=71, description="Forecast horizon hour index to explain (0-71)"),
    db: Session = Depends(get_db)
):
    try:
        return explainability_engine.get_driver_breakdown(db=db, plant_id=plant_id, horizon_hour=horizon_hour)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute weather driver breakdown: {str(e)}")

@router.post(
    "/sensitivity/{plant_id}",
    response_model=MeteorologicalSensitivityResponse,
    summary="Meteorological Sensitivity & Elasticity Curve",
    description="Simulates partial dependence response curves and generation elasticity with respect to GHI, Wind Speed, Cloud Cover, or Temperature variations."
)
def get_meteorological_sensitivity(
    plant_id: int = Path(..., description="ID of the renewable energy facility"),
    parameter: str = Query("ghi", description="Weather parameter to stress-test: 'ghi', 'wind_speed', 'cloud_cover', or 'temperature'"),
    horizon_hour: int = Query(12, ge=0, le=71, description="Forecast horizon hour index to simulate (0-71)"),
    db: Session = Depends(get_db)
):
    try:
        return explainability_engine.compute_meteorological_sensitivity(
            db=db,
            plant_id=plant_id,
            parameter=parameter,
            horizon_hour=horizon_hour
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute meteorological sensitivity: {str(e)}")
