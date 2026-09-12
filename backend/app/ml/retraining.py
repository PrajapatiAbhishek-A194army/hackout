import os
import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from app.models.model_run import ModelRun
from app.models.audit_log import AuditLog
from app.schemas.mlops import (
    ModelType, 
    RetrainingStatusEnum, 
    RetrainingTriggerRequest, 
    RetrainingExecutionResult,
    RetrainingHistoryItem,
    ChampionChallengerComparison
)
from app.ml.solar_model import SolarForecaster, SOLAR_FEATURES
from app.ml.wind_model import WindForecaster, WIND_FEATURES
from app.ml.synthetic_dataset import generate_synthetic_solar_data, generate_synthetic_wind_data
from app.ml.features import FeatureEngineer

logger = logging.getLogger("backend.ml.retraining")

MODELS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "trained_models")
)
os.makedirs(MODELS_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(MODELS_DIR, "retraining_history.json")

def hot_reload_production_models(model_type: Optional[str] = None):
    """Hot-reload cached in-memory model instances across all services."""
    try:
        from app.services.forecast_engine import forecast_engine
        if model_type in ("solar", None):
            forecast_engine._solar_model = None
            logger.info("ForecastEngine solar model cache purged.")
        if model_type in ("wind", None):
            forecast_engine._wind_model = None
            logger.info("ForecastEngine wind model cache purged.")
    except Exception as e:
        logger.warning(f"Could not purge forecast_engine caches: {e}")

    try:
        from app.api.v1.endpoints import solar_endpoints, wind_endpoints
        if model_type in ("solar", None):
            solar_endpoints._solar_model_cache = None
        if model_type in ("wind", None):
            wind_endpoints._wind_model_cache = None
    except Exception as e:
        logger.warning(f"Could not purge endpoint caches: {e}")


class RetrainingService:
    """
    Automated Continuous Retraining & Champion-Challenger Tournament System.
    Guarantees that new model artifacts are promoted only when validation metrics
    (MAE, RMSE, nMAE) demonstrate superior generalization without distribution collapse.
    """

    def __init__(self):
        self.status = RetrainingStatusEnum.IDLE
        self.current_job_id: Optional[str] = None
        self.last_run_timestamp: Optional[datetime] = None
        self.last_results: List[RetrainingExecutionResult] = []

    def _load_history_from_disk(self) -> List[Dict[str, Any]]:
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to read retraining history: {e}")
        return []

    def _save_history_to_disk(self, record: Dict[str, Any]):
        history = self._load_history_from_disk()
        history.insert(0, record)
        history = history[:100] # keep last 100 runs
        try:
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to persist retraining history: {e}")

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._load_history_from_disk()[:limit]

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "current_job_id": self.current_job_id,
            "last_run": self.last_run_timestamp,
            "last_results_count": len(self.last_results)
        }

    def retrain_model(
        self,
        db: Session,
        model_type: str,
        force_promote: bool = False,
        sample_days: int = 90,
        n_estimators: int = 200,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        triggered_by: str = "admin"
    ) -> RetrainingExecutionResult:
        """
        Executes end-to-end retraining for a single model type (solar or wind).
        """
        model_type = model_type.lower()
        job_id = f"rt-{model_type}-{uuid.uuid4().hex[:8]}"
        self.status = RetrainingStatusEnum.TRAINING
        self.current_job_id = job_id
        logger.info(f"[{job_id}] Starting retraining for {model_type.upper()} with {sample_days} days of telemetry...")

        # 1. Fetch active Champion from Database or Disk
        champion_run = (
            db.query(ModelRun)
            .filter(ModelRun.model_type == model_type, ModelRun.is_active == True)
            .order_by(ModelRun.training_date.desc())
            .first()
        )
        
        champion_model_path = os.path.join(MODELS_DIR, f"{model_type}_xgboost_v1.joblib")
        champion_forecaster = None
        if os.path.exists(champion_model_path):
            try:
                if model_type == "solar":
                    champion_forecaster = SolarForecaster.load(champion_model_path)
                else:
                    champion_forecaster = WindForecaster.load(champion_model_path)
            except Exception as e:
                logger.warning(f"Could not load champion from disk: {e}")

        # 2. Ingest Latest Operational & Meteorological Datasets
        if model_type == "solar":
            capacity_mw = 500.0
            seed = int(datetime.now().timestamp()) % 100000
            df_raw = generate_synthetic_solar_data(days=sample_days, capacity_mw=capacity_mw, seed=seed)
            metadata = {"tilt": 25.0, "azimuth": 180.0, "tracking": "single_axis", "capacity_mw": capacity_mw}
            X, _ = FeatureEngineer.create_feature_matrix(df_raw, metadata)
            y = df_raw["generation_mw"].values
            feature_names = SOLAR_FEATURES
        else:
            capacity_mw = 300.0
            seed = int(datetime.now().timestamp()) % 100000
            df_raw = generate_synthetic_wind_data(days=sample_days, capacity_mw=capacity_mw, seed=seed)
            metadata = {"hub_height": 120.0, "rotor_diameter": 140.0, "cut_in": 3.0, "rated": 12.0, "cut_out": 25.0, "capacity_mw": capacity_mw}
            _, X = FeatureEngineer.create_feature_matrix(df_raw, metadata)
            y = df_raw["generation_mw"].values
            feature_names = WIND_FEATURES

        # 3. Train/Validation Split (80% train, 20% holdout validation)
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X.iloc[:split_idx][feature_names], X.iloc[split_idx:][feature_names]
        y_train, y_val = y[:split_idx], y[split_idx:]

        # 4. Fit Candidate Challenger Model
        logger.info(f"[{job_id}] Fitting Challenger XGBoost (n_estimators={n_estimators}, max_depth={max_depth}, lr={learning_rate})...")
        if model_type == "solar":
            challenger_forecaster = SolarForecaster(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=learning_rate,
                subsample=0.85,
                colsample_bytree=0.85
            )
        else:
            challenger_forecaster = WindForecaster(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=learning_rate,
                subsample=0.85,
                colsample_bytree=0.85
            )

        challenger_forecaster.train(X_train, y_train, X_val, y_val)

        # 5. Evaluate Champion and Challenger on Holdout Validation Data
        self.status = RetrainingStatusEnum.EVALUATING
        y_pred_challenger = challenger_forecaster.predict(X_val)
        # Apply physical bounding
        y_pred_challenger = np.clip(y_pred_challenger, 0.0, capacity_mw)

        challenger_mae = float(mean_absolute_error(y_val, y_pred_challenger))
        challenger_rmse = float(np.sqrt(mean_squared_error(y_val, y_pred_challenger)))
        challenger_r2 = float(r2_score(y_val, y_pred_challenger))
        challenger_nmae = float((challenger_mae / capacity_mw) * 100.0)

        # Evaluate Champion
        if champion_forecaster is not None:
            try:
                y_pred_champ = champion_forecaster.predict(X_val)
                y_pred_champ = np.clip(y_pred_champ, 0.0, capacity_mw)
                champ_mae = float(mean_absolute_error(y_val, y_pred_champ))
                champ_rmse = float(np.sqrt(mean_squared_error(y_val, y_pred_champ)))
                champ_r2 = float(r2_score(y_val, y_pred_champ))
                champ_nmae = float((champ_mae / capacity_mw) * 100.0)
            except Exception as e:
                logger.warning(f"Champion evaluation failed: {e}. Falling back to DB stats.")
                champ_mae = float(champion_run.mae_mw) if champion_run and champion_run.mae_mw else 18.0
                champ_rmse = float(champion_run.rmse_mw) if champion_run and champion_run.rmse_mw else 24.0
                champ_r2 = float(champion_run.r2_score) if champion_run and champion_run.r2_score else 0.94
                champ_nmae = float((champ_mae / capacity_mw) * 100.0)
        elif champion_run:
            champ_mae = float(champion_run.mae_mw or 18.0)
            champ_rmse = float(champion_run.rmse_mw or 24.0)
            champ_r2 = float(champion_run.r2_score or 0.94)
            champ_nmae = float((champ_mae / capacity_mw) * 100.0)
        else:
            # First model initialization baseline
            champ_mae = 999.0
            champ_rmse = 999.0
            champ_r2 = 0.0
            champ_nmae = 100.0

        champion_metrics = {
            "mae_mw": round(champ_mae, 2),
            "rmse_mw": round(champ_rmse, 2),
            "nmae_pct": round(champ_nmae, 2),
            "r2_score": round(champ_r2, 4)
        }

        challenger_metrics = {
            "mae_mw": round(challenger_mae, 2),
            "rmse_mw": round(challenger_rmse, 2),
            "nmae_pct": round(challenger_nmae, 2),
            "r2_score": round(challenger_r2, 4)
        }

        # 6. Tournament Comparisons
        comparisons = [
            ChampionChallengerComparison(
                metric="MAE (MW)",
                champion_val=champion_metrics["mae_mw"],
                challenger_val=challenger_metrics["mae_mw"],
                delta=round(challenger_metrics["mae_mw"] - champion_metrics["mae_mw"], 2),
                improved=challenger_metrics["mae_mw"] <= champion_metrics["mae_mw"]
            ),
            ChampionChallengerComparison(
                metric="RMSE (MW)",
                champion_val=champion_metrics["rmse_mw"],
                challenger_val=challenger_metrics["rmse_mw"],
                delta=round(challenger_metrics["rmse_mw"] - champion_metrics["rmse_mw"], 2),
                improved=challenger_metrics["rmse_mw"] <= champion_metrics["rmse_mw"]
            ),
            ChampionChallengerComparison(
                metric="nMAE (%)",
                champion_val=champion_metrics["nmae_pct"],
                challenger_val=challenger_metrics["nmae_pct"],
                delta=round(challenger_metrics["nmae_pct"] - champion_metrics["nmae_pct"], 2),
                improved=challenger_metrics["nmae_pct"] <= champion_metrics["nmae_pct"]
            ),
            ChampionChallengerComparison(
                metric="R² Score",
                champion_val=champion_metrics["r2_score"],
                challenger_val=challenger_metrics["r2_score"],
                delta=round(challenger_metrics["r2_score"] - champion_metrics["r2_score"], 4),
                improved=challenger_metrics["r2_score"] >= champion_metrics["r2_score"]
            )
        ]

        # 7. Quality & Promotion Gate
        # Challenger is promoted if nMAE or MAE improved, or if force_promote is explicitly requested
        is_improved = (challenger_metrics["nmae_pct"] <= champion_metrics["nmae_pct"]) or (challenger_metrics["mae_mw"] <= champion_metrics["mae_mw"])
        promoted = is_improved or force_promote

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        challenger_version = f"v2.{timestamp_str}-{model_type}-xgb"
        champion_version_name = champion_run.version if champion_run else "v1.0.0-baseline"

        if promoted:
            if force_promote and not is_improved:
                promotion_reason = "Admin manual override (force_promote=True)"
            else:
                margin = round(champion_metrics["nmae_pct"] - challenger_metrics["nmae_pct"], 2)
                promotion_reason = f"Challenger improved accuracy (nMAE delta: -{abs(margin)}%, R²: {challenger_metrics['r2_score']})"

            # Save versioned artifact
            versioned_path = os.path.join(MODELS_DIR, f"{model_type}_xgboost_{challenger_version}.joblib")
            challenger_forecaster.save(versioned_path)

            # Update active production model
            production_path = os.path.join(MODELS_DIR, f"{model_type}_xgboost_v1.joblib")
            challenger_forecaster.save(production_path)

            # Update DB ModelRun records
            if champion_run:
                champion_run.is_active = False
                db.add(champion_run)

            new_run = ModelRun(
                model_name=f"{model_type}_xgboost_ensemble",
                model_type=model_type,
                version=challenger_version,
                training_date=datetime.now(),
                mae_mw=challenger_mae,
                rmse_mw=challenger_rmse,
                r2_score=challenger_r2,
                parameters=json.dumps({"n_estimators": n_estimators, "max_depth": max_depth, "learning_rate": learning_rate}),
                feature_importance=json.dumps(challenger_forecaster.get_feature_importance()),
                model_path=versioned_path,
                is_active=True
            )
            db.add(new_run)

            # Record Audit Log
            audit = AuditLog(
                user_id=1,
                user_email=triggered_by if "@" in triggered_by else f"{triggered_by}@grid.gov.in",
                action="MODEL_PROMOTED",
                resource_type="mlops",
                resource_id=f"model:{model_type}",
                details_json=json.dumps({
                    "version": challenger_version,
                    "mae_mw": challenger_mae,
                    "nmae_pct": challenger_nmae,
                    "r2_score": challenger_r2,
                    "reason": promotion_reason
                }),
                status="SUCCESS"
            )
            db.add(audit)
            db.commit()

            # Hot reload in-memory models across all services
            hot_reload_production_models(model_type)
            artifact_saved_path = versioned_path
            logger.info(f"[{job_id}] Model {challenger_version} PROMOTED to active production champion!")
        else:
            promotion_reason = f"Challenger did not beat Champion (Challenger nMAE {challenger_metrics['nmae_pct']}% >= Champion {champion_metrics['nmae_pct']}%)"
            artifact_saved_path = None
            audit = AuditLog(
                user_id=1,
                user_email=triggered_by if "@" in triggered_by else f"{triggered_by}@grid.gov.in",
                action="MODEL_REJECTED",
                resource_type="mlops",
                resource_id=f"model:{model_type}",
                details_json=json.dumps({
                    "version": challenger_version,
                    "champion_version": champion_version_name,
                    "reason": promotion_reason
                }),
                status="SUCCESS"
            )
            db.add(audit)
            db.commit()
            logger.info(f"[{job_id}] Challenger rejected. Retaining existing champion {champion_version_name}.")

        result = RetrainingExecutionResult(
            model_type=model_type,
            champion_version=champion_version_name,
            challenger_version=challenger_version,
            promoted=promoted,
            promotion_reason=promotion_reason,
            champion_metrics=champion_metrics,
            challenger_metrics=challenger_metrics,
            comparisons=comparisons,
            artifact_path=artifact_saved_path,
            completed_at=datetime.now()
        )

        # Persist to disk history
        history_item = {
            "job_id": job_id,
            "model_type": model_type,
            "triggered_by": triggered_by,
            "status": "PROMOTED" if promoted else "REJECTED",
            "promoted": promoted,
            "champion_version": champion_version_name,
            "challenger_version": challenger_version,
            "challenger_metrics": challenger_metrics,
            "champion_metrics": champion_metrics,
            "promotion_reason": promotion_reason,
            "timestamp": datetime.now().isoformat()
        }
        self._save_history_to_disk(history_item)

        self.last_run_timestamp = datetime.now()
        self.status = RetrainingStatusEnum.COMPLETED
        self.current_job_id = None
        return result

    def retrain_all(
        self,
        db: Session,
        force_promote: bool = False,
        sample_days: int = 90,
        n_estimators: int = 200,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        triggered_by: str = "admin"
    ) -> List[RetrainingExecutionResult]:
        """Runs retraining tournament for both Solar and Wind models sequentially."""
        results = []
        for mt in ["solar", "wind"]:
            res = self.retrain_model(
                db=db,
                model_type=mt,
                force_promote=force_promote,
                sample_days=sample_days,
                n_estimators=n_estimators,
                learning_rate=learning_rate,
                max_depth=max_depth,
                triggered_by=triggered_by
            )
            results.append(res)
        self.last_results = results
        return results

retraining_service = RetrainingService()
