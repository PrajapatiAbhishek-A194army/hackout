from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.alert import (
    AlertResponse,
    RecommendationResponse,
    AlertStatsResponse,
    AlertAcknowledgeRequest,
    AlertResolveRequest,
    AlertSuppressRequest,
    NotificationDispatchReceipt,
    AlertScanResult
)
from app.alerts.manager import alert_manager
from app.alerts.dispatcher import notification_dispatcher
from app.services import crud

router = APIRouter()

@router.get("", response_model=List[AlertResponse], summary="List grid balancing alerts")
def get_alerts(
    plant_id: Optional[int] = Query(None, description="Filter by plant ID"),
    severity: Optional[str] = Query(None, description="Filter by severity: 'info', 'warning', 'critical'"),
    status: Optional[str] = Query("active", description="Filter by status: 'active', 'acknowledged', 'resolved', 'all'"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieve grid balancing alerts with explainable recommendations and acknowledgment audit trail."""
    actual_status = None if status == "all" else status
    alerts = crud.get_alerts(
        db=db,
        plant_id=plant_id,
        severity=severity,
        status=actual_status,
        limit=limit
    )
    result = []
    for a in alerts:
        res = AlertResponse.model_validate(a)
        res.plant_name = a.plant.name if a.plant else "Grid Wide"
        result.append(res)
    return result

@router.get("/stats/summary", response_model=AlertStatsResponse, summary="Get summary statistics for active alerts")
def get_alert_statistics(db: Session = Depends(get_db)):
    """Retrieve aggregate counts and MW imbalances across active, acknowledged, and resolved alerts."""
    return alert_manager.get_alert_statistics(db=db)

@router.get("/dispatch/logs", response_model=List[NotificationDispatchReceipt], summary="Get notification dispatch history")
def get_dispatch_logs(
    limit: int = Query(50, ge=1, le=100, description="Max receipts to return")
):
    """Retrieve multi-channel notification dispatch audit logs."""
    return notification_dispatcher.get_dispatch_history(limit=limit)

@router.post("/scan/{plant_id}", response_model=List[AlertResponse], summary="Scan a plant for threshold breaches & anomalies")
def scan_plant_alerts(
    plant_id: int = Path(..., description="ID of the renewable facility to scan"),
    horizon_hours: int = Query(24, ge=1, le=72),
    auto_dispatch: bool = Query(True, description="Automatically dispatch notifications for detected alerts"),
    db: Session = Depends(get_db)
):
    """Execute automated detection engine scanning for steep ramps, under-generation, storm cut-outs, and flatlines."""
    try:
        alerts = alert_manager.scan_plant_alerts(
            db=db,
            plant_id=plant_id,
            horizon_hours=horizon_hours,
            auto_dispatch=auto_dispatch
        )
        result = []
        for a in alerts:
            res = AlertResponse.model_validate(a)
            res.plant_name = a.plant.name if a.plant else "Grid Wide"
            result.append(res)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@router.post("/scan-all", response_model=AlertScanResult, summary="Batch scan all grid assets for alerts")
def scan_all_plants_alerts(
    horizon_hours: int = Query(24, ge=1, le=72),
    auto_dispatch: bool = Query(True, description="Automatically dispatch notifications for detected alerts"),
    db: Session = Depends(get_db)
):
    """Batch scan all registered renewable facilities across the national grid."""
    try:
        raw_res = alert_manager.scan_all_plants(
            db=db,
            horizon_hours=horizon_hours,
            auto_dispatch=auto_dispatch
        )
        formatted_alerts = []
        for a in raw_res["alerts"]:
            res = AlertResponse.model_validate(a)
            res.plant_name = a.plant.name if a.plant else "Grid Wide"
            formatted_alerts.append(res)

        return AlertScanResult(
            plants_scanned=raw_res["plants_scanned"],
            new_alerts_detected=raw_res["new_alerts_detected"],
            critical_count=raw_res["critical_count"],
            warning_count=raw_res["warning_count"],
            alerts=formatted_alerts
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Grid batch scan failed: {str(e)}")

@router.post("/{alert_id}/acknowledge", response_model=AlertResponse, summary="Acknowledge an active alert")
def acknowledge_alert(
    alert_id: int = Path(..., description="ID of the alert to acknowledge"),
    payload: Optional[AlertAcknowledgeRequest] = None,
    db: Session = Depends(get_db)
):
    """Operator acknowledgment flow, logging dispatcher identity and operational notes."""
    try:
        ack_by = payload.acknowledged_by if payload else "Grid Dispatcher / Operator"
        notes = payload.notes if payload else None
        alert = alert_manager.acknowledge_alert(
            db=db,
            alert_id=alert_id,
            acknowledged_by=ack_by,
            ack_notes=notes
        )
        res = AlertResponse.model_validate(alert)
        res.plant_name = alert.plant.name if alert.plant else "Grid Wide"
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")

@router.post("/{alert_id}/resolve", response_model=AlertResponse, summary="Resolve an alert")
def resolve_alert(
    alert_id: int = Path(..., description="ID of the alert to mark as resolved"),
    payload: Optional[AlertResolveRequest] = None,
    db: Session = Depends(get_db)
):
    """Mark an operational alert as resolved with completion audit notes."""
    try:
        notes = payload.resolution_notes if payload else "Generation stabilized within nominal margins."
        by = payload.resolved_by if payload else "Grid Dispatcher / Operator"
        alert = alert_manager.resolve_alert(
            db=db,
            alert_id=alert_id,
            resolution_notes=notes,
            resolved_by=by
        )
        res = AlertResponse.model_validate(alert)
        res.plant_name = alert.plant.name if alert.plant else "Grid Wide"
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve alert: {str(e)}")

@router.post("/{alert_id}/suppress", response_model=AlertResponse, summary="Suppress an alert")
def suppress_alert(
    alert_id: int = Path(..., description="ID of the alert to suppress"),
    payload: Optional[AlertSuppressRequest] = None,
    db: Session = Depends(get_db)
):
    """Suppress a transient or known maintenance alert."""
    try:
        reason = payload.reason if payload else "Scheduled maintenance or known curtailment."
        alert = alert_manager.suppress_alert(db=db, alert_id=alert_id, reason=reason)
        res = AlertResponse.model_validate(alert)
        res.plant_name = alert.plant.name if alert.plant else "Grid Wide"
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to suppress alert: {str(e)}")

@router.post("/{alert_id}/dispatch", response_model=NotificationDispatchReceipt, summary="Dispatch alert notification")
def dispatch_alert(
    alert_id: int = Path(..., description="ID of the alert to dispatch"),
    channels: Optional[List[str]] = Query(None, description="Channels: in_app, webhook, email_sms"),
    db: Session = Depends(get_db)
):
    """Manually re-dispatch an alert to in-app, REMC webhook, and SMS/Email channels."""
    alert = crud.get_alert_by_id(db=db, alert_id=alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found.")

    receipt = notification_dispatcher.dispatch_alert(
        alert_dict={
            "id": alert.id,
            "title": alert.title,
            "severity": alert.severity,
            "delta_mw": alert.delta_mw
        },
        channels=channels
    )
    return receipt

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
