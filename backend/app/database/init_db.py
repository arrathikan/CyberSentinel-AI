"""
CyberAgent AI - Database Initialization Script.

Creates all database tables defined in SQLAlchemy models if they do not already exist.
Safe for repeatable development setup without deleting existing tables or data.

Usage:
    python -m backend.app.database.init_db
"""

import logging
import sys

from sqlalchemy.exc import SQLAlchemyError

from backend.app.database.models import Prediction, SecurityAlert  # noqa: F401
from backend.app.database.session import Base, check_db_health, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def init_db(bind_engine=None) -> bool:
    """
    Initialize all database tables.
    
    Returns True if initialization succeeded, False otherwise.
    """
    target_engine = bind_engine or engine
    logger.info("Initializing database tables on: %s", target_engine.url.render_as_string(hide_password=True))

    try:
        Base.metadata.create_all(bind=target_engine)
        logger.info("Database tables initialized successfully.")
        return True
    except SQLAlchemyError as exc:
        logger.error("Failed to initialize database tables: %s", exc)
        return False


def main():
    health = check_db_health()
    if not health["connected"]:
        logger.warning(
            "Cannot reach database at %s. Ensure PostgreSQL is running. (Error: %s)",
            health["database_url"],
            health["error"],
        )
        logger.info("Attempting table creation anyway in case of transient state...")

    success = init_db()
    if success:
        logger.info("Database initialization completed successfully.")
        sys.exit(0)
    else:
        logger.error("Database initialization failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
