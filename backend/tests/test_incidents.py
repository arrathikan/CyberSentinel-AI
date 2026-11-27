from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from itertools import combinations
from threading import Barrier

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from backend.app.api.correlation import CorrelationPolicy, FlowMetadata, correlate_alert
from backend.app.database.models import Incident, IncidentAlert, Prediction, SecurityAlert
from backend.tests.test_prediction_alerts import client_and_engine  # noqa: F401


@pytest.fixture(autouse=True)
def configure_correlation(monkeypatch):
    monkeypatch.setenv("INCIDENT_CORRELATION_SECRET", "synthetic-test-secret-for-incidents-only")
    monkeypatch.setenv("INCIDENT_WINDOW_SECONDS", "300")


def flow(source, observed_at, **overrides):
    return {
        "source_ip": f"192.0.2.{source}",
        "destination_ip": "198.51.100.10",
        "destination_port": 443,
        "protocol": "tcp",
        "observed_at": observed_at.isoformat(),
        **overrides,
    }


def submit(client, metadata=None, score=0.96):
    return client.post("/api/v1/predict", json={"features": {"score": score}, "metadata": metadata})


def membership(client, alert_id):
    return client.get(f"/api/v1/alerts/{alert_id}/incident")


def test_labeled_grouping_and_read_apis(client_and_engine):
    client, _ = client_and_engine
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    scenarios = [
        ("a", flow(1, now)),
        ("a", flow(1, now + timedelta(seconds=300), source_port=59801)),
        ("a", flow(1, now + timedelta(seconds=30))),
        ("b", flow(1, now + timedelta(seconds=301))),
        ("c", flow(2, now)),
        ("d", flow(1, now, protocol="udp")),
        ("e", flow(1, now, destination_port=80)),
        ("f", flow(1, now, destination_ip="198.51.100.11")),
    ]
    assigned = []
    for index, (expected, metadata) in enumerate(scenarios):
        response = submit(client, metadata, score=0.75 if index == 0 else 0.96)
        assert response.status_code == 200
        alert_id = response.json()["alert_id"]
        result = membership(client, alert_id)
        assert result.status_code == 200
        assigned.append((expected, result.json()["incident"]["id"]))

    pairs = list(combinations(assigned, 2))
    incorrect = sum(a != b and x == y for (a, x), (b, y) in pairs)
    missed = sum(a == b and x != y for (a, x), (b, y) in pairs)
    assert (incorrect, missed) == (0, 0)

    incident_id = assigned[0][1]
    detail = client.get(f"/api/v1/incidents/{incident_id}").json()
    assert detail["severity"] == "critical"
    assert detail["status"] == "open"
    assert datetime.fromisoformat(detail["first_seen_at"]) == now
    page = client.get(f"/api/v1/incidents/{incident_id}/alerts?limit=1&offset=1").json()
    assert page["total"] == 3
    assert "Matched source IP" in page["items"][0]["correlation_reason"]
    assert "192.0.2." not in str(page)
    listing = client.get("/api/v1/incidents?status=open&severity=critical&limit=1").json()
    assert listing["total"] >= 6 and len(listing["items"]) == 1
    assert client.get("/api/v1/incidents?severity=unknown").status_code == 422
    assert client.get("/api/v1/incidents/2147483647").status_code == 404


def test_incomplete_invalid_and_benign_metadata(client_and_engine):
    client, _ = client_and_engine
    now = datetime.now(timezone.utc)
    for metadata in (None, flow(3, now, destination_ip=None), flow(3, now + timedelta(hours=1))):
        response = submit(client, metadata)
        assert response.status_code == 200
        alert_id = response.json()["alert_id"]
        assert membership(client, alert_id).status_code == 404
        assert client.get(f"/api/v1/alerts/{alert_id}").status_code == 200
    bad_response = submit(client, flow(3, now, source_ip="sensitive-invalid-value"))
    assert bad_response.status_code == 422
    assert "sensitive-invalid-value" not in bad_response.text
    assert submit(client, flow(3, now), score=0.2).json()["alert_id"] is None


def test_same_alert_can_be_reprocessed_without_duplicate(client_and_engine):
    client, engine = client_and_engine
    metadata = flow(4, datetime.now(timezone.utc))
    alert_id = submit(client, metadata).json()["alert_id"]
    with Session(engine) as db, db.begin():
        alert = db.get(SecurityAlert, alert_id)
        for _ in range(2):
            result = correlate_alert(
                db, alert, FlowMetadata.model_validate(metadata), CorrelationPolicy.from_environment(),
            )
            assert result.alert_id == alert_id
        assert db.scalar(select(func.count()).select_from(IncidentAlert).where(
            IncidentAlert.alert_id == alert_id
        )) == 1


def test_failed_association_rolls_back_all_writes(client_and_engine):
    client, engine = client_and_engine

    def invalidate_member(mapper, connection, member):
        member.correlation_reason = None

    def counts():
        with Session(engine) as db:
            return tuple(db.scalar(select(func.count()).select_from(model)) for model in (
                Prediction, SecurityAlert, Incident, IncidentAlert,
            ))

    before = counts()
    event.listen(IncidentAlert, "before_insert", invalidate_member)
    try:
        response = submit(client, flow(5, datetime.now(timezone.utc)))
        assert response.status_code == 503
    finally:
        event.remove(IncidentAlert, "before_insert", invalidate_member)
    assert counts() == before


def test_concurrent_alerts_share_one_incident(client_and_engine):
    client, engine = client_and_engine
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL advisory lock integration test")

    metadata = flow(6, datetime.now(timezone.utc))
    workers = 6
    barrier = Barrier(workers)

    def submit_concurrently():
        barrier.wait(timeout=10)
        response = submit(client, metadata)
        assert response.status_code == 200
        return response.json()["alert_id"]

    with ThreadPoolExecutor(max_workers=workers) as pool:
        alerts = list(pool.map(lambda _: submit_concurrently(), range(workers)))
    assert len(set(alerts)) == workers
    ids = {membership(client, alert).json()["incident"]["id"] for alert in alerts}
    assert len(ids) == 1
    assert client.get(f"/api/v1/incidents/{ids.pop()}/alerts").json()["total"] == workers
