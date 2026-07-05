"""Factories for building domain objects in tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.documents.entities import (
    KnowledgeDocument,
    KnowledgeDocumentVersion,
)
from app.domain.documents.jobs import JobType, ProcessingJob
from app.domain.documents.metadata import KnowledgeMetadata
from app.domain.documents.source_type import SourceType
from app.shared.constants import DocumentStatus, ProcessingJobStatus, StorageProviderKind


def make_version(
    *,
    document_id: UUID,
    version_number: int = 1,
    checksum: str = "abc123",
) -> KnowledgeDocumentVersion:
    """Build a valid ``KnowledgeDocumentVersion`` for tests."""
    version_id = uuid4()
    return KnowledgeDocumentVersion(
        id=version_id,
        document_id=document_id,
        version_number=version_number,
        original_filename="report.pdf",
        filename=f"{version_id}.pdf",
        extension="pdf",
        mime_type="application/pdf",
        size=1024,
        checksum_sha256=checksum,
        storage_provider=StorageProviderKind.LOCAL,
        storage_path=f"documents/t/2026/07/{document_id}/{version_id}.pdf",
        uploaded_by="user-1",
        created_at=datetime.now(UTC),
    )


def make_document(
    *,
    tenant_id: str = "tenant-a",
    checksum: str = "abc123",
    status: DocumentStatus = DocumentStatus.UPLOADED,
) -> tuple[KnowledgeDocument, KnowledgeDocumentVersion]:
    """Build a ``(document, initial_version)`` pair for tests."""
    doc_id = uuid4()
    now = datetime.now(UTC)
    version = make_version(document_id=doc_id, checksum=checksum)
    document = KnowledgeDocument(
        id=doc_id,
        tenant_id=tenant_id,
        title="report.pdf",
        source_type=SourceType.PDF,
        current_version_id=version.id,
        status=status,
        metadata=KnowledgeMetadata(),
        created_by="user-1",
        created_at=now,
        updated_at=now,
        active_version=version,
    )
    return document, version


def make_job(
    *,
    tenant_id: str = "tenant-a",
    document_id: UUID | None = None,
    job_type: JobType = JobType.DOCUMENT_INGESTION,
    status: ProcessingJobStatus = ProcessingJobStatus.QUEUED,
    priority: int = 0,
) -> ProcessingJob:
    """Build a ``ProcessingJob`` for tests."""
    now = datetime.now(UTC)
    return ProcessingJob(
        id=uuid4(),
        document_id=document_id or uuid4(),
        tenant_id=tenant_id,
        job_type=job_type,
        status=status,
        priority=priority,
        created_at=now,
        updated_at=now,
    )
