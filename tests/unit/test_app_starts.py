"""Smoke test: the application boots and health responds."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_app_starts_and_health_ok(client: TestClient) -> None:
    """The app starts and /health returns 200."""
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"]


def test_openapi_available(client: TestClient) -> None:
    """OpenAPI schema is generated."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"]
