import logging
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.plant import Plant
from app.models.weather import Weather
from app.data_pipeline.open_meteo import OpenMeteoClient
from app.data_pipeline.nasa_power import NasaPowerClient
from app.data_pipeline.metadata_manager import PlantMetadataManager
from app.data_pipeline.validator import DataValidator, ValidationReport

logger = logging.getLogger("backend.data_pipeline.pipeline")

class DataPipeline:
    """
    Automated meteorological data ingestion, validation, and storage pipeline.
    Connects Open-Meteo NWP forecasts, NASA POWER climatology, and PostgreSQL storage.
    """

    def __init__(self):
        self.open_meteo_client = OpenMeteoClient()
        self.nasa_power_client = NasaPowerClient()

    def run_for_plant(
        self,
        db: Session,
        plant_id: int,
        forecast_days: int = 3,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Execute full end-to-end data pipeline for a specific plant:
        1. Retrieve plant metadata & site engineering specs
        2. Fetch Open-Meteo forecast (24h - 72h)
        3. Validate timestamps, coordinates, and physical parameters
        4. Persist clean records into PostgreSQL
        """
        metadata = PlantMetadataManager.get_plant_metadata(db, plant_id)
        if not metadata:
            return {
                "status": "failed",
                "error": f"Plant with ID {plant_id} not found",
                "records_processed": 0
            }

        lat, lon = metadata["latitude"], metadata["longitude"]
        coord_valid, coord_msg = DataValidator.validate_coordinates(lat, lon)
        if not coord_valid:
            logger.warning(f"Coordinate validation warning for plant {plant_id}: {coord_msg}")

        # 1. Fetch Open-Meteo Forecast
        raw_forecast_df = self.open_meteo_client.fetch_hourly_forecast(
            latitude=lat,
            longitude=lon,
            forecast_days=forecast_days
        )

        # 2. Validate and Clean Time-Series
        clean_df, report = DataValidator.validate_and_clean(raw_forecast_df, latitude=lat)

        # 3. Save to Database
        saved_count = 0
        if save_to_db and not clean_df.empty:
            for _, row in clean_df.iterrows():
                ts = row["timestamp"].to_pydatetime()
                existing = db.query(Weather).filter(
                    and_(
                        Weather.plant_id == plant_id,
                        Weather.timestamp == ts
                    )
                ).first()

                if existing:
                    existing.ghi = float(row.get("ghi", 0.0))
                    existing.dni = float(row.get("dni", 0.0))
                    existing.dhi = float(row.get("dhi", 0.0))
                    existing.temperature_c = float(row.get("temperature_c", 25.0))
                    existing.relative_humidity = float(row.get("relative_humidity", 50.0))
                    existing.cloud_cover_pct = float(row.get("cloud_cover_pct", 0.0))
                    existing.surface_pressure_hpa = float(row.get("surface_pressure_hpa", 1013.25))
                    existing.wind_speed_10m = float(row.get("wind_speed_10m", 0.0))
                    existing.wind_speed_100m = float(row.get("wind_speed_100m", 0.0))
                    existing.wind_direction_deg = float(row.get("wind_direction_deg", 0.0))
                    existing.source = str(row.get("source", "open_meteo"))
                else:
                    new_weather = Weather(
                        plant_id=plant_id,
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
                    db.add(new_weather)
                saved_count += 1

            db.commit()
            logger.info(f"Persisted {saved_count} validated weather records for plant '{metadata['name']}'.")

        return {
            "status": "success",
            "plant_id": plant_id,
            "plant_name": metadata["name"],
            "plant_type": metadata["plant_type"],
            "coordinates": {"lat": lat, "lon": lon},
            "records_processed": len(clean_df),
            "records_persisted": saved_count,
            "validation_report": report.to_dict()
        }

    def run_for_all_plants(
        self,
        db: Session,
        forecast_days: int = 3,
        save_to_db: bool = True
    ) -> List[Dict[str, Any]]:
        """Run the ingestion pipeline for all registered plants."""
        plants = db.query(Plant).all()
        results = []
        for plant in plants:
            res = self.run_for_plant(
                db=db,
                plant_id=plant.id,
                forecast_days=forecast_days,
                save_to_db=save_to_db
            )
            results.append(res)
        return results

# Singleton instance
data_pipeline = DataPipeline()
