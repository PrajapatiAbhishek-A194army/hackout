import unittest
import numpy as np
import pandas as pd

from app.ml.solar_model import SolarForecaster, SOLAR_FEATURES
from app.ml.wind_model import WindForecaster, WIND_FEATURES
from app.ml.synthetic_dataset import generate_synthetic_solar_data, generate_synthetic_wind_data
from app.ml.features import FeatureEngineer

class TestMLAndPhysics(unittest.TestCase):
    """Verifies ML models and physical boundary adherence."""

    def test_01_solar_feature_engineering(self):
        capacity_mw = 500.0
        df_raw = generate_synthetic_solar_data(days=5, capacity_mw=capacity_mw, seed=42)
        metadata = {"tilt": 25.0, "azimuth": 180.0, "tracking": "single_axis", "capacity_mw": capacity_mw}
        X, _ = FeatureEngineer.create_feature_matrix(df_raw, metadata)
        
        self.assertIsNotNone(X)
        for feat in SOLAR_FEATURES:
            self.assertIn(feat, X.columns, f"Missing feature {feat} in solar feature matrix")
        self.assertEqual(len(X), len(df_raw))

    def test_02_wind_feature_engineering(self):
        capacity_mw = 300.0
        df_raw = generate_synthetic_wind_data(days=5, capacity_mw=capacity_mw, seed=42)
        metadata = {"hub_height": 120.0, "rotor_diameter": 140.0, "cut_in": 3.0, "rated": 12.0, "cut_out": 25.0, "capacity_mw": capacity_mw}
        _, X = FeatureEngineer.create_feature_matrix(df_raw, metadata)

        self.assertIsNotNone(X)
        for feat in WIND_FEATURES:
            self.assertIn(feat, X.columns, f"Missing feature {feat} in wind feature matrix")
        self.assertEqual(len(X), len(df_raw))

    def test_03_solar_physical_bounds(self):
        """Ensures solar predictions never go negative and never exceed plant capacity."""
        capacity_mw = 1000.0
        df_raw = generate_synthetic_solar_data(days=3, capacity_mw=capacity_mw, seed=99)
        metadata = {"tilt": 25.0, "azimuth": 180.0, "tracking": "single_axis", "capacity_mw": capacity_mw}
        X, _ = FeatureEngineer.create_feature_matrix(df_raw, metadata)

        forecaster = SolarForecaster(n_estimators=30, max_depth=3)
        forecaster.train(X[SOLAR_FEATURES], df_raw["generation_mw"])

        preds = forecaster.predict(X[SOLAR_FEATURES])
        self.assertTrue(np.all(preds >= 0.0), "Solar generation cannot be negative")
        self.assertTrue(np.all(preds <= capacity_mw + 1.0), "Solar generation cannot exceed rated capacity")

    def test_04_wind_physical_bounds(self):
        """Ensures wind predictions respect turbine physical capacity bounds."""
        capacity_mw = 800.0
        df_raw = generate_synthetic_wind_data(days=3, capacity_mw=capacity_mw, seed=99)
        metadata = {"hub_height": 120.0, "rotor_diameter": 140.0, "cut_in": 3.0, "rated": 12.0, "cut_out": 25.0, "capacity_mw": capacity_mw}
        _, X = FeatureEngineer.create_feature_matrix(df_raw, metadata)

        forecaster = WindForecaster(n_estimators=30, max_depth=3)
        forecaster.train(X[WIND_FEATURES], df_raw["generation_mw"])

        preds = forecaster.predict(X[WIND_FEATURES])
        self.assertTrue(np.all(preds >= 0.0), "Wind generation cannot be negative")
        self.assertTrue(np.all(preds <= capacity_mw + 1.0), "Wind generation cannot exceed rated capacity")

    def test_05_uncertainty_intervals(self):
        """Validates that upper bounds are >= predicted and lower bounds are <= predicted."""
        capacity_mw = 500.0
        df_raw = generate_synthetic_solar_data(days=2, capacity_mw=capacity_mw, seed=77)
        metadata = {"tilt": 25.0, "azimuth": 180.0, "tracking": "single_axis", "capacity_mw": capacity_mw}
        X, _ = FeatureEngineer.create_feature_matrix(df_raw, metadata)

        forecaster = SolarForecaster(n_estimators=20, max_depth=3)
        forecaster.train(X[SOLAR_FEATURES], df_raw["generation_mw"])

        intervals = forecaster.predict_with_intervals(X, capacity_mw=capacity_mw)
        self.assertTrue(np.all(intervals["upper_bound_mw"] >= intervals["predicted_mw"]))
        self.assertTrue(np.all(intervals["lower_bound_mw"] <= intervals["predicted_mw"]))
        self.assertTrue(np.all(intervals["confidence_score"] >= 0.0))
        self.assertTrue(np.all(intervals["confidence_score"] <= 1.0))

if __name__ == "__main__":
    unittest.main()
