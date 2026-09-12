import logging
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd
from scipy import stats

from app.schemas.mlops import DriftStatus, FeatureDriftMetric, ConceptDriftMetric, DriftAnalysisResponse

logger = logging.getLogger("backend.mlops.drift")

class DriftDetector:
    """
    Production Statistical Drift & Data Integrity Engine.
    Implements:
      1. Population Stability Index (PSI)
      2. Two-Sample Kolmogorov-Smirnov (KS) Test
      3. Concept Drift & Rolling Error Degradation Tracking
    """

    @staticmethod
    def calculate_psi(
        baseline: np.ndarray,
        current: np.ndarray,
        num_bins: int = 10,
        epsilon: float = 1e-4
    ) -> float:
        """
        Calculates Population Stability Index (PSI) between baseline and current data distributions.
          PSI < 0.10 -> No significant change (Stable)
          0.10 <= PSI < 0.25 -> Moderate drift
          PSI >= 0.25 -> Significant distribution shift (Retraining recommended)
        """
        baseline = baseline[~np.isnan(baseline)]
        current = current[~np.isnan(current)]

        if len(baseline) < 10 or len(current) < 10:
            return 0.0

        # Create quantile bins based on the reference baseline
        quantiles = np.linspace(0, 100, num_bins + 1)
        bin_edges = np.percentile(baseline, quantiles)
        bin_edges[0] -= 1e-5
        bin_edges[-1] += 1e-5
        bin_edges = np.unique(bin_edges)

        if len(bin_edges) < 3:
            # Low variance or degenerate constant distribution
            diff = abs(float(np.mean(current) - np.mean(baseline)))
            std = float(np.std(baseline)) + 1e-6
            return round(min(1.0, diff / std * 0.1), 4)

        # Count frequencies in each bin
        expected_counts, _ = np.histogram(baseline, bins=bin_edges)
        actual_counts, _ = np.histogram(current, bins=bin_edges)

        # Convert to proportions with smoothing epsilon
        expected_pct = (expected_counts / len(baseline)) + epsilon
        actual_pct = (actual_counts / len(current)) + epsilon

        expected_pct /= np.sum(expected_pct)
        actual_pct /= np.sum(actual_pct)

        # PSI formula: Sum( (Actual - Expected) * ln(Actual / Expected) )
        psi_value = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
        return round(float(max(0.0, psi_value)), 4)

    @staticmethod
    def calculate_ks_test(
        baseline: np.ndarray,
        current: np.ndarray
    ) -> Tuple[float, float]:
        """
        Executes two-sample Kolmogorov-Smirnov test to detect non-parametric distribution shifts.
        Returns: (ks_statistic, p_value)
        """
        baseline = baseline[~np.isnan(baseline)]
        current = current[~np.isnan(current)]

        if len(baseline) < 5 or len(current) < 5:
            return 0.0, 1.0

        stat, p_val = stats.ks_2samp(baseline, current)
        return round(float(stat), 4), round(float(p_val), 6)

    @classmethod
    def evaluate_feature_drift(
        cls,
        baseline_df: pd.DataFrame,
        current_df: pd.DataFrame,
        feature_names: List[str]
    ) -> List[FeatureDriftMetric]:
        """
        Evaluates PSI and KS statistics for every feature in the dataset.
        """
        metrics = []
        for feat in feature_names:
            if feat not in baseline_df.columns or feat not in current_df.columns:
                continue

            base_arr = baseline_df[feat].to_numpy(dtype=float)
            curr_arr = current_df[feat].to_numpy(dtype=float)

            psi = cls.calculate_psi(base_arr, curr_arr)
            ks_stat, ks_pval = cls.calculate_ks_test(base_arr, curr_arr)

            # Determine drift status
            if psi >= 0.25 or (psi >= 0.15 and ks_pval < 0.001):
                status = DriftStatus.SIGNIFICANT_DRIFT
            elif psi >= 0.10 or ks_pval < 0.05:
                status = DriftStatus.MODERATE_DRIFT
            else:
                status = DriftStatus.STABLE

            metrics.append(
                FeatureDriftMetric(
                    feature_name=feat,
                    psi_score=psi,
                    ks_statistic=ks_stat,
                    ks_p_value=ks_pval,
                    drift_status=status,
                    baseline_mean=round(float(np.nanmean(base_arr)), 2),
                    current_mean=round(float(np.nanmean(curr_arr)), 2),
                    baseline_std=round(float(np.nanstd(base_arr)), 2),
                    current_std=round(float(np.nanstd(curr_arr)), 2)
                )
            )

        return metrics

    @classmethod
    def evaluate_concept_drift(
        cls,
        actual_mw: np.ndarray,
        predicted_mw: np.ndarray,
        baseline_rmse_mw: float
    ) -> ConceptDriftMetric:
        """
        Evaluates prediction error degradation against the baseline training validation error.
        """
        actual_mw = np.array(actual_mw, dtype=float)
        predicted_mw = np.array(predicted_mw, dtype=float)

        errors = actual_mw - predicted_mw
        current_rmse = float(np.sqrt(np.mean(errors ** 2)))
        mae = float(np.mean(np.abs(errors)))

        # Percentage error avoiding division by near-zero values
        denom = np.maximum(actual_mw, 5.0)
        mape = float(np.mean(np.abs(errors) / denom) * 100.0)

        degradation_ratio = (current_rmse / baseline_rmse_mw) if baseline_rmse_mw > 0 else 1.0

        # Performance drift triggers if error degraded by >25% or MAPE exceeds 18%
        drift_detected = (degradation_ratio >= 1.25) or (mape >= 18.0)

        return ConceptDriftMetric(
            baseline_rmse_mw=round(baseline_rmse_mw, 2),
            current_rmse_mw=round(current_rmse, 2),
            degradation_ratio=round(degradation_ratio, 3),
            mae_mw=round(mae, 2),
            mape_pct=round(mape, 2),
            performance_drift_detected=drift_detected
        )

    @classmethod
    def analyze_model_drift(
        cls,
        model_type: str,
        baseline_features_df: pd.DataFrame,
        current_features_df: pd.DataFrame,
        actual_mw: np.ndarray,
        predicted_mw: np.ndarray,
        baseline_rmse_mw: float,
        feature_names: List[str]
    ) -> Dict[str, Any]:
        """
        Full end-to-end drift audit.
        """
        feature_metrics = cls.evaluate_feature_drift(baseline_features_df, current_features_df, feature_names)
        concept_metric = cls.evaluate_concept_drift(actual_mw, predicted_mw, baseline_rmse_mw)

        # Determine overall drift status
        sig_count = sum(1 for f in feature_metrics if f.drift_status == DriftStatus.SIGNIFICANT_DRIFT)
        mod_count = sum(1 for f in feature_metrics if f.drift_status == DriftStatus.MODERATE_DRIFT)

        if concept_metric.performance_drift_detected or sig_count >= 2:
            overall = DriftStatus.SIGNIFICANT_DRIFT
            recommend_retrain = True
        elif sig_count >= 1 or mod_count >= 2:
            overall = DriftStatus.MODERATE_DRIFT
            recommend_retrain = False
        else:
            overall = DriftStatus.STABLE
            recommend_retrain = False

        return {
            "model_type": model_type,
            "sample_size_baseline": len(baseline_features_df),
            "sample_size_current": len(current_features_df),
            "overall_drift_status": overall,
            "recommend_retraining": recommend_retrain,
            "concept_drift": concept_metric,
            "feature_drift": feature_metrics
        }

drift_detector = DriftDetector()
