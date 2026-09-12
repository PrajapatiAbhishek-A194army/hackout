import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models.plant import Plant

logger = logging.getLogger("backend.data_pipeline.metadata_manager")

# Site engineering defaults based on MNRE / CEA Indian Grid Benchmarks
SITE_ENGINEERING_BENCHMARKS = {
    "solar": {
        "tilt_angle_deg": 26.0,
        "azimuth_deg": 180.0, # True South
        "dc_ac_ratio": 1.25,
        "temperature_coefficient_pct": -0.35, # %/°C above 25°C
        "inverter_efficiency": 0.985,
        "soiling_loss_pct": 2.5,
        "annual_degradation_pct": 0.55
    },
    "wind": {
        "hub_height_m": 120.0,
        "rotor_diameter_m": 140.0,
        "cut_in_speed_mps": 3.0,
        "rated_speed_mps": 11.5,
        "cut_out_speed_mps": 25.0,
        "power_curve_exponent": 2.2,
        "wake_loss_pct": 5.0,
        "electrical_efficiency": 0.965
    },
    "hybrid": {
        "solar_ratio": 0.60,
        "wind_ratio": 0.40,
        "tilt_angle_deg": 24.0,
        "hub_height_m": 120.0,
        "bess_capacity_mwh": 1200.0,
        "round_trip_efficiency": 0.88
    }
}

class PlantMetadataManager:
    """
    Manages and enriches plant metadata with operational parameters,
    coordinates, technology specifications, and benchmark engineering values.
    """

    @staticmethod
    def get_plant_metadata(db: Session, plant_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch plant record from database and enrich with physical engineering constants.
        """
        plant = db.query(Plant).filter(Plant.id == plant_id).first()
        if not plant:
            logger.warning(f"Plant with ID {plant_id} not found.")
            return None

        plant_type = plant.plant_type.lower()
        benchmarks = SITE_ENGINEERING_BENCHMARKS.get(plant_type, SITE_ENGINEERING_BENCHMARKS["solar"])

        metadata = {
            "plant_id": plant.id,
            "name": plant.name,
            "code": plant.code,
            "plant_type": plant_type,
            "capacity_mw": plant.capacity_mw,
            "latitude": plant.latitude,
            "longitude": plant.longitude,
            "elevation_m": plant.elevation_m or 150.0,
            "technology": plant.technology or "Standard Utility Scale",
            "commissioning_year": plant.commissioning_year or 2020,
            "operator_name": plant.operator_name or "National Grid Utility",
            "status": plant.status,
            "region_id": plant.region_id,
            "state_id": plant.state_id,
            "region_name": plant.region.name if plant.region else None,
            "state_name": plant.state.name if plant.state else None,
            "engineering_params": benchmarks
        }
        return metadata

    @staticmethod
    def get_all_plants_metadata(db: Session) -> List[Dict[str, Any]]:
        """Retrieve metadata for all registered plants."""
        plants = db.query(Plant).all()
        return [PlantMetadataManager.get_plant_metadata(db, p.id) for p in plants if p]
