"""No-op ingestion worker.

Placeholder for the future document-ingestion pipeline (parse -> render ->
normalize -> chunk -> embed -> index). It performs no parsing/AI yet; it simply
completes so the async pipeline is fully wired and observable end to end.
"""

from __future__ import annotations

from app.domain.documents.jobs import JobType, ProcessingJob
from app.workers.base import Worker


class NoOpIngestionWorker(Worker):
    """Handles DOCUMENT_INGESTION jobs (does no real work yet)."""

    job_type = JobType.DOCUMENT_INGESTION

    async def run(self, job: ProcessingJob) -> None:
        # Real ingestion steps (parsing, rendering, chunking, embedding,
        # indexing) will be implemented in later phases. No-op for now.
        return None
