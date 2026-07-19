"""Basic health check test."""
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_racs_groups():
    r = client.get("/api/racs/groups")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_racs_period():
    r = client.get("/api/racs/period")
    assert r.status_code == 200
    data = r.json()
    assert "period_start" in data
    assert "period_end" in data
