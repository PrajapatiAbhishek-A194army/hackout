from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.session import get_db
from app.models.model_run import ModelRun
from app.models.user import User
from app.schemas.mlops import (
    RetrainingTriggerRequest, 
    RetrainingExecutionResult, 
    RetrainingStatusEnum, 
    ModelRunSummary
)
from app.ml.retraining import retraining_service
from app.core.dependencies import require_roles

router = APIRouter()

@router.post(
    "/trigger",
    response_model=List[RetrainingExecutionResult],
    summary="Admin-Only Retraining Trigger",
    description="Executes automated retraining pipeline, evaluates Challenger vs Champion on holdout validation data, and promotes if performance gates pass. Strictly restricted to ADMIN role."
)
def trigger_retraining(
    request: RetrainingTriggerRequest,
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Triggers end-to-end retraining for Solar, Wind, or both XGBoost models.
    Normal users without ADMIN role receive 403 Forbidden.
    """
    model_type = request.model_type.lower()
    username = getattr(current_user, "username", "admin")

    try:
        if model_type in ("solar", "wind"):
            res = retraining_service.retrain_model(
                db=db,
                model_type=model_type,
                force_promote=request.force_promote,
                sample_days=request.sample_days,
                n_estimators=request.n_estimators or 200,
                learning_rate=request.learning_rate or 0.05,
                max_depth=request.max_depth or 6,
                triggered_by=username
            )
            return [res]
        elif model_type in ("both", "all"):
            return retraining_service.retrain_all(
                db=db,
                force_promote=request.force_promote,
                sample_days=request.sample_days,
                n_estimators=request.n_estimators or 200,
                learning_rate=request.learning_rate or 0.05,
                max_depth=request.max_depth or 6,
                triggered_by=username
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model_type '{request.model_type}'. Expected 'solar', 'wind', or 'both'."
            )
    except Exception as e:
        retraining_service.status = RetrainingStatusEnum.FAILED
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model retraining pipeline failed: {str(e)}"
        )

@router.get(
    "/status",
    summary="Retraining Service Status",
    description="Check the current runtime state of the model retraining pipeline."
)
def get_retraining_status():
    """Returns whether the retraining pipeline is IDLE, TRAINING, EVALUATING, or COMPLETED."""
    return retraining_service.get_status()

@router.get(
    "/history",
    summary="Model Retraining History",
    description="Retrieve past retraining tournament runs, challenger metrics, and promotion outcomes."
)
def get_retraining_history(
    limit: int = Query(20, ge=1, le=100, description="Number of history records to return")
):
    """Returns auditable history of model retraining runs and validation comparisons."""
    return retraining_service.get_history(limit=limit)

@router.get(
    "/models",
    response_model=List[ModelRunSummary],
    summary="List Model Registry Versions",
    description="List all registered model runs and active production champions from database."
)
def list_model_versions(
    model_type: Optional[str] = Query(None, description="Filter by 'solar' or 'wind'"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db)
):
    query = db.query(ModelRun)
    if model_type:
        query = query.filter(ModelRun.model_type == model_type.lower())
    if is_active is not None:
        query = query.filter(ModelRun.is_active == is_active)
    
    return query.order_by(ModelRun.training_date.desc()).all()
