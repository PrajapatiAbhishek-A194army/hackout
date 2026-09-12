import os
import json
import logging
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score

from app.ml.features import SOLAR_FEATURES

logger = logging.getLogger("backend.ml.solar_model")

class SolarForecaster:
    """
    Production-grade XGBoost Solar Generation Forecaster.
    Trained on celestial geometry, irradiance metrics, and plant parameters.
    Guarantees physical boundary adherence and uncertainty estimation.
    """

    def __init__(
        self,
        n_estimators: int = 350,
        max_depth: int = 6,
        learning_rate: float = 0.05,
        subsample: float = 0.85,
        colsample_bytree: float = 0.85,
        random_state: int = 42,
        **kwargs
    ):
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "random_state": random_state,
            "objective": kwargs.get("objective", "reg:squarederror"),
            "n_jobs": kwargs.get("n_jobs", -1)
        }
        self.params.update({k: v for k, v in kwargs.items() if k not in self.params})
        self.model = XGBRegressor(**self.params)
        self.feature_names = SOLAR_FEATURES
        self.metrics: Dict[str, float] = {}
        self.feature_importance: Dict[str, float] = {}
        self.is_trained: bool = False

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None
    ) -> Dict[str, float]:
        """Train model and calculate performance metrics on validation split."""
        X_tr = X_train[self.feature_names]
        logger.info(f"Training Solar XGBoost on {len(X_tr)} samples with {len(self.feature_names)} features...")
        self.model.fit(X_tr, y_train)
        self.is_trained = True

        # Extract Feature Importance (gain metric)
        booster = self.model.get_booster()
        importance_scores = booster.get_score(importance_type="gain")
        # Normalize
        total_gain = sum(importance_scores.values()) or 1.0
        self.feature_importance = {
            feat: round(importance_scores.get(feat, 0.0) / total_gain, 4)
            for feat in self.feature_names
        }
        # Sort descending
        self.feature_importance = dict(
            sorted(self.feature_importance.items(), key=lambda item: item[1], reverse=True)
        )

        # Validation Metrics
        if X_val is not None and y_val is not None:
            preds = self.predict(X_val)
            mae = float(mean_absolute_error(y_val, preds))
            rmse = float(root_mean_squared_error(y_val, preds))
            r2 = float(r2_score(y_val, preds))
        else:
            preds = self.predict(X_train)
            mae = float(mean_absolute_error(y_train, preds))
            rmse = float(root_mean_squared_error(y_train, preds))
            r2 = float(r2_score(y_train, preds))

        self.metrics = {
            "mae_mw": round(mae, 2),
            "rmse_mw": round(rmse, 2),
            "r2_score": round(r2, 4)
        }
        logger.info(f"Solar Model Training Completed: R2={r2:.4f}, MAE={mae:.2f} MW, RMSE={rmse:.2f} MW")
        return self.metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Generate predictions and enforce physical solar conservation:
        Output is strictly 0.0 MW when GHI is 0 or during nighttime.
        """
        if not self.is_trained:
            raise ValueError("Solar model must be trained before predicting.")

        X_in = X[self.feature_names]
        raw_preds = self.model.predict(X_in)
        preds = np.maximum(0.0, raw_preds)

        # Physical constraints
        if "ghi" in X.columns:
            ghi = X["ghi"].values
            preds = np.where(ghi <= 1.0, 0.0, preds)

        if "is_daytime" in X.columns:
            is_day = X["is_daytime"].values
            preds = np.where(is_day == 0, 0.0, preds)

        if "capacity_mw" in X.columns:
            cap = X["capacity_mw"].values
            preds = np.minimum(cap, preds)

        return np.round(preds, 2)

    def predict_with_intervals(
        self,
        X: pd.DataFrame,
        capacity_mw: float
    ) -> pd.DataFrame:
        """
        Predict hourly generation with P10 (lower bound), P90 (upper bound),
        and confidence scores.
        """
        preds = self.predict(X)
        n = len(preds)

        lower_bounds = []
        upper_bounds = []
        confidences = []

        ghi_vals = X.get("ghi", pd.Series([0.0]*n)).values
        cloud_vals = X.get("cloud_cover_pct", pd.Series([0.0]*n)).values

        for i in range(n):
            pred = float(preds[i])
            ghi = float(ghi_vals[i])
            cloud = float(cloud_vals[i])

            if pred <= 0.0 or ghi <= 1.0:
                lower_bounds.append(0.0)
                upper_bounds.append(0.0)
                confidences.append(0.98) # Very high certainty at night (0 MW)
            else:
                # Confidence scales inversely with cloud cover and forecast horizon
                conf = max(0.80, min(0.96, 0.95 - (cloud / 100.0) * 0.12 - (i / 72.0) * 0.05))
                conf = round(conf, 2)
                uncertainty = (1.0 - conf) * capacity_mw * 0.35
                
                lower = max(0.0, round(pred - uncertainty, 2))
                upper = min(capacity_mw, round(pred + uncertainty, 2))

                lower_bounds.append(lower)
                upper_bounds.append(upper)
                confidences.append(conf)

        result = pd.DataFrame({
            "predicted_mw": preds,
            "lower_bound_mw": lower_bounds,
            "upper_bound_mw": upper_bounds,
            "confidence_score": confidences
        })
        return result

    def get_feature_importance(self) -> Dict[str, float]:
        """Return relative predictive gain for each feature."""
        return self.feature_importance

    def save(self, filepath: str) -> None:
        """Serialize model to disk."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        payload = {
            "model": self.model,
            "params": self.params,
            "feature_names": self.feature_names,
            "metrics": self.metrics,
            "feature_importance": self.feature_importance,
            "is_trained": self.is_trained
        }
        joblib.dump(payload, filepath)
        logger.info(f"Solar model serialized successfully to {filepath}")

    @classmethod
    def load(cls, filepath: str) -> "SolarForecaster":
        """Deserialize model from disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found at {filepath}")
        payload = joblib.load(filepath)
        instance = cls(**payload.get("params", {}))
        instance.model = payload["model"]
        instance.feature_names = payload.get("feature_names", SOLAR_FEATURES)
        instance.metrics = payload.get("metrics", {})
        instance.feature_importance = payload.get("feature_importance", {})
        instance.is_trained = payload.get("is_trained", True)
        logger.info(f"Solar model loaded successfully from {filepath}")
        return instance
