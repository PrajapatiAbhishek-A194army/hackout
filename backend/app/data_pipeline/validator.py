import logging
import math
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, List
from datetime import timezone

logger = logging.getLogger("backend.data_pipeline.validator")

class ValidationReport:
    """Structured report produced after data validation and cleaning."""
    def __init__(self):
        self.is_valid: bool = True
        self.total_records: int = 0
        self.missing_imputed: int = 0
        self.clipped_outliers: int = 0
        self.night_zeroed: int = 0
        self.warnings: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "total_records": self.total_records,
            "missing_imputed": self.missing_imputed,
            "clipped_outliers": self.clipped_outliers,
            "night_zeroed": self.night_zeroed,
            "warnings": self.warnings
        }

class DataValidator:
    """
    Production-grade meteorological and time-series validator.
    Enforces physical conservation laws, boundary conditions, and completeness.
    """

    # Physical meteorological sanity thresholds
    LIMITS = {
        "ghi": (0.0, 1400.0),             # W/m²
        "dni": (0.0, 1200.0),             # W/m²
        "dhi": (0.0, 800.0),              # W/m²
        "temperature_c": (-15.0, 55.0),   # °C
        "relative_humidity": (0.0, 100.0),# %
        "cloud_cover_pct": (0.0, 100.0),  # %
        "surface_pressure_hpa": (800.0, 1100.0), # hPa
        "wind_speed_10m": (0.0, 55.0),    # m/s
        "wind_speed_100m": (0.0, 65.0),   # m/s
        "wind_direction_deg": (0.0, 360.0)# degrees
    }

    # Geographic boundary of India and offshore exclusive economic zone
    INDIA_BOUNDS = {
        "min_lat": 6.0,
        "max_lat": 38.0,
        "min_lon": 68.0,
        "max_lon": 98.0
    }

    @classmethod
    def validate_coordinates(cls, latitude: float, longitude: float) -> Tuple[bool, str]:
        """Validate geographic coordinates and warn if outside India."""
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            return False, f"Coordinates ({latitude}, {longitude}) are out of mathematical range."

        in_india = (
            cls.INDIA_BOUNDS["min_lat"] <= latitude <= cls.INDIA_BOUNDS["max_lat"] and
            cls.INDIA_BOUNDS["min_lon"] <= longitude <= cls.INDIA_BOUNDS["max_lon"]
        )
        if not in_india:
            return True, f"Coordinates ({latitude}, {longitude}) are outside the Indian subcontinent bounding box."

        return True, "Valid Indian geographic coordinates."

    @classmethod
    def validate_and_clean(
        cls,
        df: pd.DataFrame,
        latitude: float = 23.0
    ) -> Tuple[pd.DataFrame, ValidationReport]:
        """
        Validate and clean input meteorological time-series DataFrame.
        Performs:
        1. Timestamp continuity and sorting
        2. Missing value detection and smart interpolation
        3. Physical limit clipping
        4. Nighttime solar irradiance zeroing
        5. Consistency enforcement (e.g. DHI <= GHI)
        """
        report = ValidationReport()

        if df is None or df.empty:
            report.is_valid = False
            report.warnings.append("Empty or None DataFrame received for validation.")
            return pd.DataFrame(), report

        cleaned = df.copy()
        report.total_records = len(cleaned)

        # 1. Timestamp validation
        if "timestamp" not in cleaned.columns:
            report.is_valid = False
            report.warnings.append("Missing 'timestamp' column in data.")
            return cleaned, report

        cleaned["timestamp"] = pd.to_datetime(cleaned["timestamp"], utc=True)
        cleaned = cleaned.sort_values("timestamp").drop_duplicates(subset=["timestamp"])

        # Check for gaps > 1 hour
        time_diffs = cleaned["timestamp"].diff()
        unexpected_gaps = (time_diffs > pd.Timedelta(hours=1)).sum()
        if unexpected_gaps > 0:
            report.warnings.append(f"Detected {unexpected_gaps} timestamp gaps exceeding 1 hour.")

        # 2. Missing value detection & interpolation
        numeric_cols = [c for c in cls.LIMITS.keys() if c in cleaned.columns]
        null_count_before = cleaned[numeric_cols].isnull().sum().sum()

        if null_count_before > 0:
            report.warnings.append(f"Found {null_count_before} missing values across numeric columns. Imputing...")
            # Short gap linear interpolation (up to 3 consecutive NaNs)
            cleaned[numeric_cols] = cleaned[numeric_cols].interpolate(method="linear", limit=3)
            # Forward fill / backward fill remaining
            cleaned[numeric_cols] = cleaned[numeric_cols].ffill().bfill()
            
            # If still null, fill with physical midpoint defaults
            defaults = {
                "ghi": 0.0, "dni": 0.0, "dhi": 0.0, "temperature_c": 25.0,
                "relative_humidity": 50.0, "cloud_cover_pct": 20.0,
                "surface_pressure_hpa": 1013.25, "wind_speed_10m": 4.5,
                "wind_speed_100m": 6.5, "wind_direction_deg": 180.0
            }
            cleaned = cleaned.fillna(value=defaults)
            report.missing_imputed = int(null_count_before)

        # 3. Physical Sanity Bounds & Outlier Clipping
        clipped_count = 0
        for col, (lower, upper) in cls.LIMITS.items():
            if col in cleaned.columns:
                outliers = ((cleaned[col] < lower) | (cleaned[col] > upper)).sum()
                if outliers > 0:
                    clipped_count += int(outliers)
                    cleaned[col] = cleaned[col].clip(lower=lower, upper=upper)
        report.clipped_outliers = clipped_count
        if clipped_count > 0:
            report.warnings.append(f"Clipped {clipped_count} values outside physical limits.")

        # 4. Nighttime solar irradiance zeroing
        night_zero_count = 0
        hours = cleaned["timestamp"].dt.hour
        # In India, solar irradiance between 19:00 and 05:00 UTC (or local night) is 0
        is_night = (hours < 6) | (hours > 18)

        for col in ["ghi", "dni", "dhi"]:
            if col in cleaned.columns:
                night_positive = (is_night & (cleaned[col] > 0.0)).sum()
                if night_positive > 0:
                    night_zero_count += int(night_positive)
                    cleaned.loc[is_night, col] = 0.0

        report.night_zeroed = night_zero_count

        # 5. Solar consistency: DHI cannot exceed GHI
        if "ghi" in cleaned.columns and "dhi" in cleaned.columns:
            inconsistent = cleaned["dhi"] > cleaned["ghi"]
            if inconsistent.sum() > 0:
                cleaned.loc[inconsistent, "dhi"] = cleaned.loc[inconsistent, "ghi"]

        logger.info(
            f"Validation complete for {report.total_records} records. "
            f"Imputed: {report.missing_imputed}, Clipped: {report.clipped_outliers}, Night Zeroed: {report.night_zeroed}"
        )
        return cleaned, report
