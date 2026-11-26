import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "CyberAgent AI"
    assert "backend is running" in data["message"]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True


def test_model_info(client):
    response = client.get("/api/v1/model-info")
    assert response.status_code == 200
    data = response.json()
    assert "model" in data
    assert "feature_count" in data
    assert "required_features" in data
    assert data["feature_count"] > 0


def test_predict_endpoint(client):
    info_resp = client.get("/api/v1/model-info")
    required_features = info_resp.json()["required_features"]

    # Supply dummy zeroes for all required features
    sample_features = {feat: 0.0 for feat in required_features}

    response = client.post(
        "/api/v1/predict",
        json={"features": sample_features},
    )
    assert response.status_code == 200
    result = response.json()
    assert "prediction" in result
    assert "label" in result
    assert result["label"] in ["Benign", "Attack"]
