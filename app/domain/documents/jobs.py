"""ProcessingJob: unit of asynchronous work over a document.

Pure domain: the state machine and its transitions live here. The domain knows
nothing about workers, queues, Celery or FastAPI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from app.domain.shared.exceptions import ValidationError
from app.shared.constants import (
    ACTIVE_JOB_STATUSES,
    TERMINAL_JOB_STATUSES,
    ProcessingJobStatus,
)


class JobType(StrEnum):
    """Type of processing job."""

    DOCUMENT_INGESTION = "document_ingestion"
    RENDER_PAGES = "render_pages"
    OCR = "ocr"
    CHUNKING = "chunking"
    GENERATE_EMBEDDINGS = "generate_embeddings"
    REINDEX = "reindex"
    DELETE_INDEX = "delete_index"


# Intermediate phase statuses a running job may progress through.
_PHASE_STATUSES: frozenset[ProcessingJobStatus] = frozenset(
    {
        ProcessingJobStatus.PARSING,
        ProcessingJobStatus.RENDERING,
        ProcessingJobStatus.NORMALIZING,
        ProcessingJobStatus.CHUNKING,
        ProcessingJobStatus.EMBEDDING,
        ProcessingJobStatus.INDEXING,
    }
)


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class ProcessingJob:
    """An asynchronous processing job bound to a document (and its version)."""

    id: UUID
    document_id: UUID
    tenant_id: str
    job_type: JobType
    status: ProcessingJobStatus = ProcessingJobStatus.QUEUED
    version_id: UUID | None = None
    priority: int = 0
    retry_count: int = 0
    progress: int = 0
    worker_name: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_JOB_STATUSES

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_JOB_STATUSES

    # --- transitions ------------------------------------------------------

    def start(self, worker_name: str) -> None:
        """QUEUED -> RUNNING."""
        if self.status != ProcessingJobStatus.QUEUED:
            raise ValidationError(f"Cannot start job in status '{self.status}'; expected QUEUED.")
        self.status = ProcessingJobStatus.RUNNING
        self.worker_name = worker_name
        self.started_at = _now()
        self.progress = 0
        self.error_message = None

    def advance(self, phase: ProcessingJobStatus, progress: int) -> None:
        """Move a running job to an intermediate phase and report progress."""
        if phase not in _PHASE_STATUSES:
            raise ValidationError(f"'{phase}' is not a valid processing phase.")
        if self.status not in (ProcessingJobStatus.RUNNING, *_PHASE_STATUSES):
            raise ValidationError(f"Cannot advance job in status '{self.status}'.")
        self.status = phase
        self.progress = max(0, min(100, progress))

    def complete(self) -> None:
        """-> COMPLETED."""
        if self.is_terminal:
            raise ValidationError(f"Job already terminal ('{self.status}').")
        self.status = ProcessingJobStatus.COMPLETED
        self.progress = 100
        self.finished_at = _now()
        self.error_message = None

    def fail(self, error_message: str) -> None:
        """-> FAILED (terminal)."""
        if self.is_terminal:
            raise ValidationError(f"Job already terminal ('{self.status}').")
        self.status = ProcessingJobStatus.FAILED
        self.finished_at = _now()
        self.error_message = error_message

    def cancel(self) -> None:
        """-> CANCELLED (terminal)."""
        if self.is_terminal:
            raise ValidationError(f"Job already terminal ('{self.status}').")
        self.status = ProcessingJobStatus.CANCELLED
        self.finished_at = _now()

    def can_retry(self, max_retries: int) -> bool:
        """Whether a failed job may be retried."""
        return self.status == ProcessingJobStatus.FAILED and self.retry_count < max_retries

    def retry(self) -> None:
        """FAILED -> QUEUED, incrementing retry_count."""
        if self.status != ProcessingJobStatus.FAILED:
            raise ValidationError(f"Only failed jobs can be retried (status '{self.status}').")
        self.status = ProcessingJobStatus.QUEUED
        self.retry_count += 1
        self.progress = 0
        self.worker_name = None
        self.started_at = None
        self.finished_at = None
        self.error_message = None
