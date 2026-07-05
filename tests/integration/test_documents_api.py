"""End-to-end API tests for the documents endpoints (SQLite-backed)."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_database, get_storage_provider
from app.infrastructure.persistence.sqlalchemy import models  # noqa: F401
from app.infrastructure.persistence.sqlalchemy.base import Base
from app.infrastructure.persistence.sqlalchemy.session import Database
from app.infrastructure.storage.local_storage import LocalStorageProvider
from app.main import create_app

PDF = b"%PDF-1.7 end-to-end test content"


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    database = Database(db_url)

    async def _create_tables() -> None:
        async with database.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_tables())

    app = create_app()
    app.dependency_overrides[get_database] = lambda: database
    storage = LocalStorageProvider(str(tmp_path / "storage"))
    app.dependency_overrides[get_storage_provider] = lambda: storage

    with TestClient(app) as test_client:
        yield test_client


def _upload(client: TestClient, *, filename: str = "report.pdf") -> object:
    return client.post(
        "/api/v1/documents",
        files={"file": (filename, PDF, "application/pdf")},
    )


def test_upload_returns_201_and_view(client: TestClient) -> None:
    response = _upload(client)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "uploaded"
    assert body["size"] == len(PDF)
    assert len(body["checksum_sha256"]) == 64


def test_full_lifecycle(client: TestClient) -> None:
    doc_id = _upload(client).json()["id"]  # type: ignore[attr-defined]

    # list
    listed = client.get("/api/v1/documents").json()
    assert listed["total"] == 1

    # get
    assert client.get(f"/api/v1/documents/{doc_id}").status_code == 200

    # patch metadata (typed)
    patched = client.patch(
        f"/api/v1/documents/{doc_id}",
        json={"metadata": {"language": "es", "department": "RH", "tags": ["ISO9001"]}},
    )
    assert patched.status_code == 200
    assert patched.json()["metadata"]["language"] == "es"
    assert patched.json()["metadata"]["department"] == "RH"
    assert patched.json()["source_type"] == "pdf"


def test_invalid_metadata_language_rejected(client: TestClient) -> None:
    doc_id = _upload(client).json()["id"]  # type: ignore[attr-defined]

    response = client.patch(
        f"/api/v1/documents/{doc_id}",
        json={"metadata": {"language": "klingon"}},
    )
    assert response.status_code == 422

    # delete (soft)
    assert client.delete(f"/api/v1/documents/{doc_id}").status_code == 204

    # gone
    assert client.get(f"/api/v1/documents/{doc_id}").status_code == 404


def test_duplicate_upload_conflicts(client: TestClient) -> None:
    assert _upload(client).status_code == 201  # type: ignore[attr-defined]
    assert _upload(client).status_code == 409  # type: ignore[attr-defined]


def test_invalid_extension_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents",
        files={"file": ("notes.txt", PDF, "text/plain")},
    )
    assert response.status_code == 422
