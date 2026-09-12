import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

logger = logging.getLogger("backend.alerts.detector")

class ThresholdBreachDetector:
    """
    Detects physical and operational threshold violations:
      - Steep generation ramp rates (|dMW/dt| >= 15%, 25%)
      - Generation deficits (under-generation during prime irradiance/wind)
      - Generation surpluses (over-generation exceeding evacuation headroom)
      - Extreme meteorological boundaries (storm cut-out >= 25 m/s, sudden GHI collapse, cell thermal limits)
    """

    @staticmethod
    def detect_ramp_breaches(
        forecast_points: List[Dict[str, Any]],
        capacity_mw: float,
        plant_id: int,
        plant_name: str
    ) -> List[Dict[str, Any]]:
        """Identify dangerous 1-hour ramp rate excursions across forecast trajectory."""
        alerts = []
        if not forecast_points or len(forecast_points) < 2:
            return alerts

        warn_threshold = 0.15 * capacity_mw
        crit_threshold = 0.25 * capacity_mw

        prev_mw = forecast_points[0]["predicted_mw"]
        for i in range(1, len(forecast_points)):
            curr_pt = forecast_points[i]
            curr_mw = curr_pt["predicted_mw"]
            delta = round(curr_mw - prev_mw, 2)
            abs_delta = abs(delta)

            if abs_delta >= warn_threshold:
                severity = "critical" if abs_delta >= crit_threshold else "warning"
                direction = "Ramp-Up" if delta > 0 else "Ramp-Down"
                action_type = "storage_charge" if delta > 0 else "storage_discharge"

                ts = curr_pt["timestamp"]
                end_ts = ts + timedelta(hours=1) if isinstance(ts, datetime) else datetime.now(timezone.utc)

                alerts.append({
                    "plant_id": plant_id,
                    "alert_type": "ramp_warning",
                    "severity": severity,
                    "title": f"Steep {direction} Warning: {abs_delta:+.1f} MW/h at {plant_name}",
                    "description": (
                        f"Hourly generation shift of {delta:+.1f} MW ({abs_delta / capacity_mw * 100:.1f}% capacity) "
                        f"violates Indian Grid Code operational ramp rate limits. Grid frequency balancing action required."
                    ),
                    "start_time": ts,
                    "end_time": end_ts,
                    "delta_mw": delta,
                    "confidence": curr_pt.get("confidence_score", 0.90),
                    "recommendations": [
                        {
                            "action_type": action_type,
                            "title": f"Deploy BESS {action_type.replace('_', ' ').title()}",
                            "summary": f"Dispatch energy storage at {plant_name} to buffer {abs_delta:.1f} MW ramp rate swing.",
                            "rationale": f"Compensates {abs_delta:.1f} MW rate of change to protect transmission bus voltage stability.",
                            "recommended_mw": round(min(abs_delta * 0.75, capacity_mw * 0.2), 2),
                            "priority": 1 if severity == "critical" else 2,
                            "estimated_cost_saving_inr": round(abs_delta * 1450.0, 2)
                        }
                    ]
                })

            prev_mw = curr_mw

        return alerts

    @staticmethod
    def detect_generation_deficit(
        forecast_points: List[Dict[str, Any]],
        weather_records: List[Dict[str, Any]],
        plant_type: str,
        capacity_mw: float,
        plant_id: int,
        plant_name: str
    ) -> List[Dict[str, Any]]:
        """Flag under-generation during peak atmospheric resource conditions."""
        alerts = []
        n = min(len(forecast_points), len(weather_records))
        plant_type = plant_type.lower()

        for i in range(n):
            fc = forecast_points[i]
            w = weather_records[i]
            pred_mw = fc["predicted_mw"]
            ts = fc["timestamp"]
            cf_pct = (pred_mw / capacity_mw * 100.0) if capacity_mw > 0 else 0.0

            # Solar deficit check: High GHI (>500 W/m^2) but low output (<20% CF)
            if plant_type in ["solar", "hybrid"]:
                ghi = w.get("ghi", 0.0)
                if ghi >= 500.0 and cf_pct < 20.0:
                    deficit_mw = round((0.60 * capacity_mw) - pred_mw, 2)
                    alerts.append({
                        "plant_id": plant_id,
                        "alert_type": "under_generation",
                        "severity": "critical" if cf_pct < 10.0 else "warning",
                        "title": f"Solar Generation Deficit: {deficit_mw:.1f} MW Gap at {plant_name}",
                        "description": (
                            f"Surface GHI is {ghi:.1f} W/m^2, but projected output is only {pred_mw:.1f} MW ({cf_pct:.1f}% CF). "
                            f"Indicates severe cloud occlusion, inverter trip, or soiling anomaly."
                        ),
                        "start_time": ts,
                        "end_time": ts + timedelta(hours=1) if isinstance(ts, datetime) else datetime.now(timezone.utc),
                        "delta_mw": -deficit_mw,
                        "confidence": fc.get("confidence_score", 0.88),
                        "recommendations": [
                            {
                                "action_type": "backup_dispatch",
                                "title": "Dispatch Flexible Gas/Hydro Spinning Reserve",
                                "summary": f"Procure {deficit_mw:.1f} MW replacement capacity via Day-Ahead Market / RTM.",
                                "rationale": f"Replaces unexpected {deficit_mw:.1f} MW generation shortfall to maintain system frequency at 50.0 Hz.",
                                "recommended_mw": deficit_mw,
                                "priority": 1,
                                "estimated_cost_saving_inr": round(deficit_mw * 2200.0, 2)
                            }
                        ]
                    })

            # Wind deficit check: High wind speed (>9.0 m/s) but low output (<20% CF)
            if plant_type in ["wind", "hybrid"]:
                ws = w.get("wind_speed_100m", 0.0)
                if 9.0 <= ws < 24.0 and cf_pct < 20.0:
                    deficit_mw = round((0.70 * capacity_mw) - pred_mw, 2)
                    alerts.append({
                        "plant_id": plant_id,
                        "alert_type": "under_generation",
                        "severity": "critical" if cf_pct < 10.0 else "warning",
                        "title": f"Wind Aerodynamic Deficit: {deficit_mw:.1f} MW Gap at {plant_name}",
                        "description": (
                            f"Hub-height wind speed is {ws:.1f} m/s, but output is only {pred_mw:.1f} MW. "
                            f"Possible blade yaw misalignment, pitch fault, or grid-directed curtailment."
                        ),
                        "start_time": ts,
                        "end_time": ts + timedelta(hours=1) if isinstance(ts, datetime) else datetime.now(timezone.utc),
                        "delta_mw": -deficit_mw,
                        "confidence": fc.get("confidence_score", 0.86),
                        "recommendations": [
                            {
                                "action_type": "power_procurement",
                                "title": "Procure Emergency Balancing Power",
                                "summary": f"Schedule {deficit_mw:.1f} MW bilateral exchange power.",
                                "rationale": "Mitigates DSM (Deviation Settlement Mechanism) penal rates for schedule shortfall.",
                                "recommended_mw": deficit_mw,
                                "priority": 1,
                                "estimated_cost_saving_inr": round(deficit_mw * 2650.0, 2)
                            }
                        ]
                    })

        return alerts

    @staticmethod
    def detect_meteorological_extremes(
        weather_records: List[Dict[str, Any]],
        plant_id: int,
        plant_name: str,
        plant_type: str,
        capacity_mw: float
    ) -> List[Dict[str, Any]]:
        """Identify hazardous weather thresholds (storm cut-out, dust storms, thermal alarms)."""
        alerts = []
        plant_type = plant_type.lower()
        prev_ghi = None

        for w in weather_records:
            ts = w.get("timestamp")
            ws_100m = w.get("wind_speed_100m", 0.0)
            ghi = w.get("ghi", 0.0)
            temp = w.get("temperature_c", 25.0)

            # Storm cut-out threshold (>= 25 m/s)
            if plant_type in ["wind", "hybrid"] and ws_100m >= 25.0:
                alerts.append({
                    "plant_id": plant_id,
                    "alert_type": "storm_cutout_risk",
                    "severity": "critical",
                    "title": f"Storm Cut-Out Trip Hazard: {ws_100m:.1f} m/s at {plant_name}",
                    "description": (
                        f"Gale-force hub wind speed of {ws_100m:.1f} m/s exceeds turbine 25.0 m/s aerodynamic cut-out threshold. "
                        f"Emergency aerodynamic feathering and mechanical brake trip imminent. Full generation loss expected."
                    ),
                    "start_time": ts,
                    "end_time": ts + timedelta(hours=2) if isinstance(ts, datetime) else datetime.now(timezone.utc),
                    "delta_mw": -capacity_mw,
                    "confidence": 0.95,
                    "recommendations": [
                        {
                            "action_type": "controlled_curtailment",
                            "title": "Controlled Turbine Feathering & Pre-emptive Shutdown",
                            "summary": f"Feather turbine blades at {plant_name} in stages before mechanical storm trip.",
                            "rationale": "Prevents catastrophic mechanical drive train stress and shock-loss to the transmission network.",
                            "recommended_mw": capacity_mw,
                            "priority": 1,
                            "estimated_cost_saving_inr": round(capacity_mw * 4500.0, 2)
                        }
                    ]
                })

            # Sudden GHI collapse (> 400 W/m^2 drop in 1 hour)
            if plant_type in ["solar", "hybrid"] and prev_ghi is not None:
                ghi_drop = prev_ghi - ghi
                if ghi_drop >= 400.0:
                    lost_mw = round((ghi_drop / 1000.0) * capacity_mw * 0.75, 2)
                    alerts.append({
                        "plant_id": plant_id,
                        "alert_type": "solar_irradiance_drop",
                        "severity": "warning",
                        "title": f"Sudden Solar Irradiance Drop: -{ghi_drop:.0f} W/m^2 at {plant_name}",
                        "description": (
                            f"Severe surface irradiance drop of {ghi_drop:.0f} W/m^2 detected. "
                            f"Dense thunderstorm cloud front or dust storm causing rapid {lost_mw:.1f} MW solar output attenuation."
                        ),
                        "start_time": ts,
                        "end_time": ts + timedelta(hours=1) if isinstance(ts, datetime) else datetime.now(timezone.utc),
                        "delta_mw": -lost_mw,
                        "confidence": 0.91,
                        "recommendations": [
                            {
                                "action_type": "storage_discharge",
                                "title": "BESS Rapid Injection",
                                "summary": f"Discharge on-site battery storage to counter {lost_mw:.1f} MW cloud ramp.",
                                "rationale": "Supplies instantaneous sub-second active power to preserve grid frequency stability.",
                                "recommended_mw": lost_mw,
                                "priority": 2,
                                "estimated_cost_saving_inr": round(lost_mw * 1800.0, 2)
                            }
                        ]
                    })

            # Extreme ambient temperature (>= 45 deg C -> cell temp > 65 deg C)
            if plant_type in ["solar", "hybrid"] and temp >= 45.0:
                derate_mw = round(capacity_mw * 0.08, 2)
                alerts.append({
                    "plant_id": plant_id,
                    "alert_type": "thermal_overload_risk",
                    "severity": "warning",
                    "title": f"Extreme Ambient Heat: {temp:.1f} C at {plant_name}",
                    "description": (
                        f"Ambient temperature of {temp:.1f} C elevates solar PV cell junction temperature beyond 65 C, "
                        f"inducing -0.4%/C thermal voltage degradation and inverter thermal throttling."
                    ),
                    "start_time": ts,
                    "end_time": ts + timedelta(hours=2) if isinstance(ts, datetime) else datetime.now(timezone.utc),
                    "delta_mw": -derate_mw,
                    "confidence": 0.89,
                    "recommendations": [
                        {
                            "action_type": "controlled_curtailment",
                            "title": "Inverter Thermal Load Management",
                            "summary": "Cycle central inverter cooling fans and optimize reactive power dispatch (VARs).",
                            "rationale": "Prevents catastrophic IGBT inverter bridge failure during extreme peak heat waves.",
                            "recommended_mw": derate_mw,
                            "priority": 3,
                            "estimated_cost_saving_inr": round(derate_mw * 850.0, 2)
                        }
                    ]
                })

            prev_ghi = ghi

        return alerts


class AnomalyDetector:
    """
    Statistical and physics-informed anomaly detection:
      - Z-score residual outlier detection
      - Daytime flatline / stuck sensor identification
      - Wind power curve deviation
    """

    @staticmethod
    def detect_statistical_anomalies(
        forecast_points: List[Dict[str, Any]],
        actual_telemetry: List[Dict[str, Any]],
        capacity_mw: float,
        plant_id: int,
        plant_name: str
    ) -> List[Dict[str, Any]]:
        """Flag telemetry points that deviate beyond 2.5 standard deviations from physical forecast."""
        alerts = []
        n = min(len(forecast_points), len(actual_telemetry))
        if n < 4:
            return alerts

        residuals = []
        for i in range(n):
            actual = actual_telemetry[i].get("actual_mw")
            pred = forecast_points[i]["predicted_mw"]
            if actual is not None:
                residuals.append(actual - pred)

        if not residuals:
            return alerts

        mean_res = float(np.mean(residuals))
        std_res = float(np.std(residuals)) if len(residuals) > 1 else 1.0
        if std_res == 0:
            std_res = 1.0

        for i in range(n):
            actual = actual_telemetry[i].get("actual_mw")
            if actual is None:
                continue

            pred = forecast_points[i]["predicted_mw"]
            res = actual - pred
            z_score = (res - mean_res) / std_res

            # Flag if |z| >= 2.5 and deviation exceeds 10% capacity
            if abs(z_score) >= 2.5 and abs(res) >= (0.10 * capacity_mw):
                ts = forecast_points[i]["timestamp"]
                direction = "Over-generation" if res > 0 else "Under-generation"

                alerts.append({
                    "plant_id": plant_id,
                    "alert_type": "forecast_anomaly",
                    "severity": "warning" if abs(z_score) < 3.5 else "critical",
                    "title": f"Statistical {direction} Outlier (Z={z_score:+.1f}) at {plant_name}",
                    "description": (
                        f"Observed generation ({actual:.1f} MW) deviates from machine learning forecast ({pred:.1f} MW) "
                        f"by {res:+.1f} MW (|Z| = {abs(z_score):.2f}). Indicates unmodeled transmission curtailment or telemetry error."
                    ),
                    "start_time": ts,
                    "end_time": ts + timedelta(hours=1) if isinstance(ts, datetime) else datetime.now(timezone.utc),
                    "delta_mw": round(res, 2),
                    "confidence": 0.92,
                    "recommendations": [
                        {
                            "action_type": "power_procurement" if res < 0 else "storage_charge",
                            "title": "Trigger ML Feature Retraining & SCADA Audit",
                            "summary": "Audit local pyranometer/anemometer sensors and adjust online ML bias weights.",
                            "rationale": "Calibrates online forecast model to eliminate systematic localized telemetry bias.",
                            "recommended_mw": round(abs(res), 2),
                            "priority": 2,
                            "estimated_cost_saving_inr": round(abs(res) * 980.0, 2)
                        }
                    ]
                })

        return alerts

    @staticmethod
    def detect_daytime_flatline(
        forecast_points: List[Dict[str, Any]],
        weather_records: List[Dict[str, Any]],
        capacity_mw: float,
        plant_id: int,
        plant_name: str,
        plant_type: str
    ) -> List[Dict[str, Any]]:
        """Identify zero-generation flatlining during bright daytime conditions (stuck sensor/trip)."""
        alerts = []
        if plant_type.lower() not in ["solar", "hybrid"]:
            return alerts

        n = min(len(forecast_points), len(weather_records))
        flatline_run = 0
        run_start = None

        for i in range(n):
            w = weather_records[i]
            fc = forecast_points[i]
            ghi = w.get("ghi", 0.0)
            pred_mw = fc.get("predicted_mw", 0.0)
            actual_mw = fc.get("actual_mw")

            # Check if actual output is zero despite bright sun
            eval_mw = actual_mw if actual_mw is not None else pred_mw

            if ghi >= 250.0 and eval_mw <= 1.0:
                flatline_run += 1
                if run_start is None:
                    run_start = fc["timestamp"]

                if flatline_run >= 2:
                    alerts.append({
                        "plant_id": plant_id,
                        "alert_type": "sensor_flatline_anomaly",
                        "severity": "critical",
                        "title": f"Zero-Generation Flatline Anomaly at {plant_name}",
                        "description": (
                            f"Facility generation has flatlined at {eval_mw:.1f} MW for {flatline_run} consecutive hours "
                            f"despite high clear-sky irradiance ({ghi:.1f} W/m^2). Indicates main substation breaker trip or SCADA failure."
                        ),
                        "start_time": run_start,
                        "end_time": fc["timestamp"] + timedelta(hours=1) if isinstance(fc["timestamp"], datetime) else datetime.now(timezone.utc),
                        "delta_mw": -round(0.5 * capacity_mw, 2),
                        "confidence": 0.96,
                        "recommendations": [
                            {
                                "action_type": "backup_dispatch",
                                "title": "Substation Switchyard Inspection",
                                "summary": "Dispatch field electrical engineers to inspect 220kV/400kV pool substation breakers.",
                                "rationale": "Verifies whether power evacuation line is open or RTU communication link is severed.",
                                "recommended_mw": round(0.5 * capacity_mw, 2),
                                "priority": 1,
                                "estimated_cost_saving_inr": round(capacity_mw * 3200.0, 2)
                            }
                        ]
                    })
                    break  # Alert raised
            else:
                flatline_run = 0
                run_start = None

        return alerts
