from fastapi import APIRouter
from app.api.v1.endpoints import (
    health, plants, regions, weather, forecasts, alerts,
    pipeline_endpoints, features_endpoints, solar_endpoints, wind_endpoints,
    aggregation_endpoints, explainability_endpoints, storage_endpoints,
    report_endpoints, mlops_endpoints, auth_endpoints, ws_endpoints,
    retraining_endpoints
)

api_router = APIRouter()

# Register core endpoint routers
api_router.include_router(health.router, tags=["Health & Status"])
api_router.include_router(auth_endpoints.router, prefix="/auth", tags=["Authentication & Security"])
api_router.include_router(retraining_endpoints.router, prefix="/retrain", tags=["Model Retraining & Drift Re-Optimization"])
api_router.include_router(ws_endpoints.router, tags=["Real-Time WebSockets & Telemetry"])
api_router.include_router(plants.router, prefix="/plants", tags=["Renewable Plants"])
api_router.include_router(regions.router, prefix="/regions", tags=["Grid Regions & States"])
api_router.include_router(weather.router, prefix="/weather", tags=["Weather Telemetry"])
api_router.include_router(forecasts.router, prefix="/forecast", tags=["Generation Forecasts"])
api_router.include_router(aggregation_endpoints.router, prefix="/aggregate", tags=["Hierarchical Aggregation Engine"])
api_router.include_router(explainability_endpoints.router, prefix="/explain", tags=["Explainability Engine (SHAP & Drivers)"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Grid Alerts & Recommendations"])
api_router.include_router(storage_endpoints.router, prefix="/storage", tags=["Battery Energy Storage (BESS)"])
api_router.include_router(report_endpoints.router, prefix="/reports", tags=["Reporting & Compliance Exports"])
api_router.include_router(mlops_endpoints.router, prefix="/mlops", tags=["MLOps, Retraining & Drift Monitoring"])
api_router.include_router(pipeline_endpoints.router, prefix="/pipeline", tags=["Data Pipeline & Ingestion"])

api_router.include_router(features_endpoints.router, prefix="/features", tags=["Feature Engineering"])
api_router.include_router(solar_endpoints.router, prefix="/solar", tags=["Solar Forecasting (XGBoost)"])
api_router.include_router(wind_endpoints.router, prefix="/wind", tags=["Wind Forecasting (XGBoost)"])







