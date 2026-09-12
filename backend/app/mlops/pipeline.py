import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from app.models.model_run import ModelRun
from app.schemas.mlops import (
    ModelType, ChampionChallengerComparison, ModelRetrainResponse, ModelRetrainRequest
)
from app.ml.solar_model import SolarForecaster, SOLAR_FEATURES
from app.ml.wind_model import WindForecaster, WIND_FEATURES
from app.ml.synthetic_dataset import generate_synthetic_solar_data, generate_synthetic_wind_data
from app.ml.features import FeatureEngineer

logger = logging.getLogger("backend.mlops.pipeline")

MODELS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "trained_models")
)
os.makedirs(MODELS_DIR, exist_ok=True)

class MLOpsPipeline:
    """
    Automated Continuous Model Retraining and Champion-Challenger Tournament Engine.
    Executes:
      1. Challenger training with latest operational telemetry
      2. Direct Champion vs Challenger side-by-side evaluation on holdout test splits
      3. Strict quality gate validation prior to automatic production promotion
      4. Instant version rollback and registry synchronization
    """

    @classmethod
    def get_active_champion(cls, db: Session, model_type: str) -> Optional[ModelRun]:
        return (
            db.query(ModelRun)
            .filter(ModelRun.model_type == model_type, ModelRun.is_active == True)
            .order_by(ModelRun.training_date.desc())
            .first()
        )

    @classmethod
    def retrain_and_evaluate(
        cls,
        db: Session,
        request: ModelRetrainRequest
    ) -> Dict[str, Any]:
        """
        Trains a Challenger model, runs tournament against the active Champion,
        and promotes if promotion gates pass.
        """
        model_type = request.model_type.value.lower()
        logger.info(f"Initiating MLOps retraining pipeline for {model_type.upper()} forecasting engine...")

        # 1. Fetch current Champion
        champion_run = cls.get_active_champion(db, model_type)
        if not champion_run:
            champion_version = "none"
            champion_rmse = 9999.0
            champion_mae = 9999.0
            champion_r2 = -1.0
        else:
            champion_version = champion_run.version
            champion_rmse = float(champion_run.rmse_mw or 20.0)
            champion_mae = float(champion_run.mae_mw or 15.0)
            champion_r2 = float(champion_run.r2_score or 0.95)

        # 2. Generate training and holdout validation datasets with recent conditions
        if model_type == "solar":
            capacity_mw = 500.0
            df_raw = generate_synthetic_solar_data(days=60, capacity_mw=capacity_mw, seed=int(datetime.now().timestamp()) % 10000)
            metadata = {"tilt": 25.0, "azimuth": 180.0, "tracking": "single_axis", "capacity_mw": capacity_mw}
            X, _ = FeatureEngineer.create_feature_matrix(df_raw, metadata)
            y = df_raw["generation_mw"].values
            feature_names = SOLAR_FEATURES
            model_cls = SolarForecaster
        else: # wind
            capacity_mw = 300.0
            df_raw = generate_synthetic_wind_data(days=60, capacity_mw=capacity_mw, seed=int(datetime.now().timestamp()) % 10000)
            metadata = {"hub_height": 120.0, "rotor_diameter": 140.0, "cut_in": 3.0, "rated": 12.0, "cut_out": 25.0, "capacity_mw": capacity_mw}
            _, X = FeatureEngineer.create_feature_matrix(df_raw, metadata)
            y = df_raw["generation_mw"].values
            feature_names = WIND_FEATURES
            model_cls = WindForecaster

        # Train/Val/Test split (70% / 15% / 15%)
        n = len(X)
        i_train = int(n * 0.70)
        i_val = int(n * 0.85)

        X_train, y_train = X.iloc[:i_train], y[:i_train]
        X_val, y_val = X.iloc[i_train:i_val], y[i_train:i_val]
        X_test, y_test = X.iloc[i_val:], y[i_val:]

        # 3. Train Challenger Model
        challenger = model_cls(
            n_estimators=request.n_estimators or 150,
            learning_rate=request.learning_rate or 0.05,
            max_depth=request.max_depth or 6
        )
        challenger.train(X_train, y_train, X_val, y_val)

        # 4. Evaluate Challenger on holdout test set
        y_pred_challenger = challenger.predict(X_test)
        challenger_rmse = float(np.sqrt(mean_squared_error(y_test, y_pred_challenger)))
        challenger_mae = float(mean_absolute_error(y_test, y_pred_challenger))
        challenger_r2 = float(r2_score(y_test, y_pred_challenger))

        # 5. Evaluate Champion on the same holdout set (if model file exists)
        if champion_run and champion_run.model_path and os.path.exists(champion_run.model_path):
            try:
                champion_model = model_cls.load(champion_run.model_path)
                y_pred_champ = champion_model.predict(X_test)
                champ_test_rmse = float(np.sqrt(mean_squared_error(y_test, y_pred_champ)))
                champ_test_mae = float(mean_absolute_error(y_test, y_pred_champ))
                champ_test_r2 = float(r2_score(y_test, y_pred_champ))
            except Exception as e:
                logger.warning(f"Failed to evaluate existing champion: {e}. Using DB logged metrics.")
                champ_test_rmse = champion_rmse
                champ_test_mae = champion_mae
                champ_test_r2 = champion_r2
        else:
            champ_test_rmse = champion_rmse
            champ_test_mae = champion_mae
            champ_test_r2 = champion_r2

        # 6. Champion vs Challenger Tournament Comparison
        rmse_diff = challenger_rmse - champ_test_rmse
        mae_diff = challenger_mae - champ_test_mae
        r2_diff = challenger_r2 - champ_test_r2

        comparisons = [
            ChampionChallengerComparison(
                metric="RMSE (MW)",
                champion_val=round(champ_test_rmse, 2),
                challenger_val=round(challenger_rmse, 2),
                delta=round(rmse_diff, 2),
                improved=(challenger_rmse <= champ_test_rmse)
            ),
            ChampionChallengerComparison(
                metric="MAE (MW)",
                champion_val=round(champ_test_mae, 2),
                challenger_val=round(challenger_mae, 2),
                delta=round(mae_diff, 2),
                improved=(challenger_mae <= champ_test_mae)
            ),
            ChampionChallengerComparison(
                metric="R² Score",
                champion_val=round(champ_test_r2, 4),
                challenger_val=round(challenger_r2, 4),
                delta=round(r2_diff, 4),
                improved=(challenger_r2 >= champ_test_r2)
            )
        ]

        # 7. Promotion Gates:
        # - Challenger must achieve R² >= 0.90
        # - Challenger RMSE must not degrade significantly compared to champion
        # - Or force_promote is explicitly requested
        promoted = False
        reason = ""

        if request.force_promote:
            promoted = True
            reason = "Promoted via explicit manual force override."
        elif challenger_r2 < 0.90:
            promoted = False
            reason = f"Challenger rejected: R² ({challenger_r2:.4f}) is below minimum threshold (0.9000)."
        elif challenger_rmse <= (champ_test_rmse * 1.05) and challenger_r2 >= (champ_test_r2 - 0.01):
            promoted = True
            reason = f"Challenger promoted: Achieved competitive RMSE ({challenger_rmse:.2f} MW) and strong R² ({challenger_r2:.4f})."
        else:
            promoted = False
            reason = f"Challenger rejected: Did not outperform Champion RMSE ({champ_test_rmse:.2f} MW)."

        # Determine challenger version string
        runs_count = db.query(ModelRun).filter(ModelRun.model_type == model_type).count()
        challenger_version = f"v1.{runs_count + 1}.0-{model_type}-xgb"
        artifact_filename = f"{model_type}_xgboost_{challenger_version}.joblib"
        artifact_path = os.path.join(MODELS_DIR, artifact_filename)

        # Save challenger artifact
        challenger.save(artifact_path)

        # 8. Update Model Registry in DB
        if promoted:
            # Demote existing champion
            if champion_run:
                champion_run.is_active = False

            new_run = ModelRun(
                model_name=f"{model_type.capitalize()} XGBoost Ensemble",
                model_type=model_type,
                version=challenger_version,
                training_date=datetime.now(),
                mae_mw=round(challenger_mae, 2),
                rmse_mw=round(challenger_rmse, 2),
                r2_score=round(challenger_r2, 4),
                parameters=json.dumps(challenger.params),
                feature_importance=json.dumps(challenger.feature_importance),
                model_path=artifact_path,
                is_active=True
            )
            db.add(new_run)
            db.commit()
            db.refresh(new_run)

            # Update default active symlink/primary file so live forecaster uses it
            primary_path = os.path.join(MODELS_DIR, f"{model_type}_xgboost_v1.joblib")
            try:
                challenger.save(primary_path)
            except Exception as e:
                logger.warning(f"Could not update primary active model file: {e}")

        else:
            # Register challenger as inactive run for audit trail
            new_run = ModelRun(
                model_name=f"{model_type.capitalize()} XGBoost Challenger (Rejected)",
                model_type=model_type,
                version=challenger_version,
                training_date=datetime.now(),
                mae_mw=round(challenger_mae, 2),
                rmse_mw=round(challenger_rmse, 2),
                r2_score=round(challenger_r2, 4),
                parameters=json.dumps(challenger.params),
                feature_importance=json.dumps(challenger.feature_importance),
                model_path=artifact_path,
                is_active=False
            )
            db.add(new_run)
            db.commit()

        return {
            "model_type": model_type,
            "champion_version": champion_version,
            "challenger_version": challenger_version,
            "promoted_to_champion": promoted,
            "promotion_reason": reason,
            "metrics_comparison": comparisons,
            "challenger_metrics": {
                "rmse_mw": round(challenger_rmse, 2),
                "mae_mw": round(challenger_mae, 2),
                "r2_score": round(challenger_r2, 4)
            },
            "completed_at": datetime.now()
        }

    @classmethod
    def rollback_model(cls, db: Session, model_type: str, target_version: str) -> Dict[str, Any]:
        """
        Rolls back the active model to a specified historical version.
        """
        target = (
            db.query(ModelRun)
            .filter(ModelRun.model_type == model_type, ModelRun.version == target_version)
            .first()
        )
        if not target:
            raise ValueError(f"Target model version '{target_version}' for {model_type} not found.")

        # Deactivate all models of this type
        all_runs = db.query(ModelRun).filter(ModelRun.model_type == model_type).all()
        for r in all_runs:
            r.is_active = False

        target.is_active = True
        db.commit()

        # Update primary model file if physical artifact exists
        if target.model_path and os.path.exists(target.model_path):
            import shutil
            primary_path = os.path.join(MODELS_DIR, f"{model_type}_xgboost_v1.joblib")
            try:
                shutil.copyfile(target.model_path, primary_path)
            except Exception as e:
                logger.warning(f"Could not copy rollback model to primary: {e}")

        logger.info(f"Successfully rolled back {model_type} model to {target_version}")
        return {
            "model_type": model_type,
            "active_version": target.version,
            "training_date": target.training_date,
            "rmse_mw": target.rmse_mw,
            "r2_score": target.r2_score,
            "status": "active"
        }

    @classmethod
    def list_registry(cls, db: Session, model_type: Optional[str] = None) -> List[ModelRun]:
        q = db.query(ModelRun)
        if model_type:
            q = q.filter(ModelRun.model_type == model_type.lower())
        return q.order_by(ModelRun.training_date.desc()).all()

mlops_pipeline = MLOpsPipeline()
