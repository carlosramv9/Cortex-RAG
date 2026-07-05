"""API tests for the processing-jobs endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

PDF = b"%PDF-1.7 processing api test"


def _upload(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/documents",
        files={"file": ("report.pdf", PDF, "application/pdf")},
    )
    assert resp.status_code == 201
    return resp.json()["id"]  # type: ignore[no-any-return]


def test_upload_creates_queued_job_listed_by_api(api_client: TestClient) -> None:
    document_id = _upload(api_client)

    listed = api_client.get("/api/v1/processing-jobs", params={"document_id": document_id})
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    job = body["items"][0]
    assert job["job_type"] == "document_ingestion"
    assert job["status"] == "queued"
    assert job["document_id"] == document_id


def test_get_processing_job_by_id(api_client: TestClient) -> None:
    document_id = _upload(api_client)
    job_id = api_client.get("/api/v1/processing-jobs", params={"document_id": document_id}).json()[
        "items"
    ][0]["id"]

    resp = api_client.get(f"/api/v1/processing-jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


def test_get_missing_job_returns_404(api_client: TestClient) -> None:
    resp = api_client.get("/api/v1/processing-jobs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_filter_by_status(api_client: TestClient) -> None:
    _upload(api_client)
    resp = api_client.get("/api/v1/processing-jobs", params={"status": "queued"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    empty = api_client.get("/api/v1/processing-jobs", params={"status": "completed"})
    assert empty.json()["total"] == 0
