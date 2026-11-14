
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.job_manager import job_manager


client = TestClient(app)


SAMPLE_REQUEST = {
    "patient_id": "TEST-001",
    "policy_id": "POLICY-001",
    "policy_start_date": "2023-01-01",
    "admission_date": "2026-11-15",
    "procedure": "cataract surgery",
    "admission_type": "planned_surgical",
    "room_category": "private",
    "estimated_cost": 100000,
    "diagnosis": "cataract",
    "pre_existing_condition": "unknown",
}


def test_root():
    response = client.get("/")
    assert response.status_code == 200


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_monitoring():
    response = client.get("/monitoring/agent-metrics")
    assert response.status_code == 200


def test_submit_request(monkeypatch):
    monkeypatch.setattr(
        job_manager,
        "submit_job",
        lambda request: {
            "job_id": "test-job-001",
            "status": "queued",
        },
    )

    response = client.post(
        "/requests",
        json=SAMPLE_REQUEST,
    )

    assert response.status_code == 202
    assert response.json()["job_id"] == "test-job-001"


def test_missing_job():
    response = client.get(
        "/requests/nonexistent-job"
    )

    assert response.status_code == 404


def test_missing_job_result():
    response = client.get(
        "/requests/nonexistent-job/result"
    )

    assert response.status_code == 404


def test_invalid_request():
    response = client.post(
        "/requests",
        json={},
    )

    assert response.status_code == 422
