from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_check_returns_200():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "FloodPath API"


def test_root_endpoint_returns_200():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
