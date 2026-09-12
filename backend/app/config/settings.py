from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

# Calculate workspace directories
# settings.py is in backend/app/config/
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(CONFIG_DIR)
BACKEND_DIR = os.path.dirname(APP_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)

# Priority: root .env first, then backend .env
env_files = [
    os.path.join(ROOT_DIR, ".env"),
    os.path.join(BACKEND_DIR, ".env")
]

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Renewable Generation Forecasting Platform"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    
    # Database configuration
    # Defaults to PostgreSQL, falls back to SQLite if PostgreSQL is unavailable in local dev
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/renewable_db"
    SQL_ECHO: bool = False

    # Security
    JWT_SECRET: str = "default_development_secret_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # External APIs
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1"
    NASA_POWER_BASE_URL: str = "https://power.larc.nasa.gov/api/temporal"

    # CORS configuration
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(
        env_file=env_files,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
