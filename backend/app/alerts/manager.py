import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.plant import Plant
from app.models.weather import Weather
from app.models.forecast import Forecast
from app.models.alert_recommendation import Alert, Recommendation
from app.alerts.detector import ThresholdBreachDetector, AnomalyDetector
from app.alerts.dispatcher import notification_dispatcher
from app.services.forecast_engine import forecast_engine

logger = logging.getLogger("backend.alerts.manager")

class AlertManager:
    """
    Production-grade Alert Management Engine.
    Coordinates automated scanning, threshold breach detection, anomaly classification,
    multi-channel notification dispatch, and operator acknowledgment workflows.
    """

    def __init__(self):
        self.dispatcher = notification_dispatcher
        self.forecast_service = forecast_engine

    # -------------------------------------------------------------------------
    # 1. SCANNING & AUTOMATED DETECTION
    # -------------------------------------------------------------------------
    def scan_plant_alerts(
        self,
        db: Session,
        plant_id: int,
        horizon_hours: int = 24,
        auto_dispatch: bool = True
    ) -> List[Alert]:
        """
        Scan plant telemetry and forecasts for threshold breaches and anomalies.
        Persists detected alerts and automatically triggers dispatch.
        """
        plant = db.query(Plant).filter(Plant.id == plant_id).first()
        if not plant:
            raise ValueError(f"Plant with ID {plant_id} does not exist.")

        capacity_mw = float(plant.capacity_mw)

        # 1. Retrieve or generate forecast
        fc = self.forecast_service.generate_plant_forecast(
            db=db,
            plant_id=plant.id,
            horizon_hours=horizon_hours,
            save_to_db=True
        )
        forecast_points = fc["forecast_points"]

        # 2. Retrieve weather records
        weather_records = [
            {
                "timestamp": w.timestamp,
                "ghi": w.ghi,
                "dni": w.dni,
                "dhi": w.dhi,
                "wind_speed_100m": w.wind_speed_100m,
                "wind_speed_10m": w.wind_speed_10m,
                "temperature_c": w.temperature_c,
                "cloud_cover_pct": w.cloud_cover_pct
            }
            for w in db.query(Weather).filter(
                Weather.plant_id == plant.id
            ).order_by(Weather.timestamp.asc()).limit(horizon_hours).all()
        ]

        # 3. Detect Threshold Breaches
        ramp_alerts = ThresholdBreachDetector.detect_ramp_breaches(
            forecast_points=forecast_points,
            capacity_mw=capacity_mw,
            plant_id=plant.id,
            plant_name=plant.name
        )

        deficit_alerts = ThresholdBreachDetector.detect_generation_deficit(
            forecast_points=forecast_points,
            weather_records=weather_records,
            plant_type=plant.plant_type,
            capacity_mw=capacity_mw,
            plant_id=plant.id,
            plant_name=plant.name
        )

        extreme_alerts = ThresholdBreachDetector.detect_meteorological_extremes(
            weather_records=weather_records,
            plant_id=plant.id,
            plant_name=plant.name,
            plant_type=plant.plant_type,
            capacity_mw=capacity_mw
        )

        # 4. Detect Anomalies
        flatline_alerts = AnomalyDetector.detect_daytime_flatline(
            forecast_points=forecast_points,
            weather_records=weather_records,
            capacity_mw=capacity_mw,
            plant_id=plant.id,
            plant_name=plant.name,
            plant_type=plant.plant_type
        )

        detected_raw = ramp_alerts + deficit_alerts + extreme_alerts + flatline_alerts
        persisted_alerts = []

        # 5. Persist unique active alerts into database
        for raw in detected_raw:
            # Check for existing alert with same plant, type, and start_time
            existing = db.query(Alert).filter(
                and_(
                    Alert.plant_id == raw["plant_id"],
                    Alert.alert_type == raw["alert_type"],
                    Alert.start_time == raw["start_time"],
                    Alert.status.in_(["active", "acknowledged"])
                )
            ).first()

            if not existing:
                new_alert = Alert(
                    plant_id=raw["plant_id"],
                    alert_type=raw["alert_type"],
                    severity=raw["severity"],
                    title=raw["title"],
                    description=raw["description"],
                    start_time=raw["start_time"],
                    end_time=raw["end_time"],
                    delta_mw=raw.get("delta_mw"),
                    status="active",
                    confidence=raw.get("confidence", 0.90)
                )
                db.add(new_alert)
                db.flush()  # assign ID

                # Add recommendations
                for rec_data in raw.get("recommendations", []):
                    new_rec = Recommendation(
                        alert_id=new_alert.id,
                        action_type=rec_data["action_type"],
                        title=rec_data["title"],
                        summary=rec_data["summary"],
                        rationale=rec_data["rationale"],
                        recommended_mw=rec_data.get("recommended_mw"),
                        priority=rec_data.get("priority", 1),
                        estimated_cost_saving_inr=rec_data.get("estimated_cost_saving_inr")
                    )
                    db.add(new_rec)

                persisted_alerts.append(new_alert)

                # Auto-dispatch notification
                if auto_dispatch:
                    self.dispatcher.dispatch_alert({
                        "id": new_alert.id,
                        "title": new_alert.title,
                        "severity": new_alert.severity,
                        "delta_mw": new_alert.delta_mw
                    })
            else:
                persisted_alerts.append(existing)

        db.commit()
        return persisted_alerts

    def scan_all_plants(
        self,
        db: Session,
        horizon_hours: int = 24,
        auto_dispatch: bool = True
    ) -> Dict[str, Any]:
        """Batch scan all active renewable generation facilities across the grid."""
        plants = db.query(Plant).filter(Plant.status == "active").all()
        total_alerts = []

        for p in plants:
            plant_alerts = self.scan_plant_alerts(
                db=db,
                plant_id=p.id,
                horizon_hours=horizon_hours,
                auto_dispatch=auto_dispatch
            )
            total_alerts.extend(plant_alerts)

        crit_count = sum(1 for a in total_alerts if a.severity == "critical")
        warn_count = sum(1 for a in total_alerts if a.severity == "warning")

        return {
            "plants_scanned": len(plants),
            "new_alerts_detected": len(total_alerts),
            "critical_count": crit_count,
            "warning_count": warn_count,
            "alerts": total_alerts
        }

    # -------------------------------------------------------------------------
    # 2. ACKNOWLEDGMENT & RESOLUTION WORKFLOW
    # -------------------------------------------------------------------------
    def acknowledge_alert(
        self,
        db: Session,
        alert_id: int,
        acknowledged_by: str = "Grid Dispatcher / Operator",
        ack_notes: Optional[str] = None
    ) -> Alert:
        """Acknowledge an active grid alert, logging operator details and notes."""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert with ID {alert_id} not found.")

        alert.status = "acknowledged"
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.ack_notes = ack_notes or "Alert verified by transmission desk. Corrective action in progress."

        db.commit()
        db.refresh(alert)
        logger.info(f"[ALERT ACKNOWLEDGED] Alert #{alert.id} acknowledged by {acknowledged_by}.")
        return alert

    def resolve_alert(
        self,
        db: Session,
        alert_id: int,
        resolution_notes: str = "Generation returned to scheduled operating tolerance.",
        resolved_by: Optional[str] = "Grid Dispatcher / Operator"
    ) -> Alert:
        """Mark an alert as resolved with completion audit notes."""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert with ID {alert_id} not found.")

        alert.status = "resolved"
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolution_notes = f"{resolution_notes} (Resolved by: {resolved_by})"

        db.commit()
        db.refresh(alert)
        logger.info(f"[ALERT RESOLVED] Alert #{alert.id} resolved.")
        return alert

    def suppress_alert(
        self,
        db: Session,
        alert_id: int,
        reason: str = "Scheduled maintenance or known plant curtailment."
    ) -> Alert:
        """Suppress a transient alarm or false positive."""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert with ID {alert_id} not found.")

        alert.status = "suppressed"
        alert.resolution_notes = f"Suppressed: {reason}"
        db.commit()
        db.refresh(alert)
        return alert

    # -------------------------------------------------------------------------
    # 3. STATISTICS SUMMARY
    # -------------------------------------------------------------------------
    def get_alert_statistics(self, db: Session) -> Dict[str, Any]:
        """Aggregate counts, severity distributions, and MW imbalances."""
        from sqlalchemy import func

        active_alerts = db.query(Alert).filter(Alert.status == "active").all()
        ack_alerts = db.query(Alert).filter(Alert.status == "acknowledged").all()
        resolved_alerts = db.query(Alert).filter(Alert.status == "resolved").all()

        crit_count = sum(1 for a in active_alerts if a.severity == "critical")
        warn_count = sum(1 for a in active_alerts if a.severity == "warning")
        info_count = sum(1 for a in active_alerts if a.severity == "info")

        over_mw = sum(a.delta_mw for a in active_alerts if a.delta_mw and a.delta_mw > 0)
        under_mw = sum(abs(a.delta_mw) for a in active_alerts if a.delta_mw and a.delta_mw < 0)

        return {
            "total_active_alerts": len(active_alerts),
            "critical_alerts": crit_count,
            "warning_alerts": warn_count,
            "info_alerts": info_count,
            "acknowledged_alerts": len(ack_alerts),
            "resolved_alerts": len(resolved_alerts),
            "over_generation_mw": round(over_mw, 2),
            "under_generation_mw": round(under_mw, 2)
        }

# Singleton instance
alert_manager = AlertManager()
