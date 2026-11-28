"""
CyberAgent AI - Database Session and Connection Management.

Provides:
- SQLAlchemy 2.x engine configured from environment variables.
- Declarative Base for ORM models.
- SessionLocal factory.
- get_db: FastAPI dependency for yielding isolated sessions with automatic rollback on error.
- check_db_health: Diagnostics and connectivity check function.
"""

import logging
import os
from typing import Any, Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Ensure environment variables are loaded
load_dotenv()

logger = logging.getLogger(__name__)

# Default to development PostgreSQL URL on port 5433
DEFAULT_DB_URL = "postgresql://cyberagent:local_dev_password@127.0.0.1:5433/cyberagent_db"


def get_database_url() -> str:
    """
    Retrieve and normalize the DATABASE_URL.
    
    If the URL starts with postgresql:// and uses psycopg 3,
    normalize to postgresql+psycopg:// for SQLAlchemy.
    """
    url = os.getenv("DATABASE_URL", DEFAULT_DB_URL).strip()
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = get_database_url()


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def create_db_engine(url: str | None = None):
    """Create a configured SQLAlchemy engine."""
    db_url = url or get_database_url()
    is_sqlite = db_url.startswith("sqlite")

    engine_kwargs: dict[str, Any] = {
        "pool_pre_ping": True,
        "echo": os.getenv("DEBUG", "false").lower() in ("true", "1", "yes"),
    }

    if not is_sqlite:
        engine_kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "5"))
        engine_kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "10"))
        engine_kwargs["pool_timeout"] = float(os.getenv("DB_POOL_TIMEOUT", "30.0"))

    return create_engine(db_url, **engine_kwargs)


engine = create_db_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a SQLAlchemy database session.
    
    Rolls back transaction on any unhandled exception, and always
    closes the session upon completion.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_health(test_engine=None, timeout: float = 3.0) -> dict[str, Any]:
    """
    Verify database connectivity.
    
    Returns a dictionary with status, driver, and error details if unavailable.
    """
    target_engine = test_engine or engine
    # Connection options and driver exceptions can also contain private values.
    safe_url = target_engine.url.set(query={}).render_as_string(hide_password=True)

    try:
        with target_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "connected": True,
            "database_url": safe_url,
            "error": None,
        }
    except Exception as exc:
        logger.warning("Database connectivity check failed (%s)", type(exc).__name__)
        return {
            "status": "unhealthy",
            "connected": False,
            "database_url": safe_url,
            "error": "Database connection check failed",
        }
