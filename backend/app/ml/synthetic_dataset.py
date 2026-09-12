import math
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any
from datetime import datetime, timedelta, timezone

from app.ml.features import FeatureEngineer, SOLAR_FEATURES, WIND_FEATURES

def generate_training_dataset(
    plant_metadata: Dict[str, Any],
    days: int = 180
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """
    Generate ground-truth synthetic historical training dataset using physical
    conservation models and realistic meteorological time-series.
    Returns:
        (X_solar, y_solar, X_wind, y_wind)
    """
    base_time = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    total_hours = days * 24
    records = []

    cap = float(plant_metadata.get("capacity_mw", 100.0))
    lat = float(plant_metadata.get("latitude", 23.0))
    lon = float(plant_metadata.get("longitude", 71.0))
    eng = plant_metadata.get("engineering_params", {})

    np.random.seed(42) # Deterministic reproducibility

    for h in range(total_hours):
        t = base_time + timedelta(hours=h)
        hour = t.hour
        day_of_year = t.timetuple().tm_yday

        # Solar Simulation
        if 6 <= hour <= 18:
            solar_elev = math.sin((hour - 6) / 12.0 * math.pi)
            # Seasonal irradiance variation (higher in Mar-May, lower in Dec/Jan & monsoon)
            seasonal_factor = 1.0 + 0.15 * math.sin((day_of_year - 80) / 365.25 * 2 * math.pi)
            cloud = max(0.0, min(100.0, 15.0 + 25.0 * math.sin(h * 0.05) + np.random.normal(0, 8)))
            clear_sky = 1000.0 * solar_elev * seasonal_factor
            ghi = round(max(0.0, clear_sky * (1.0 - (cloud / 100.0) * 0.75)), 1)
            dni = round(max(0.0, ghi * 0.85 * (1.0 - cloud / 100.0)), 1)
            dhi = round(max(0.0, ghi - dni * math.sin(max(0.1, solar_elev))), 1)
            temp = round(28.0 + solar_elev * 11.0 + np.random.normal(0, 1.5), 1)
        else:
            ghi, dni, dhi = 0.0, 0.0, 0.0
            cloud = max(0.0, min(100.0, 10.0 + np.random.normal(0, 5)))
            temp = round(21.0 - ((hour + 4) % 6) * 0.8 + np.random.normal(0, 1.0), 1)

        # Wind Simulation
        wind_seasonal = 7.0 + 3.0 * math.sin((day_of_year - 150) / 365.25 * 2 * math.pi) # Indian monsoon high in Jun-Aug
        wind_diurnal = math.sin((hour - 15) / 24.0 * 2 * math.pi) * 2.5
        wind_100m = round(max(1.5, wind_seasonal + wind_diurnal + np.random.normal(0, 1.2)), 1)
        wind_10m = round(wind_100m * 0.73, 1)
        wind_dir = round((210.0 + math.sin(h * 0.02) * 50.0 + np.random.normal(0, 10)) % 360, 1)

        # Target Generation Calculation (Physical Ground Truth)
        # 1. Solar Target (MW)
        temp_derate = max(0.80, 1.0 - max(0.0, temp - 25.0) * 0.0035)
        inverter_eff = 0.985
        soiling = 0.975
        solar_mw = (ghi / 1000.0) * cap * temp_derate * inverter_eff * soiling
        # Inverter clipping at 1.0 * AC capacity
        solar_target = round(min(cap, max(0.0, solar_mw + np.random.normal(0, 0.01 * cap))), 2)

        # 2. Wind Target (MW)
        cut_in, rated, cut_out = 3.0, 11.5, 25.0
        if wind_100m < cut_in or wind_100m > cut_out:
            wind_mw = 0.0
        elif wind_100m >= rated:
            wind_mw = cap
        else:
            wind_mw = cap * ((wind_100m - cut_in) / (rated - cut_in)) ** 2.2
        wind_target = round(min(cap, max(0.0, wind_mw * 0.95 + np.random.normal(0, 0.015 * cap))), 2)

        records.append({
            "timestamp": t,
            "temperature_c": temp,
            "relative_humidity": round(45.0 + math.cos(hour / 12.0) * 20.0, 1),
            "surface_pressure_hpa": round(1012.0 - (temp * 0.15), 1),
            "cloud_cover_pct": cloud,
            "ghi": ghi,
            "dni": dni,
            "dhi": dhi,
            "wind_speed_10m": wind_10m,
            "wind_speed_100m": wind_100m,
            "wind_direction_deg": wind_dir,
            "solar_generation_mw": solar_target,
            "wind_generation_mw": wind_target
        })

    df = pd.DataFrame(records)

    # Apply Feature Engineering
    X_solar, X_wind = FeatureEngineer.create_feature_matrix(df, plant_metadata)
    y_solar = df["solar_generation_mw"]
    y_wind = df["wind_generation_mw"]

    return X_solar, y_solar, X_wind, y_wind
