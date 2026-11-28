import os

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.severity import SeverityPolicy
from backend.app.database.models import Prediction, SecurityAlert
from backend.app.database.session import Base, get_db
from backend.app.main import app


@pytest.fixture
def client_and_engine(tmp_path, monkeypatch):
    # The optional PostgreSQL URL must point to a migrated disposable database.
    postgres_url = os.getenv("STEP9C_TEST_DATABASE_URL")
    engine = create_engine(postgres_url or f"sqlite:///{tmp_path / 'alerts.db'}")
    if postgres_url is None:
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(engine)

    def get_test_db():
        with Session(engine) as session:
            yield session

    class Predictor:
        model_version = "2026.1"

        def predict(self, values):
            score = values["score"]
            prediction = int(score >= 0.5)
            return dict(
                model="XGBoost", prediction=prediction,
                label="Attack" if prediction else "Benign",
                attack_score=score, threshold=0.5,
            )

    monkeypatch.setitem(app.dependency_overrides, get_db, get_test_db)
    monkeypatch.setattr("backend.app.main.CyberattackPredictor", Predictor)
    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        engine.dispose()


def submit(client, score):
    return client.post("/api/v1/predict", json={"features": {"score": score}})


def test_prediction_and_alert_lifecycle(client_and_engine):
    client, engine = client_and_engine
    assert submit(client, True).status_code == 422
    benign = submit(client, 0.1).json()
    assert benign["alert_id"] is None
    attack = submit(client, 0.95).json()
    assert attack["label"] == "Attack"
    url = f"/api/v1/alerts/{attack['alert_id']}"

    history = client.get("/api/v1/predictions", params={"limit": 1}).json()
    assert history["items"][0]["id"] == attack["prediction_id"]
    assert history["items"][0]["label"] == "Attack"
    assert history["items"][0]["model_version"] == "2026.1"
    older = client.get("/api/v1/predictions", params={"limit": 1, "offset": 1}).json()
    assert older["items"][0]["id"] == benign["prediction_id"]
    assert older["items"][0]["label"] == "Benign"
    page = client.get(
        "/api/v1/alerts", params={"status": "open", "severity": "critical", "limit": 1},
    ).json()
    assert page["items"][0]["id"] == attack["alert_id"]
    assert client.get("/api/v1/alerts", params={"limit": 0}).status_code == 422
    assert client.get("/api/v1/alerts", params={"offset": 2**63}).status_code == 422
    assert client.get("/api/v1/alerts/2147483647").status_code == 404
    assert client.get(url).json()["prediction"]["id"] == attack["prediction_id"]
    assert client.patch(f"{url}/status", json={"status": "closed"}).status_code == 409
    for status in ("investigating", "investigating", "resolved", "closed"):
        assert client.patch(f"{url}/status", json={"status": status}).status_code == 200
    change_history = client.get(url).json()["status_history"]
    assert [(row["previous_status"], row["new_status"]) for row in change_history] == [
        ("open", "investigating"), ("investigating", "resolved"), ("resolved", "closed"),
    ]

    with Session(engine) as session:
        session.add(SecurityAlert(prediction_id=attack["prediction_id"], severity="high"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_alert_insert_failure_rolls_back_prediction(client_and_engine):
    client, engine = client_and_engine

    def invalidate_alert(mapper, connection, alert):
        alert.severity = "invalid"

    with Session(engine) as session:
        before = session.scalars(select(Prediction.id)).all()

    event.listen(SecurityAlert, "before_insert", invalidate_alert)
    try:
        response = submit(client, 0.99)
        assert response.status_code == 503
        assert response.json() == {"detail": "Database operation failed"}
    finally:
        event.remove(SecurityAlert, "before_insert", invalidate_alert)

    with Session(engine) as session:
        assert session.scalars(select(Prediction.id)).all() == before


@pytest.mark.parametrize("score, level", [
    (0.69, "low"), (0.70, "medium"), (0.85, "high"), (0.95, "critical"),
])
def test_severity_boundaries(score, level):
    assert SeverityPolicy().classify(score) == level


def test_severity_configuration(monkeypatch):
    monkeypatch.setenv("ALERT_SEVERITY_MEDIUM", "0.60")
    assert SeverityPolicy.from_environment().classify(0.60) == "medium"
    monkeypatch.setenv("ALERT_SEVERITY_MEDIUM", "0.90")
    with pytest.raises(ValidationError):
        SeverityPolicy.from_environment()


def test_alert_requires_existing_prediction(client_and_engine):
    _, engine = client_and_engine
    with Session(engine) as session:
        session.add(SecurityAlert(prediction_id=-1, severity="high"))
        with pytest.raises(IntegrityError):
            session.commit()
