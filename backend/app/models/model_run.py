from sqlalchemy import Column, String, Float, Text, Boolean, DateTime, func
from app.database.base import Base
from app.models.base_model import TimestampMixin

class ModelRun(Base, TimestampMixin):
    __tablename__ = "model_runs"

    model_name = Column(String(100), nullable=False) # e.g. 'solar_xgboost_ensemble', 'wind_xgboost_ensemble'
    model_type = Column(String(20), nullable=False) # 'solar', 'wind'
    version = Column(String(50), unique=True, index=True, nullable=False) # e.g. 'v1.0.0-xgb'
    training_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Performance Metrics
    mae_mw = Column(Float, nullable=True) # Mean Absolute Error in MW
    rmse_mw = Column(Float, nullable=True) # Root Mean Squared Error in MW
    r2_score = Column(Float, nullable=True) # Coefficient of Determination R²

    # Model Configuration & Explainability Artifacts (JSON strings)
    parameters = Column(Text, nullable=True) # Hyperparameters dict as JSON
    feature_importance = Column(Text, nullable=True) # Feature importance dict as JSON
    model_path = Column(String(255), nullable=True) # Relative path to saved .joblib model
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<ModelRun(version='{self.version}', type='{self.model_type}', r2={self.r2_score})>"
