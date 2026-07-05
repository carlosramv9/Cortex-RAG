"""Domain events for the documents context.

Only ingestion-level events exist in this phase. Parsing/embedding events are
reserved for later phases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.domain.shared.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentUploaded(DomainEvent):
    """Emitted when a document has been created with its first version."""

    document_id: UUID
    tenant_id: str
    version_id: UUID
    version_number: int
    checksum_sha256: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentVersionAdded(DomainEvent):
    """Emitted when a new immutable version is added to an existing document."""

    document_id: UUID
    tenant_id: str
    version_id: UUID
    version_number: int
    checksum_sha256: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentDeleted(DomainEvent):
    """Emitted when a document has been (soft) deleted."""

    document_id: UUID
    tenant_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentMetadataUpdated(DomainEvent):
    """Emitted when a document's metadata has been updated."""

    document_id: UUID
    tenant_id: str
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessingJobCreated(DomainEvent):
    """Emitted when a processing job is enqueued (status QUEUED)."""

    job_id: UUID
    document_id: UUID
    tenant_id: str
    job_type: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessingJobStarted(DomainEvent):
    """Emitted when a worker starts a job (status RUNNING)."""

    job_id: UUID
    document_id: UUID
    tenant_id: str
    worker_name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessingJobCompleted(DomainEvent):
    """Emitted when a job finishes successfully (status COMPLETED)."""

    job_id: UUID
    document_id: UUID
    tenant_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessingJobFailed(DomainEvent):
    """Emitted when a job fails terminally (status FAILED)."""

    job_id: UUID
    document_id: UUID
    tenant_id: str
    error_message: str
    retry_count: int
