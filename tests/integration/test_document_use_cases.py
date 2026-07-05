"""Tests for the document use cases (with a real repository)."""

from __future__ import annotations

import pytest

from app.application.documents.dtos import (
    GetDocumentInput,
    ListDocumentsInput,
    UpdateDocumentMetadataInput,
    UploadDocumentInput,
)
from app.application.documents.use_cases.delete_document import DeleteDocumentUseCase
from app.application.documents.use_cases.get_document import GetDocumentUseCase
from app.application.documents.use_cases.list_documents import ListDocumentsUseCase
from app.application.documents.use_cases.update_document_metadata import (
    UpdateDocumentMetadataUseCase,
)
from app.config.settings import UploadSettings
from app.domain.documents.events import (
    DocumentDeleted,
    DocumentMetadataUpdated,
    DocumentUploaded,
    ProcessingJobCreated,
)
from app.domain.documents.jobs import JobType
from app.domain.documents.metadata import KnowledgeMetadata, SecurityLevel
from app.domain.documents.source_type import SourceType
from app.domain.shared.exceptions import (
    ConflictError,
    EntityNotFoundError,
    ValidationError,
)
from app.infrastructure.persistence.sqlalchemy.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.infrastructure.persistence.sqlalchemy.repositories.processing_job_repository import (
    SqlAlchemyProcessingJobRepository,
)
from app.shared.constants import DocumentStatus, ProcessingJobStatus
from tests.builders import build_upload_use_case
from tests.fakes import CapturingEventPublisher, InMemoryStorage

PDF = b"%PDF-1.7 minimal content"


def _upload_input(**overrides: object) -> UploadDocumentInput:
    data: dict[str, object] = {
        "tenant_id": "tenant-a",
        "original_filename": "report.pdf",
        "content": PDF,
        "content_type": "application/pdf",
    }
    data.update(overrides)
    return UploadDocumentInput(**data)  # type: ignore[arg-type]


async def test_upload_stores_registers_and_enqueues_job(
    document_repo: SqlAlchemyDocumentRepository,
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    storage = InMemoryStorage()
    events = CapturingEventPublisher()
    use_case = build_upload_use_case(document_repo, job_repo, storage=storage, events=events)

    view = await use_case.execute(_upload_input())

    assert view.status == DocumentStatus.UPLOADED
    assert view.size == len(PDF)
    assert view.checksum_sha256
    assert any(k.startswith("documents/tenant-a/") for k in storage.objects)
    # Both a DocumentUploaded and a ProcessingJobCreated event were published.
    assert any(isinstance(e, DocumentUploaded) for e in events.events)
    assert any(isinstance(e, ProcessingJobCreated) for e in events.events)

    # A QUEUED ingestion job now exists for the document.
    jobs, total = await job_repo.list_jobs("tenant-a")
    assert total == 1
    assert jobs[0].job_type == JobType.DOCUMENT_INGESTION
    assert jobs[0].status == ProcessingJobStatus.QUEUED


async def test_upload_duplicate_checksum_conflicts(
    document_repo: SqlAlchemyDocumentRepository,
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    use_case = build_upload_use_case(document_repo, job_repo)
    await use_case.execute(_upload_input())

    with pytest.raises(ConflictError):
        await use_case.execute(_upload_input())


async def test_upload_rejects_bad_extension(
    document_repo: SqlAlchemyDocumentRepository,
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    use_case = build_upload_use_case(document_repo, job_repo)

    with pytest.raises(ValidationError):
        await use_case.execute(_upload_input(original_filename="notes.txt"))


async def test_upload_rejects_oversize(
    document_repo: SqlAlchemyDocumentRepository,
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    use_case = build_upload_use_case(
        document_repo, job_repo, upload_settings=UploadSettings(max_size_mb=0)
    )

    with pytest.raises(ValidationError):
        await use_case.execute(_upload_input())


async def test_upload_rejects_empty(
    document_repo: SqlAlchemyDocumentRepository,
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    use_case = build_upload_use_case(document_repo, job_repo)

    with pytest.raises(ValidationError):
        await use_case.execute(_upload_input(content=b""))


async def test_get_and_list(
    document_repo: SqlAlchemyDocumentRepository,
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    upload = build_upload_use_case(document_repo, job_repo)
    view = await upload.execute(_upload_input())

    got = await GetDocumentUseCase(document_repo).execute(
        GetDocumentInput(tenant_id="tenant-a", document_id=view.id)
    )
    assert got.id == view.id

    listed = await ListDocumentsUseCase(document_repo).execute(
        ListDocumentsInput(tenant_id="tenant-a")
    )
    assert listed.total == 1


async def test_delete_then_get_missing_raises(
    document_repo: SqlAlchemyDocumentRepository,
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    upload = build_upload_use_case(document_repo, job_repo)
    view = await upload.execute(_upload_input())

    events = CapturingEventPublisher()
    await DeleteDocumentUseCase(document_repo, events).execute(
        GetDocumentInput(tenant_id="tenant-a", document_id=view.id)
    )

    assert isinstance(events.events[0], DocumentDeleted)
    with pytest.raises(EntityNotFoundError):
        await GetDocumentUseCase(document_repo).execute(
            GetDocumentInput(tenant_id="tenant-a", document_id=view.id)
        )


async def test_update_metadata_replaces(
    document_repo: SqlAlchemyDocumentRepository,
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    upload = build_upload_use_case(document_repo, job_repo)
    view = await upload.execute(_upload_input())

    events = CapturingEventPublisher()
    updated = await UpdateDocumentMetadataUseCase(document_repo, events).execute(
        UpdateDocumentMetadataInput(
            tenant_id="tenant-a",
            document_id=view.id,
            metadata=KnowledgeMetadata(author="Ada", language="es"),
        )
    )

    assert updated.metadata.author == "Ada"
    assert updated.metadata.language == "es"
    assert isinstance(events.events[0], DocumentMetadataUpdated)


async def test_metadata_survives_persistence_roundtrip(
    document_repo: SqlAlchemyDocumentRepository,
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    upload = build_upload_use_case(document_repo, job_repo)
    view = await upload.execute(_upload_input())

    await UpdateDocumentMetadataUseCase(document_repo, CapturingEventPublisher()).execute(
        UpdateDocumentMetadataInput(
            tenant_id="tenant-a",
            document_id=view.id,
            metadata=KnowledgeMetadata(
                language="es",
                department="RH",
                security_level=SecurityLevel.CONFIDENTIAL,
                tags=["ISO9001"],
                keywords=["auditoria"],
            ),
        )
    )

    reloaded = await GetDocumentUseCase(document_repo).execute(
        GetDocumentInput(tenant_id="tenant-a", document_id=view.id)
    )
    assert reloaded.metadata.language == "es"
    assert reloaded.metadata.department == "RH"
    assert reloaded.metadata.security_level == SecurityLevel.CONFIDENTIAL
    assert reloaded.metadata.tags == ["ISO9001"]
    assert reloaded.source_type == SourceType.PDF
