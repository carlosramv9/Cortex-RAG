"""Tests for SqlAlchemyDocumentRepository (identity + versions)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.infrastructure.persistence.sqlalchemy.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.shared.constants import DocumentStatus
from tests.factories import make_document, make_version


async def test_add_and_get_populates_active_version(
    document_repo: SqlAlchemyDocumentRepository,
) -> None:
    doc, version = make_document()
    await document_repo.add(doc, version)

    fetched = await document_repo.get(doc.tenant_id, doc.id)

    assert fetched is not None
    assert fetched.current_version_id == version.id
    assert fetched.active_version is not None
    assert fetched.active_version.version_number == 1
    assert fetched.active_version.checksum_sha256 == version.checksum_sha256


async def test_get_is_tenant_scoped(
    document_repo: SqlAlchemyDocumentRepository,
) -> None:
    doc, version = make_document(tenant_id="tenant-a")
    await document_repo.add(doc, version)

    assert await document_repo.get("tenant-b", doc.id) is None


async def test_get_by_checksum_finds_across_versions(
    document_repo: SqlAlchemyDocumentRepository,
) -> None:
    doc, version = make_document(checksum="v1sum")
    await document_repo.add(doc, version)

    # Add a second version with a different checksum.
    v2 = make_version(document_id=doc.id, version_number=2, checksum="v2sum")
    doc.current_version_id = v2.id
    await document_repo.add_version(doc, v2)

    # Both the old and new version checksums resolve to the same document.
    for checksum in ("v1sum", "v2sum"):
        found = await document_repo.get_by_checksum(doc.tenant_id, checksum)
        assert found is not None
        assert found.id == doc.id


async def test_add_version_switches_active_and_keeps_history(
    document_repo: SqlAlchemyDocumentRepository,
) -> None:
    doc, v1 = make_document(checksum="c1")
    await document_repo.add(doc, v1)

    v2 = make_version(document_id=doc.id, version_number=2, checksum="c2")
    doc.current_version_id = v2.id
    await document_repo.add_version(doc, v2)

    fetched = await document_repo.get(doc.tenant_id, doc.id)
    assert fetched is not None
    assert fetched.active_version is not None
    assert fetched.active_version.version_number == 2

    history = await document_repo.list_versions(doc.id)
    assert [v.version_number for v in history] == [2, 1]  # newest first, none lost


async def test_list_returns_items_and_total(
    document_repo: SqlAlchemyDocumentRepository,
) -> None:
    for i in range(3):
        doc, version = make_document(checksum=f"c{i}")
        await document_repo.add(doc, version)

    items, total = await document_repo.list_documents("tenant-a", limit=2, offset=0)

    assert total == 3
    assert len(items) == 2
    assert all(d.active_version is not None for d in items)


async def test_soft_delete_hides_document(
    document_repo: SqlAlchemyDocumentRepository,
) -> None:
    doc, version = make_document()
    await document_repo.add(doc, version)

    doc.status = DocumentStatus.DELETED
    doc.deleted_at = datetime.now(UTC)
    await document_repo.update(doc)

    assert await document_repo.get(doc.tenant_id, doc.id) is None
    # Versions are never removed on soft delete.
    assert len(await document_repo.list_versions(doc.id)) == 1


async def test_get_missing_returns_none(
    document_repo: SqlAlchemyDocumentRepository,
) -> None:
    assert await document_repo.get("tenant-a", uuid4()) is None
