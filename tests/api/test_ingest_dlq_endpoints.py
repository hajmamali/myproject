from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_dlq_retry_endpoint_fails_closed_without_unified_loader():
    response = client.post(
        "/api/v1/ingest/dlq/test-job/retry",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 503
    detail = response.json().get("detail", "")
    assert "Unified loader" in detail or "unavailable" in detail.lower()


def test_dlq_delete_endpoint_fails_closed_without_unified_loader():
    response = client.delete(
        "/api/v1/ingest/dlq/test-job",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 503
    detail = response.json().get("detail", "")
    assert "Unified loader" in detail or "unavailable" in detail.lower()
