from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config.settings import settings
from app.database.session import get_db
from app.schemas import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)):
    """
    Check system health, database readiness, and operational environment.
    """
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return HealthResponse(
        status="online" if "unhealthy" not in db_status else "degraded",
        service=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        database=db_status,
        version="0.1.0"
    )
