"""
CyberAgent AI - Database Module.

Exposes ORM models, session dependencies, and database health utilities.
"""

from backend.app.database.init_db import init_db
from backend.app.database.models import Prediction, SecurityAlert
from backend.app.database.session import (
    Base,
    SessionLocal,
    check_db_health,
    create_db_engine,
    engine,
    get_database_url,
    get_db,
)

__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "create_db_engine",
    "get_database_url",
    "get_db",
    "check_db_health",
    "Prediction",
    "SecurityAlert",
    "init_db",
]
