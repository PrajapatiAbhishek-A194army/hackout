import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.config.settings import settings

logger = logging.getLogger("backend.database")

def get_engine():
    database_url = settings.DATABASE_URL
    
    # Try creating engine with primary URL
    try:
        connect_args = {}
        if database_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
            
        engine = create_engine(
            database_url,
            echo=settings.SQL_ECHO,
            connect_args=connect_args,
            pool_pre_ping=True
        )
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Database engine initialized successfully with URL: {database_url.split('@')[-1]}")
        return engine
    except Exception as exc:
        logger.warning(
            f"Failed to connect to primary database ({database_url.split('@')[-1]}): {exc}. "
            f"Falling back to local SQLite database for uninterrupted local development."
        )
        sqlite_url = "sqlite:///./renewable_dev.db"
        engine = create_engine(
            sqlite_url,
            echo=settings.SQL_ECHO,
            connect_args={"check_same_thread": False}
        )
        return engine

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a SQLAlchemy database session per request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
