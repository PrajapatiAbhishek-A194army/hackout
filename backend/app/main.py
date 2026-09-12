from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.api.v1.api import api_router
from app.database.session import engine
from app.database.base import Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("backend.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables or schema are verified
    logger.info("Initializing Renewable Forecasting Platform Backend...")
    try:
        # Create tables if not present (migration ready)
        Base.metadata.create_all(bind=engine)
        logger.info("Database connection and schema tables verified.")
    except Exception as e:
        logger.warning(f"Database schema initialization notice: {e}")
    yield
    # Shutdown
    logger.info("Shutting down Renewable Forecasting Platform Backend...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Production-grade AI-powered renewable generation forecasting platform API. "
        "Transforms Weather + Historical Generation + Plant Metadata into Forecast -> Risk -> Recommendation."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.get("/", tags=["System"])
def root():
    return {
        "service": settings.PROJECT_NAME,
        "status": "online",
        "version": "0.1.0",
        "documentation": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health"
    }

@app.get("/health", tags=["System"])
def root_health():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "0.1.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
