import os
import json
import logging
import pandas as pd
from datetime import datetime, timezone
from sklearn.model_selection import train_test_split

from app.database.session import SessionLocal
from app.models.plant import Plant
from app.models.model_run import ModelRun
from app.ml.features import FeatureEngineer, WIND_FEATURES
from app.ml.synthetic_dataset import generate_training_dataset
from app.ml.wind_model import WindForecaster

logger = logging.getLogger("backend.ml.train_wind")

def train_and_register_wind_model(days: int = 180) -> WindForecaster:
    """
    Train production Wind XGBoost model, evaluate on test split,
    serialize model artifact, and update database model registry.
    """
    print(f"[TRAIN] Synthesizing {days} days of aerodynamic training data across Indian wind corridors...")
    db = SessionLocal()

    try:
        # Load active wind plants
        wind_plants = db.query(Plant).filter(Plant.plant_type.in_(["wind", "hybrid"])).all()
        if not wind_plants:
            raise ValueError("No wind plants found in database to base training metadata on.")

        all_X = []
        all_y = []

        for p in wind_plants:
            meta = {
                "plant_id": p.id,
                "name": p.name,
                "capacity_mw": p.capacity_mw * (0.4 if p.plant_type == "hybrid" else 1.0),
                "latitude": p.latitude,
                "longitude": p.longitude,
                "elevation_m": p.elevation_m or 50.0,
                "engineering_params": {
                    "hub_height_m": 120.0,
                    "rotor_diameter_m": 140.0,
                    "cut_in_speed_mps": 3.0,
                    "rated_speed_mps": 11.5,
                    "cut_out_speed_mps": 25.0
                }
            }
            _, _, X_w, y_w = generate_training_dataset(meta, days=days)
            all_X.append(X_w)
            all_y.append(y_w)

        X_full = pd.concat(all_X, ignore_index=True)
        y_full = pd.concat(all_y, ignore_index=True)

        print(f"[TRAIN] Total training samples: {len(X_full)} across {len(wind_plants)} wind facilities.")

        # Train/test split (80/20)
        X_train, X_val, y_train, y_val = train_test_split(
            X_full, y_full, test_size=0.20, random_state=42, shuffle=True
        )

        forecaster = WindForecaster(
            n_estimators=400,
            max_depth=7,
            learning_rate=0.04,
            subsample=0.80,
            colsample_bytree=0.80
        )

        metrics = forecaster.train(X_train, y_train, X_val, y_val)
        print(f"[EVALUATION] Validation Results -> R2: {metrics['r2_score']:.4f}, MAE: {metrics['mae_mw']} MW, RMSE: {metrics['rmse_mw']} MW")

        # Top 5 predictive features
        top_features = list(forecaster.feature_importance.items())[:5]
        print("[FEATURE IMPORTANCE] Top 5 drivers:")
        for feat, score in top_features:
            print(f"  - {feat}: {score * 100:.1f}%")

        # Save model artifact
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_dir = os.path.join(backend_dir, "trained_models")
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "wind_xgboost_v1.joblib")
        forecaster.save(model_path)
        print(f"[ARTIFACT] Saved model to {model_path}")

        # Register in PostgreSQL model_runs table
        version_str = "v1.0.0-wind-xgb"
        existing_run = db.query(ModelRun).filter(ModelRun.version == version_str).first()
        if existing_run:
            existing_run.mae_mw = metrics["mae_mw"]
            existing_run.rmse_mw = metrics["rmse_mw"]
            existing_run.r2_score = metrics["r2_score"]
            existing_run.parameters = json.dumps(forecaster.params)
            existing_run.feature_importance = json.dumps(forecaster.feature_importance)
            existing_run.model_path = "trained_models/wind_xgboost_v1.joblib"
            existing_run.is_active = True
        else:
            model_run = ModelRun(
                model_name="wind_xgboost_ensemble",
                model_type="wind",
                version=version_str,
                mae_mw=metrics["mae_mw"],
                rmse_mw=metrics["rmse_mw"],
                r2_score=metrics["r2_score"],
                parameters=json.dumps(forecaster.params),
                feature_importance=json.dumps(forecaster.feature_importance),
                model_path="trained_models/wind_xgboost_v1.joblib",
                is_active=True
            )
            db.add(model_run)

        db.commit()
        print(f"[REGISTRY] Registered model {version_str} in database model_runs table.")
        return forecaster

    finally:
        db.close()

if __name__ == "__main__":
    train_and_register_wind_model()
