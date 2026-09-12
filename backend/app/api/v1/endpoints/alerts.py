from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.alert import AlertResponse, RecommendationResponse, AlertStatsResponse
from app.services import crud

router = APIRouter()

@router.get("", response_model=List[AlertResponse], summary="List grid balancing alerts")
def get_alerts(
    plant_id: Optional[int] = Query(None, description="Filter by plant ID"),
    severity: Optional[str] = Query(None, description="Filter by severity: 'info', 'warning', 'critical'"),
    status: Optional[str] = Query("active", description="Filter by status: 'active', 'acknowledged', 'resolved'"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieve grid balancing alerts (over-generation, under-generation, ramp warnings) with explainable recommendations."""
    alerts = crud.get_alerts(
        db=db,
        plant_id=plant_id,
        severity=severity,
        status=status,
        limit=limit
    )
    # Map plant_name for convenient frontend display
    result = []
    for a in alerts:
        res = AlertResponse.model_validate(a)
        res.plant_name = a.plant.name if a.plant else "Grid Wide"
        result.append(res)
    return result

@router.get("/stats/summary", response_model=AlertStatsResponse, summary="Get summary statistics for active alerts")
def get_alert_statistics(db: Session = Depends(get_db)):
    """Retrieve aggregate counts and MW imbalances for active alerts."""
    return crud.get_alert_statistics(db=db)

@router.get("/{alert_id}", response_model=AlertResponse, summary="Get alert details with explainable recommendations")
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Get single alert by ID with actionable recommendations and XAI reasoning."""
    alert = crud.get_alert_by_id(db=db, alert_id=alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found"
        )
    res = AlertResponse.model_validate(alert)
    res.plant_name = alert.plant.name if alert.plant else "Grid Wide"
    return res

@router.get("/recommendations/list", response_model=List[RecommendationResponse], summary="List operational recommendations")
def get_recommendations(
    alert_id: Optional[int] = Query(None, description="Filter by alert ID"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieve actionable engineering recommendations (storage dispatch, curtailment, reserve ramping)."""
    return crud.get_recommendations(db=db, alert_id=alert_id, limit=limit)
