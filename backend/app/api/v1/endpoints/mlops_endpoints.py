import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
import numpy as np
import pandas as pd

from app.database.session import get_db
from app.models.model_run import ModelRun
from app.schemas.mlops import (
    ModelType, DriftAnalysisResponse, ModelRetrainRequest,
    ModelRetrainResponse, ModelRunSummary, ModelRollbackRequest
)
from app.mlops.drift_detector import drift_detector
from app.mlops.pipeline import mlops_pipeline, MODELS_DIR
from app.ml.solar_model import SOLAR_FEATURES, SolarForecaster
from app.ml.wind_model import WIND_FEATURES, WindForecaster
from app.ml.synthetic_dataset import generate_synthetic_solar_data, generate_synthetic_wind_data
from app.ml.features import FeatureEngineer

logger = logging.getLogger("backend.api.mlops")

router = APIRouter()

@router.get("/drift/{model_type}", response_model=DriftAnalysisResponse)
def get_model_drift_analysis(
    model_type: ModelType,
    drift_injection: bool = Query(False, description="Simulate seasonal meteorological distribution shift for testing"),
    db: Session = Depends(get_db)
):
    """
    Computes statistical feature drift (PSI, two-sample KS-test) and concept drift (RMSE degradation).
    """
    mtype = model_type.value.lower()

    # 1. Generate baseline reference dataset (historical normal)
    if mtype == "solar":
        df_base = generate_synthetic_solar_data(days=30, capacity_mw=400.0, seed=42)
        meta = {"tilt": 25.0, "azimuth": 180.0, "tracking": "single_axis", "capacity_mw": 400.0}
        X_base, _ = FeatureEngineer.create_feature_matrix(df_base, meta)
        feature_names = SOLAR_FEATURES
        model_path = os.path.join(MODELS_DIR, "solar_xgboost_v1.joblib")
        forecaster = SolarForecaster.load(model_path)

        # Current telemetry dataset
        seed_curr = 999 if drift_injection else 100
        df_curr = generate_synthetic_solar_data(days=14, capacity_mw=400.0, seed=seed_curr)
        if drift_injection:
            # Simulate monsoon cloud cover & high aerosol degradation
            df_curr["cloud_cover"] = np.clip(df_curr["cloud_cover"] * 1.6 + 20, 0, 100)
            df_curr["ghi"] = np.clip(df_curr["ghi"] * 0.65, 0, 1200)

        X_curr, _ = FeatureEngineer.create_feature_matrix(df_curr, meta)
        y_curr = df_curr["generation_mw"].values
        y_pred = forecaster.predict(X_curr)
        baseline_rmse = 16.38

    else: # wind
        df_base = generate_synthetic_wind_data(days=30, capacity_mw=250.0, seed=42)
        meta = {"hub_height": 120.0, "rotor_diameter": 140.0, "cut_in": 3.0, "rated": 12.0, "cut_out": 25.0, "capacity_mw": 250.0}
        _, X_base = FeatureEngineer.create_feature_matrix(df_base, meta)
        feature_names = WIND_FEATURES
        model_path = os.path.join(MODELS_DIR, "wind_xgboost_v1.joblib")
        forecaster = WindForecaster.load(model_path)

        seed_curr = 888 if drift_injection else 100
        df_curr = generate_synthetic_wind_data(days=14, capacity_mw=250.0, seed=seed_curr)
        if drift_injection:
            # Simulate severe low-wind lull
            df_curr["wind_speed"] = np.clip(df_curr["wind_speed"] * 0.5, 0, 30)

        _, X_curr = FeatureEngineer.create_feature_matrix(df_curr, meta)
        y_curr = df_curr["generation_mw"].values
        y_pred = forecaster.predict(X_curr)
        baseline_rmse = 15.04

    # Run statistical drift detector
    drift_result = drift_detector.analyze_model_drift(
        model_type=mtype,
        baseline_features_df=X_base,
        current_features_df=X_curr,
        actual_mw=y_curr,
        predicted_mw=y_pred,
        baseline_rmse_mw=baseline_rmse,
        feature_names=feature_names
    )

    return DriftAnalysisResponse(
        model_type=mtype,
        analyzed_at=datetime.now(),
        sample_size_baseline=drift_result["sample_size_baseline"],
        sample_size_current=drift_result["sample_size_current"],
        overall_drift_status=drift_result["overall_drift_status"],
        recommend_retraining=drift_result["recommend_retraining"],
        concept_drift=drift_result["concept_drift"],
        feature_drift=drift_result["feature_drift"]
    )

@router.post("/retrain", response_model=ModelRetrainResponse)
def trigger_model_retraining(
    request: ModelRetrainRequest,
    db: Session = Depends(get_db)
):
    """
    Triggers Champion-Challenger retraining tournament.
    Promotes challenger only if quality gates are satisfied.
    """
    try:
        result = mlops_pipeline.retrain_and_evaluate(db=db, request=request)
        return ModelRetrainResponse(**result)
    except Exception as e:
        logger.error(f"Retraining failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Model retraining failed: {str(e)}")

@router.get("/models", response_model=List[ModelRunSummary])
def get_model_registry(
    model_type: Optional[ModelType] = None,
    db: Session = Depends(get_db)
):
    """
    Returns audit trail of all model versions registered in the MLOps registry.
    """
    mtype = model_type.value if model_type else None
    runs = mlops_pipeline.list_registry(db, model_type=mtype)
    return [ModelRunSummary.model_validate(r) for r in runs]

@router.post("/rollback", response_model=Dict[str, Any])
def rollback_model_version(
    request: ModelRollbackRequest,
    db: Session = Depends(get_db)
):
    """
    Rolls back the active model to a previous historical version.
    """
    try:
        res = mlops_pipeline.rollback_model(
            db=db,
            model_type=request.model_type.value,
            target_version=request.target_version
        )
        return {"status": "success", "rollback_details": res}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/promote/{version}", response_model=Dict[str, Any])
def promote_model_version(
    version: str = Path(..., description="Target model version string"),
    db: Session = Depends(get_db)
):
    """
    Manually activates a specific model version from the registry as the active Champion.
    """
    target = db.query(ModelRun).filter(ModelRun.version == version).first()
    if not target:
        raise HTTPException(status_code=404, detail=f"Model version '{version}' not found.")

    res = mlops_pipeline.rollback_model(db=db, model_type=target.model_type, target_version=version)
    return {"status": "success", "message": f"Model {version} is now active Champion.", "details": res}
