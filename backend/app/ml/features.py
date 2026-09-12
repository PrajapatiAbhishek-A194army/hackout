import math
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

# Standardized Feature Columns for ML Models
SOLAR_FEATURES = [
    # Meteorological & Radiation
    "ghi",
    "dni",
    "dhi",
    "effective_ghi",
    "clearness_index",
    "temperature_c",
    "temp_derate_factor",
    "cloud_cover_pct",
    "relative_humidity",
    "surface_pressure_hpa",
    "air_mass",
    "solar_zenith_deg",
    "solar_elevation_deg",
    
    # Temporal & Cyclical
    "hour_sin",
    "hour_cos",
    "day_sin",
    "day_cos",
    "month_sin",
    "month_cos",
    "is_daytime",
    "solar_noon_dist",
    
    # Lags & Dynamics
    "ghi_lag_1",
    "ghi_lag_2",
    "ghi_lag_3",
    "ghi_ramp_1h",
    "ghi_rolling_mean_3h",
    "ghi_rolling_std_3h",
    "ghi_rolling_max_3h",
    
    # Site Engineering
    "capacity_mw",
    "latitude",
    "longitude",
    "elevation_m",
    "dc_ac_ratio",
    "tilt_angle_deg"
]

WIND_FEATURES = [
    # Aerodynamic & Meteorological
    "wind_speed_10m",
    "wind_speed_100m",
    "wind_power_density",
    "wind_shear_exponent",
    "wind_shear_velocity",
    "wind_dir_sin",
    "wind_dir_cos",
    "air_density_kg_m3",
    "temperature_c",
    "relative_humidity",
    "surface_pressure_hpa",
    
    # Temporal & Cyclical
    "hour_sin",
    "hour_cos",
    "day_sin",
    "day_cos",
    "month_sin",
    "month_cos",
    
    # Lags & Dynamics
    "wind_100m_lag_1",
    "wind_100m_lag_2",
    "wind_100m_lag_3",
    "wind_ramp_1h",
    "wind_rolling_mean_3h",
    "wind_rolling_std_3h",
    "wind_rolling_max_3h",
    "wind_rolling_mean_6h",
    "wind_rolling_max_6h",
    
    # Site Engineering
    "capacity_mw",
    "latitude",
    "longitude",
    "elevation_m",
    "hub_height_m"
]

class FeatureEngineer:
    """
    Production-grade Feature Engineering Engine for Renewable Generation Forecasting.
    Transforms raw weather time-series and site metadata into enriched feature matrices.
    """

    @staticmethod
    def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
        """Compute sinusoidal and cosinusoidal cyclical time encodings."""
        result = df.copy()
        if "timestamp" not in result.columns:
            return result

        ts = pd.to_datetime(result["timestamp"], utc=True)
        hour = ts.dt.hour
        day_of_year = ts.dt.dayofyear
        month = ts.dt.month

        # Diurnal (24-hour cycle)
        result["hour_sin"] = np.sin(2.0 * np.pi * hour / 24.0)
        result["hour_cos"] = np.cos(2.0 * np.pi * hour / 24.0)

        # Seasonal (365.25-day cycle)
        result["day_sin"] = np.sin(2.0 * np.pi * day_of_year / 365.25)
        result["day_cos"] = np.cos(2.0 * np.pi * day_of_year / 365.25)

        # Annual (12-month cycle)
        result["month_sin"] = np.sin(2.0 * np.pi * month / 12.0)
        result["month_cos"] = np.cos(2.0 * np.pi * month / 12.0)

        # Solar operational markers
        result["is_daytime"] = ((hour >= 6) & (hour <= 18)).astype(int)
        result["solar_noon_dist"] = np.abs(hour - 12.0)

        return result

    @staticmethod
    def add_solar_features(df: pd.DataFrame, metadata: Dict[str, Any]) -> pd.DataFrame:
        """Compute celestial geometry, clearness index, and thermal derating."""
        result = df.copy()
        ts = pd.to_datetime(result["timestamp"], utc=True)
        lat = float(metadata.get("latitude", 23.0))
        lat_rad = math.radians(lat)

        day_of_year = ts.dt.dayofyear
        hour = ts.dt.hour

        # 1. Solar declination angle delta
        # Cooper's formula (in radians)
        declination_rad = np.radians(23.45 * np.sin(2.0 * np.pi * (284.0 + day_of_year) / 365.0))

        # 2. Solar hour angle omega (15 deg per hour from solar noon)
        hour_angle_rad = np.radians(15.0 * (hour - 12.0))

        # 3. Cosine of Zenith Angle
        cos_zenith = np.sin(lat_rad) * np.sin(declination_rad) + np.cos(lat_rad) * np.cos(declination_rad) * np.cos(hour_angle_rad)
        cos_zenith = np.clip(cos_zenith, -1.0, 1.0)
        zenith_rad = np.arccos(cos_zenith)
        zenith_deg = np.degrees(zenith_rad)
        elevation_deg = np.maximum(0.0, 90.0 - zenith_deg)

        result["solar_zenith_deg"] = zenith_deg
        result["solar_elevation_deg"] = elevation_deg

        # 4. Extraterrestrial solar radiation (Spencer formula)
        i0 = 1367.0 * (1.0 + 0.033 * np.cos(2.0 * np.pi * day_of_year / 365.0)) * np.maximum(0.0, cos_zenith)

        # 5. Clearness Index (kt)
        ghi = result.get("ghi", 0.0)
        result["clearness_index"] = np.clip(ghi / (i0 + 1e-4), 0.0, 1.0)

        # 6. Thermal derating (0.35% / deg C above 25 deg C)
        temp = result.get("temperature_c", 25.0)
        result["temp_derate_factor"] = np.maximum(0.80, 1.0 - np.maximum(0.0, temp - 25.0) * 0.0035)

        # 7. Effective GHI accounting for cloud attenuation
        cloud = result.get("cloud_cover_pct", 0.0)
        result["effective_ghi"] = np.maximum(0.0, ghi * (1.0 - (cloud / 100.0) * 0.75))

        # 8. Optical Air Mass (Kasten-Young model)
        result["air_mass"] = np.where(
            elevation_deg > 0.5,
            1.0 / (np.sin(np.radians(elevation_deg)) + 0.50572 * np.power(elevation_deg + 6.07995, -1.6364)),
            38.0 # Night / extreme zenith cutoff
        )

        return result

    @staticmethod
    def add_wind_features(df: pd.DataFrame, metadata: Dict[str, Any]) -> pd.DataFrame:
        """Compute aerodynamic properties, air density, and wind power density."""
        result = df.copy()

        temp_c = result.get("temperature_c", 25.0)
        pressure_hpa = result.get("surface_pressure_hpa", 1013.25)
        # Ideal gas law: rho = (P * 100) / (R_specific * T_kelvin)
        # R_specific for dry air = 287.05 J/(kg K)
        temp_k = temp_c + 273.15
        air_density = (pressure_hpa * 100.0) / (287.05 * temp_k)
        result["air_density_kg_m3"] = np.clip(air_density, 0.95, 1.35)

        w10 = np.maximum(0.0, result.get("wind_speed_10m", 0.0))
        w100 = np.maximum(0.0, result.get("wind_speed_100m", 0.0))

        # Wind Power Density (WPD) = 0.5 * rho * v^3 (in W/m2)
        result["wind_power_density"] = 0.5 * result["air_density_kg_m3"] * np.power(w100, 3)

        # Wind shear exponent: alpha = ln(v100 / v10) / ln(100 / 10)
        # ln(10) ~ 2.302585
        ratio = np.maximum(0.1, w100) / np.maximum(0.1, w10)
        alpha = np.log(ratio) / 2.302585
        result["wind_shear_exponent"] = np.clip(alpha, 0.0, 0.60)
        result["wind_shear_velocity"] = np.maximum(0.0, w100 - w10)

        # Directional components (sine & cosine)
        wind_dir = result.get("wind_direction_deg", 180.0)
        wind_dir_rad = np.radians(wind_dir)
        result["wind_dir_sin"] = np.sin(wind_dir_rad)
        result["wind_dir_cos"] = np.cos(wind_dir_rad)

        return result

    @staticmethod
    def add_lag_and_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
        """Compute time lags, rolling window statistics, and 1-hour ramp rate velocities."""
        result = df.copy()

        # Solar lags and statistics
        if "ghi" in result.columns:
            result["ghi_lag_1"] = result["ghi"].shift(1).bfill()
            result["ghi_lag_2"] = result["ghi"].shift(2).bfill()
            result["ghi_lag_3"] = result["ghi"].shift(3).bfill()
            result["ghi_ramp_1h"] = result["ghi"] - result["ghi_lag_1"]

            # Rolling stats (min_periods=1 ensures no NaNs at edges)
            result["ghi_rolling_mean_3h"] = result["ghi"].rolling(window=3, min_periods=1).mean()
            result["ghi_rolling_std_3h"] = result["ghi"].rolling(window=3, min_periods=1).std().fillna(0.0)
            result["ghi_rolling_max_3h"] = result["ghi"].rolling(window=3, min_periods=1).max()

        # Wind lags and statistics
        if "wind_speed_100m" in result.columns:
            w100 = result["wind_speed_100m"]
            result["wind_100m_lag_1"] = w100.shift(1).bfill()
            result["wind_100m_lag_2"] = w100.shift(2).bfill()
            result["wind_100m_lag_3"] = w100.shift(3).bfill()
            result["wind_ramp_1h"] = w100 - result["wind_100m_lag_1"]

            result["wind_rolling_mean_3h"] = w100.rolling(window=3, min_periods=1).mean()
            result["wind_rolling_std_3h"] = w100.rolling(window=3, min_periods=1).std().fillna(0.0)
            result["wind_rolling_max_3h"] = w100.rolling(window=3, min_periods=1).max()

            result["wind_rolling_mean_6h"] = w100.rolling(window=6, min_periods=1).mean()
            result["wind_rolling_max_6h"] = w100.rolling(window=6, min_periods=1).max()

        return result

    @staticmethod
    def add_site_metadata_features(df: pd.DataFrame, metadata: Dict[str, Any]) -> pd.DataFrame:
        """Inject site geometry and technical equipment parameters."""
        result = df.copy()
        eng = metadata.get("engineering_params", {})

        result["capacity_mw"] = float(metadata.get("capacity_mw", 100.0))
        result["latitude"] = float(metadata.get("latitude", 23.0))
        result["longitude"] = float(metadata.get("longitude", 71.0))
        result["elevation_m"] = float(metadata.get("elevation_m", 150.0))

        # Solar specifics
        result["dc_ac_ratio"] = float(eng.get("dc_ac_ratio", 1.25))
        result["tilt_angle_deg"] = float(eng.get("tilt_angle_deg", 26.0))

        # Wind specifics
        result["hub_height_m"] = float(eng.get("hub_height_m", 120.0))

        return result

    @classmethod
    def create_feature_matrix(
        cls,
        df: pd.DataFrame,
        metadata: Dict[str, Any]
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Complete end-to-end transformation.
        Returns:
            solar_matrix: DataFrame matching SOLAR_FEATURES
            wind_matrix: DataFrame matching WIND_FEATURES
        """
        # Step 1: Time features
        step1 = cls.add_time_features(df)
        # Step 2: Solar features
        step2 = cls.add_solar_features(step1, metadata)
        # Step 3: Wind features
        step3 = cls.add_wind_features(step2, metadata)
        # Step 4: Lags & rolling stats
        step4 = cls.add_lag_and_rolling_features(step3)
        # Step 5: Site metadata
        full_df = cls.add_site_metadata_features(step4, metadata)

        # Fill any remaining NaNs
        full_df = full_df.fillna(0.0)

        # Extract targeted feature matrices
        solar_cols = [c for c in SOLAR_FEATURES if c in full_df.columns]
        wind_cols = [c for c in WIND_FEATURES if c in full_df.columns]

        return full_df[solar_cols], full_df[wind_cols]
