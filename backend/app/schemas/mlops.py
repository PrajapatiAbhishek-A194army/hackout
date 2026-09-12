from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class ModelType(str, Enum):
    SOLAR = "solar"
    WIND = "wind"

class DriftStatus(str, Enum):
    STABLE = "stable"
    MODERATE_DRIFT = "moderate_drift"
    SIGNIFICANT_DRIFT = "significant_drift"

class FeatureDriftMetric(BaseModel):
    feature_name: str
    psi_score: float = Field(..., description="Population Stability Index")
    ks_statistic: float = Field(..., description="Kolmogorov-Smirnov test statistic")
    ks_p_value: float = Field(..., description="Two-sample KS test p-value")
    drift_status: DriftStatus
    baseline_mean: float
    current_mean: float
    baseline_std: float
    current_std: float

class ConceptDriftMetric(BaseModel):
    baseline_rmse_mw: float
    current_rmse_mw: float
    degradation_ratio: float = Field(..., description="current_rmse / baseline_rmse")
    mae_mw: float
    mape_pct: float
    performance_drift_detected: bool

class DriftAnalysisResponse(BaseModel):
    model_type: str
    analyzed_at: datetime
    sample_size_baseline: int
    sample_size_current: int
    overall_drift_status: DriftStatus
    recommend_retraining: bool
    concept_drift: ConceptDriftMetric
    feature_drift: List[FeatureDriftMetric]

class ModelRetrainRequest(BaseModel):
    model_type: ModelType
    force_promote: bool = Field(default=False, description="Promote challenger even if improvement margin is minimal")
    n_estimators: Optional[int] = Field(default=150, ge=50, le=500)
    learning_rate: Optional[float] = Field(default=0.05, ge=0.01, le=0.3)
    max_depth: Optional[int] = Field(default=6, ge=3, le=12)

class ChampionChallengerComparison(BaseModel):
    metric: str
    champion_val: float
    challenger_val: float
    delta: float
    improved: bool

class ModelRetrainResponse(BaseModel):
    model_type: str
    champion_version: str
    challenger_version: str
    promoted_to_champion: bool
    promotion_reason: str
    metrics_comparison: List[ChampionChallengerComparison]
    challenger_metrics: Dict[str, float]
    completed_at: datetime

class ModelRunSummary(BaseModel):
    id: int
    model_name: str
    model_type: str
    version: str
    training_date: datetime
    mae_mw: Optional[float] = None
    rmse_mw: Optional[float] = None
    r2_score: Optional[float] = None
    is_active: bool
    model_path: Optional[str] = None

    class Config:
        from_attributes = True

class ModelRollbackRequest(BaseModel):
    model_type: ModelType
    target_version: str = Field(..., description="Model version string to rollback to, e.g. 'v1.0.0-solar-xgb'")
