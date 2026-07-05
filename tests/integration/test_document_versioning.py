"""Tests for document versioning use cases."""

from __future__ import annotations

import pytest

from app.application.documents.dtos import (
    AddDocumentVersionInput,
    GetDocumentInput,
    UploadDocumentInput,
)
from app.application.documents.use_cases.add_document_version import (
    AddDocumentVersionUseCase,
)
from app.application.documents.use_cases.get_document import GetDocumentUseCase
from app.application.documents.use_cases.list_document_versions import (
    ListDocumentVersionsUseCase,
)
from app.config.settings import UploadSettings
from app.domain.documents.events import DocumentVersionAdded
from app.domain.shared.exceptions import EntityNotFoundError
from app.infrastructure.persistence.sqlalchemy.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.infrastructure.persistence.sqlalchemy.repositories.processing_job_repository import (
    SqlAlchemyProcessingJobRepository,
)
from tests.builders import build_upload_use_case
from tests.fakes import CapturingEventPublisher, InMemoryStorage


async def _upload(
    repo: SqlAlchemyDocumentRepository,
    job_repo: SqlAlchemyProcessingJobRepository,
    storage: InMemoryStorage,
    *,
    content: bytes,
) -> object:
    uc = build_upload_use_case(repo, job_repo, storage=storage)
    return await uc.execute(
        UploadDocumentInput(
            tenant_id="tenant-a",
            original_filename="report.pdf",
            content=content,
            content_type="application/pdf",
        )
    )


async def test_add_version_creates_and_activates(
    document_repo: SqlAlchemyDocumentRepository,
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    storage = InMemoryStorage()
    doc = await _upload(document_repo, job_repo, storage, content=b"%PDF v1")
    events = CapturingEventPublisher()

    add = AddDocumentVersionUseCase(document_repo, storage, events, UploadSettings())
    version = await add.execute(
        AddDocumentVersionInput(
            tenant_id="tenant-a",
            document_id=doc.id,  # type: ignore[attr-defined]
            original_filename="report.pdf",
            content=b"%PDF v2 different",
            content_type="application/pdf",
        )
    )

    assert version.version_number == 2
    assert isinstance(events.events[0], DocumentVersionAdded)

    # Active version is now v2.
    got = await GetDocumentUseCase(document_repo).execute(
        GetDocumentInput(tenant_id="tenant-a", document_id=doc.id)  # type: ignore[attr-defined]
    )
    assert got.version_number == 2
    assert got.current_version_id == version.id


async def test_history_is_preserved_and_ordered(
    document_repo: SqlAlchemyDocumentRepository,
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    storage = InMemoryStorage()
    doc = await _upload(document_repo, job_repo, storage, content=b"%PDF v1")
    add = AddDocumentVersionUseCase(
        document_repo, storage, CapturingEventPublisher(), UploadSettings()
    )
    await add.execute(
        AddDocumentVersionInput(
            tenant_id="tenant-a",
            document_id=doc.id,  # type: ignore[attr-defined]
            original_filename="report.pdf",
            content=b"%PDF v2",
            content_type="application/pdf",
        )
    )

    history = await ListDocumentVersionsUseCase(document_repo).execute(
        GetDocumentInput(tenant_id="tenant-a", document_id=doc.id)  # type: ignore[attr-defined]
    )

    assert [v.version_number for v in history.versions] == [2, 1]


async def test_integrity_each_version_keeps_own_bytes(
    document_repo: SqlAlchemyDocumentRepository,
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    storage = InMemoryStorage()
    doc = await _upload(document_repo, job_repo, storage, content=b"%PDF v1 bytes")
    add = AddDocumentVersionUseCase(
        document_repo, storage, CapturingEventPublisher(), UploadSettings()
    )
    await add.execute(
        AddDocumentVersionInput(
            tenant_id="tenant-a",
            document_id=doc.id,  # type: ignore[attr-defined]
            original_filename="report.pdf",
            content=b"%PDF v2 bytes",
            content_type="application/pdf",
        )
    )

    versions = await document_repo.list_versions(doc.id)  # type: ignore[attr-defined]
    # Two distinct stored objects, distinct checksums, distinct paths.
    assert len({v.storage_path for v in versions}) == 2
    assert len({v.checksum_sha256 for v in versions}) == 2
    for v in versions:
        assert v.storage_path in storage.objects


async def test_add_version_missing_document_raises(
    document_repo: SqlAlchemyDocumentRepository,
) -> None:
    from uuid import uuid4

    add = AddDocumentVersionUseCase(
        document_repo, InMemoryStorage(), CapturingEventPublisher(), UploadSettings()
    )

    with pytest.raises(EntityNotFoundError):
        await add.execute(
            AddDocumentVersionInput(
                tenant_id="tenant-a",
                document_id=uuid4(),
                original_filename="report.pdf",
                content=b"%PDF",
                content_type="application/pdf",
            )
        )
