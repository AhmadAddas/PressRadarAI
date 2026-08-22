from fastapi.testclient import TestClient

from pressradar.main import app


def test_health_reports_ready_local_api() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "local"}
