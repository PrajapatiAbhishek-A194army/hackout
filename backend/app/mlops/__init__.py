"""
MLOps Package: Continuous Monitoring, Drift Detection, Champion-Challenger Tournament,
and Model Registry Management.
"""
from app.mlops.drift_detector import DriftDetector, drift_detector
from app.mlops.pipeline import MLOpsPipeline, mlops_pipeline

__all__ = [
    "DriftDetector",
    "drift_detector",
    "MLOpsPipeline",
    "mlops_pipeline",
]
