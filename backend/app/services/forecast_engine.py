import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.plant import Plant
from app.models.weather import Weather
from app.models.forecast import Forecast
from app.data_pipeline.metadata_manager import PlantMetadataManager
from app.data_pipeline.open_meteo import OpenMeteoClient
from app.ml.features import FeatureEngineer
from app.ml.solar_model import SolarForecaster
from app.ml.wind_model import WindForecaster

logger = logging.getLogger("backend.services.forecast_engine")

class ForecastEngine:
    """
    Production-grade multi-horizon renewable generation forecast engine.
    Orchestrates Solar and Wind XGBoost models, computes uncertainty bands,
    evaluates ramp risks, and persists predictions to PostgreSQL.
    """

    def __init__(self):
        self._solar_model: Optional[SolarForecaster] = None
        self._wind_model: Optional[WindForecaster] = None
        self.open_meteo_client = OpenMeteoClient()

    def _get_solar_forecaster(self) -> SolarForecaster:
        if self._solar_model is not None:
            return self._solar_model

        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(backend_dir, "trained_models", "solar_xgboost_v1.joblib")

        if os.path.exists(model_path):
            self._solar_model = SolarForecaster.load(model_path)
        else:
            from app.ml.train_solar import train_and_register_solar_model
            self._solar_model = train_and_register_solar_model(days=90)

        return self._solar_model

    def _get_wind_forecaster(self) -> WindForecaster:
        if self._wind_model is not None:
            return self._wind_model

        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(backend_dir, "trained_models", "wind_xgboost_v1.joblib")

        if os.path.exists(model_path):
            self._wind_model = WindForecaster.load(model_path)
        else:
            from app.ml.train_wind import train_and_register_wind_model
            self._wind_model = train_and_register_wind_model(days=90)

        return self._wind_model

    def _ensure_weather_data(
        self,
        db: Session,
        plant: Plant,
        horizon_hours: int
    ) -> List[Dict[str, Any]]:
        """
        Ensure sufficient weather telemetry exists for the forecast horizon.
        If missing, automatically queries Open-Meteo.
        """
        records = db.query(Weather).filter(
            Weather.plant_id == plant.id
        ).order_by(Weather.timestamp.asc()).limit(horizon_hours).all()

        if len(records) < horizon_hours:
            logger.info(f"Insufficient weather in DB ({len(records)}/{horizon_hours} hours). Ingesting fresh Open-Meteo NWP...")
            forecast_days = int(np.ceil(horizon_hours / 24.0))
            raw_df = self.open_meteo_client.fetch_hourly_forecast(
                latitude=plant.latitude,
                longitude=plant.longitude,
                forecast_days=max(3, forecast_days)
            )
            from app.data_pipeline.validator import DataValidator
            clean_df, _ = DataValidator.validate_and_clean(raw_df, latitude=plant.latitude)

            for _, row in clean_df.iterrows():
                ts = row["timestamp"].to_pydatetime()
                existing = db.query(Weather).filter(
                    and_(Weather.plant_id == plant.id, Weather.timestamp == ts)
                ).first()
                if not existing:
                    w = Weather(
                        plant_id=plant.id,
                        timestamp=ts,
                        ghi=float(row.get("ghi", 0.0)),
                        dni=float(row.get("dni", 0.0)),
                        dhi=float(row.get("dhi", 0.0)),
                        temperature_c=float(row.get("temperature_c", 25.0)),
                        relative_humidity=float(row.get("relative_humidity", 50.0)),
                        cloud_cover_pct=float(row.get("cloud_cover_pct", 0.0)),
                        surface_pressure_hpa=float(row.get("surface_pressure_hpa", 1013.25)),
                        wind_speed_10m=float(row.get("wind_speed_10m", 0.0)),
                        wind_speed_100m=float(row.get("wind_speed_100m", 0.0)),
                        wind_direction_deg=float(row.get("wind_direction_deg", 0.0)),
                        source=str(row.get("source", "open_meteo"))
                    )
                    db.add(w)
            db.commit()

            records = db.query(Weather).filter(
                Weather.plant_id == plant.id
            ).order_by(Weather.timestamp.asc()).limit(horizon_hours).all()

        return [
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
            for w in records[:horizon_hours]
        ]

    def generate_plant_forecast(
        self,
        db: Session,
        plant_id: int,
        horizon_hours: int = 24,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Generate hourly generation forecast for a specific plant over 24h, 48h, or 72h.
        Routes to SolarForecaster, WindForecaster, or Hybrid ensemble.
        Computes P10/P90 intervals and capacity factor.
        """
        plant = db.query(Plant).filter(Plant.id == plant_id).first()
        if not plant:
            raise ValueError(f"Plant with ID {plant_id} does not exist.")

        metadata = PlantMetadataManager.get_plant_metadata(db, plant_id)
        capacity_mw = float(plant.capacity_mw)
        plant_type = plant.plant_type.lower()

        weather_data = self._ensure_weather_data(db, plant, horizon_hours)
        df_weather = pd.DataFrame(weather_data)

        # Feature transformations
        X_solar, X_wind = FeatureEngineer.create_feature_matrix(df_weather, metadata)

        # Model Execution
        if plant_type == "solar":
            forecaster = self._get_solar_forecaster()
            intervals_df = forecaster.predict_with_intervals(X_solar, capacity_mw=capacity_mw)
            model_ver = "v1.0.0-solar-xgb"

        elif plant_type == "wind":
            forecaster = self._get_wind_forecaster()
            intervals_df = forecaster.predict_with_intervals(X_wind, capacity_mw=capacity_mw)
            model_ver = "v1.0.0-wind-xgb"

        elif plant_type == "hybrid":
            solar_forecaster = self._get_solar_forecaster()
            wind_forecaster = self._get_wind_forecaster()

            solar_cap = capacity_mw * 0.60
            wind_cap = capacity_mw * 0.40

            solar_intervals = solar_forecaster.predict_with_intervals(X_solar, capacity_mw=solar_cap)
            wind_intervals = wind_forecaster.predict_with_intervals(X_wind, capacity_mw=wind_cap)

            total_pred = np.round(solar_intervals["predicted_mw"] + wind_intervals["predicted_mw"], 2)
            total_lower = np.round(solar_intervals["lower_bound_mw"] + wind_intervals["lower_bound_mw"], 2)
            total_upper = np.round(solar_intervals["upper_bound_mw"] + wind_intervals["upper_bound_mw"], 2)
            mean_conf = np.round(0.6 * solar_intervals["confidence_score"] + 0.4 * wind_intervals["confidence_score"], 2)

            intervals_df = pd.DataFrame({
                "predicted_mw": np.minimum(capacity_mw, total_pred),
                "lower_bound_mw": np.maximum(0.0, total_lower),
                "upper_bound_mw": np.minimum(capacity_mw, total_upper),
                "confidence_score": mean_conf
            })
            model_ver = "v1.0.0-hybrid-ensemble"
        else:
            raise ValueError(f"Unsupported plant type: {plant_type}")

        # Assemble forecast points & identify ramp events
        forecast_points = []
        ramp_events = []
        prev_mw = None

        for i, row in intervals_df.iterrows():
            curr_ts = df_weather["timestamp"].iloc[i]
            pred_mw = float(row["predicted_mw"])

            if prev_mw is not None:
                delta = round(pred_mw - prev_mw, 2)
                # Flag ramp if change exceeds 15% of capacity in 1 hour
                if abs(delta) >= (0.15 * capacity_mw):
                    ramp_events.append({
                        "timestamp": curr_ts,
                        "delta_mw": delta,
                        "direction": "up" if delta > 0 else "down",
                        "severity": "critical" if abs(delta) >= (0.25 * capacity_mw) else "warning"
                    })
            prev_mw = pred_mw

            point = {
                "timestamp": curr_ts,
                "horizon_hours": horizon_hours,
                "predicted_mw": pred_mw,
                "lower_bound_mw": float(row["lower_bound_mw"]),
                "upper_bound_mw": float(row["upper_bound_mw"]),
                "confidence_score": float(row["confidence_score"]),
                "model_version": model_ver
            }
            forecast_points.append(point)

            # Persist to database if enabled
            if save_to_db:
                existing_fc = db.query(Forecast).filter(
                    and_(
                        Forecast.plant_id == plant_id,
                        Forecast.forecast_timestamp == curr_ts,
                        Forecast.horizon_hours == horizon_hours
                    )
                ).first()

                if existing_fc:
                    existing_fc.predicted_mw = pred_mw
                    existing_fc.lower_bound_mw = float(row["lower_bound_mw"])
                    existing_fc.upper_bound_mw = float(row["upper_bound_mw"])
                    existing_fc.confidence_score = float(row["confidence_score"])
                    existing_fc.model_version = model_ver
                else:
                    new_fc = Forecast(
                        plant_id=plant_id,
                        forecast_timestamp=curr_ts,
                        horizon_hours=horizon_hours,
                        predicted_mw=pred_mw,
                        lower_bound_mw=float(row["lower_bound_mw"]),
                        upper_bound_mw=float(row["upper_bound_mw"]),
                        confidence_score=float(row["confidence_score"]),
                        model_version=model_ver
                    )
                    db.add(new_fc)

        if save_to_db:
            db.commit()

        # Operational summary statistics
        mw_values = [p["predicted_mw"] for p in forecast_points]
        peak_mw = max(mw_values) if mw_values else 0.0
        peak_idx = mw_values.index(peak_mw) if mw_values else 0
        peak_time = forecast_points[peak_idx]["timestamp"] if forecast_points else None
        avg_mw = sum(mw_values) / len(mw_values) if mw_values else 0.0
        total_mwh = sum(mw_values)
        cf_pct = round((avg_mw / capacity_mw * 100), 2) if capacity_mw > 0 else 0.0

        return {
            "plant_id": plant.id,
            "plant_name": plant.name,
            "plant_type": plant.plant_type,
            "capacity_mw": capacity_mw,
            "horizon_hours": horizon_hours,
            "model_version": model_ver,
            "peak_generation_mw": round(peak_mw, 2),
            "peak_generation_timestamp": peak_time,
            "average_generation_mw": round(avg_mw, 2),
            "expected_total_mwh": round(total_mwh, 2),
            "capacity_factor_pct": cf_pct,
            "average_confidence": round(float(np.mean([p["confidence_score"] for p in forecast_points])), 2),
            "ramp_events_count": len(ramp_events),
            "ramp_events": ramp_events,
            "forecast_points": forecast_points
        }

    def generate_multi_horizon(
        self,
        db: Session,
        plant_id: int
    ) -> Dict[str, Any]:
        """
        Generate and compare 24h, 48h, and 72h generation forecasts for a plant.
        """
        fc_24 = self.generate_plant_forecast(db, plant_id, horizon_hours=24, save_to_db=True)
        fc_48 = self.generate_plant_forecast(db, plant_id, horizon_hours=48, save_to_db=True)
        fc_72 = self.generate_plant_forecast(db, plant_id, horizon_hours=72, save_to_db=True)

        return {
            "plant_id": plant_id,
            "plant_name": fc_24["plant_name"],
            "plant_type": fc_24["plant_type"],
            "capacity_mw": fc_24["capacity_mw"],
            "horizons": {
                "24h": {
                    "peak_mw": fc_24["peak_generation_mw"],
                    "average_mw": fc_24["average_generation_mw"],
                    "total_mwh": fc_24["expected_total_mwh"],
                    "capacity_factor_pct": fc_24["capacity_factor_pct"],
                    "mean_confidence": fc_24["average_confidence"],
                    "ramp_events": fc_24["ramp_events_count"]
                },
                "48h": {
                    "peak_mw": fc_48["peak_generation_mw"],
                    "average_mw": fc_48["average_generation_mw"],
                    "total_mwh": fc_48["expected_total_mwh"],
                    "capacity_factor_pct": fc_48["capacity_factor_pct"],
                    "mean_confidence": fc_48["average_confidence"],
                    "ramp_events": fc_48["ramp_events_count"]
                },
                "72h": {
                    "peak_mw": fc_72["peak_generation_mw"],
                    "average_mw": fc_72["average_generation_mw"],
                    "total_mwh": fc_72["expected_total_mwh"],
                    "capacity_factor_pct": fc_72["capacity_factor_pct"],
                    "mean_confidence": fc_72["average_confidence"],
                    "ramp_events": fc_72["ramp_events_count"]
                }
            },
            "points_24h": fc_24["forecast_points"],
            "points_48h": fc_48["forecast_points"],
            "points_72h": fc_72["forecast_points"]
        }

    def generate_all_plants_forecast(
        self,
        db: Session,
        horizon_hours: int = 72
    ) -> List[Dict[str, Any]]:
        """Batch generate and persist forecasts across all registered renewable parks."""
        plants = db.query(Plant).all()
        results = []
        for p in plants:
            res = self.generate_plant_forecast(db, p.id, horizon_hours=horizon_hours, save_to_db=True)
            results.append(res)
        return results

# Singleton instance
forecast_engine = ForecastEngine()
