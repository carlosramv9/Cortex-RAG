"""Shared constants and enums used across layers."""

from __future__ import annotations

from enum import StrEnum

API_V1_PREFIX = "/api/v1"


class DocumentStatus(StrEnum):
    """Lifecycle status of a knowledge document.

    Ingestion stops at ``UPLOADED`` in this phase; parsing/processing states are
    reserved for later phases.
    """

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DELETED = "deleted"


class ProcessingJobStatus(StrEnum):
    """Lifecycle status of an asynchronous processing job."""

    QUEUED = "queued"
    RUNNING = "running"
    PARSING = "parsing"
    RENDERING = "rendering"
    NORMALIZING = "normalizing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Statuses in which a job is considered still active (occupies its type slot).
ACTIVE_JOB_STATUSES: frozenset[ProcessingJobStatus] = frozenset(
    {
        ProcessingJobStatus.QUEUED,
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.PARSING,
        ProcessingJobStatus.RENDERING,
        ProcessingJobStatus.NORMALIZING,
        ProcessingJobStatus.CHUNKING,
        ProcessingJobStatus.EMBEDDING,
        ProcessingJobStatus.INDEXING,
    }
)

# Terminal statuses.
TERMINAL_JOB_STATUSES: frozenset[ProcessingJobStatus] = frozenset(
    {
        ProcessingJobStatus.COMPLETED,
        ProcessingJobStatus.FAILED,
        ProcessingJobStatus.CANCELLED,
    }
)


class StorageProviderKind(StrEnum):
    """Identifier of the storage backend that holds a document's bytes."""

    LOCAL = "local"
    S3 = "s3"
