"""
CyberAgent AI - Database Integration & Unit Tests.

Covers:
1. Database engine and connection configuration.
2. Prediction model creation and persistence.
3. Security alert model creation and persistence.
4. Foreign-key relationships and cascade behavior.
5. Transaction rollback on exception.
6. Environment variable handling and URL normalization.
7. Database initialization (idempotent init_db).
8. Database health verification.
9. FastAPI endpoint compatibility with database health check.
"""

import os
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.app.database.session import (
    Base,
    create_db_engine,
    get_database_url,
    check_db_health,
)
from backend.app.database.models import Prediction, SecurityAlert
from backend.app.database.init_db import init_db
from backend.app.main import app


@pytest.fixture(scope="module")
def memory_db_engine():
    """Isolated in-memory SQLite database engine for testing."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Enable foreign keys for SQLite
    with test_engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(memory_db_engine):
    """Isolated session per test function."""
    connection = memory_db_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------
# 1. Database engine and connection configuration
# ---------------------------------------------------------
def test_create_db_engine():
    """Verify engine creation and configuration."""
    test_engine = create_db_engine("sqlite:///:memory:")
    assert test_engine is not None
    assert test_engine.dialect.name == "sqlite"



# ---------------------------------------------------------
# 2. Prediction model creation and persistence
# ---------------------------------------------------------
def test_prediction_creation_and_persistence(db_session: Session):
    """Verify Prediction ORM creation, defaults, and persistence."""
    pred = Prediction(
        model_name="XGBoost",
        prediction=1,
        attack_score=0.985,
    )
    db_session.add(pred)
    db_session.flush()

    assert pred.id is not None
    assert pred.model_name == "XGBoost"
    assert pred.prediction == 1
    assert pytest.approx(pred.attack_score, 0.001) == 0.985
    assert pred.created_at is not None

    # Query back
    stmt = select(Prediction).where(Prediction.id == pred.id)
    retrieved = db_session.scalar(stmt)
    assert retrieved is not None
    assert retrieved.model_name == "XGBoost"
    assert retrieved.to_dict()["prediction"] == 1


# ---------------------------------------------------------
# 3. Security alert model creation and persistence
# ---------------------------------------------------------
def test_security_alert_creation_and_persistence(db_session: Session):
    """Verify SecurityAlert model creation and default status."""
    pred = Prediction(
        model_name="RandomForest",
        prediction=1,
        attack_score=0.88,
    )
    db_session.add(pred)
    db_session.flush()

    alert = SecurityAlert(
        prediction_id=pred.id,
        severity="high",
    )
    db_session.add(alert)
    db_session.flush()

    assert alert.id is not None
    assert alert.prediction_id == pred.id
    assert alert.severity == "high"
    assert alert.status == "open"  # Default status
    assert alert.created_at is not None
    assert "id" in alert.to_dict()


# ---------------------------------------------------------
# 4. Foreign-key relationships & cascading delete
# ---------------------------------------------------------
def test_foreign_key_relationship_and_cascade(db_session: Session):
    """Verify bidirectional relationship and cascading delete."""
    pred = Prediction(
        model_name="XGBoost",
        prediction=1,
        attack_score=0.99,
    )
    alert1 = SecurityAlert(severity="high", status="open")
    alert2 = SecurityAlert(severity="critical", status="investigating")
    pred.alerts.append(alert1)
    pred.alerts.append(alert2)

    db_session.add(pred)
    db_session.flush()

    pred_id = pred.id
    assert len(pred.alerts) == 2
    assert alert1.prediction_id == pred_id
    assert alert2.prediction == pred

    # Verify query via relationship
    retrieved_pred = db_session.get(Prediction, pred_id)
    assert len(retrieved_pred.alerts) == 2

    # Verify cascade delete
    db_session.delete(retrieved_pred)
    db_session.flush()

    # Alerts should be deleted when parent prediction is deleted
    stmt = select(SecurityAlert).where(SecurityAlert.prediction_id == pred_id)
    remaining_alerts = db_session.scalars(stmt).all()
    assert len(remaining_alerts) == 0


# ---------------------------------------------------------
# 5. Transaction rollback behavior
# ---------------------------------------------------------
def test_transaction_rollback_behavior(memory_db_engine):
    """Verify session rollback on unhandled error leaves database intact."""
    session_factory = sessionmaker(bind=memory_db_engine)
    session = session_factory()

    try:
        pred = Prediction(
            model_name="TestModel",
            prediction=0,
            attack_score=0.1,
        )
        session.add(pred)
        session.flush()

        # Simulate exception
        raise ValueError("Simulated failure during transaction")
    except ValueError:
        session.rollback()
    finally:
        session.close()

    # Verify nothing was committed
    with session_factory() as verify_session:
        stmt = select(Prediction).where(Prediction.model_name == "TestModel")
        found = verify_session.scalars(stmt).all()
        assert len(found) == 0


# ---------------------------------------------------------
# 6. Environment variable handling and normalization
# ---------------------------------------------------------
def test_database_url_env_handling(monkeypatch):
    """Verify URL retrieval and psycopg3 dialect normalization."""
    # Test standard postgresql:// normalization
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:pass@host:5432/mydb"
    )
    normalized = get_database_url()
    assert normalized == "postgresql+psycopg://user:pass@host:5432/mydb"

    # Test postgres:// normalization
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgres://user:pass@host:5432/mydb"
    )
    assert get_database_url() == "postgresql+psycopg://user:pass@host:5432/mydb"

    # Test already normalized
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:pass@host:5432/mydb"
    )
    assert get_database_url() == "postgresql+psycopg://user:pass@host:5432/mydb"

    # Test sqlite unchanged
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    assert get_database_url() == "sqlite:///test.db"


# ---------------------------------------------------------
# 7. Database initialization (idempotent init_db)
# ---------------------------------------------------------
def test_init_db_idempotent():
    """Verify init_db creates tables and can run repeatedly safely."""
    test_engine = create_engine("sqlite:///:memory:")
    assert init_db(test_engine) is True
    # Calling a second time should succeed without error
    assert init_db(test_engine) is True


# ---------------------------------------------------------
# 8. Database health verification
# ---------------------------------------------------------
def test_check_db_health():
    """Verify health check utility reports healthy and unhealthy states."""
    healthy_engine = create_engine("sqlite:///:memory:")
    health = check_db_health(healthy_engine)
    assert health["status"] == "healthy"
    assert health["connected"] is True
    assert health["error"] is None

    # Test unhealthy engine with invalid path/driver
    broken_engine = create_engine("sqlite:///nonexistent_dir/impossible/db.sqlite")
    unhealthy = check_db_health(broken_engine)
    assert unhealthy["status"] == "unhealthy"
    assert unhealthy["connected"] is False
    assert unhealthy["error"] is not None


# ---------------------------------------------------------
# 9. FastAPI health endpoint includes database status
# ---------------------------------------------------------
def test_fastapi_health_endpoint():
    """Verify GET /health returns existing fields and database status."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["model_loaded"] is True
        assert "database" in data
        assert "connected" in data["database"]


# ---------------------------------------------------------
# 10. Alembic migration verification
# ---------------------------------------------------------
def test_alembic_migrations_offline(capsys):
    """Verify Alembic can parse models and generate migration SQL offline."""
    from alembic.config import Config
    from alembic import command
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    alembic_cfg = Config(str(root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(root / "alembic"))

    # Run offline SQL generation without raising any exceptions
    command.upgrade(alembic_cfg, "head", sql=True)
    captured = capsys.readouterr()
    assert "CREATE TABLE predictions" in captured.out
    assert "CREATE TABLE security_alerts" in captured.out


