"""Ingestion worker.

Handles ``DOCUMENT_INGESTION`` jobs by delegating to ``ProcessDocumentUseCase``
(parse -> chunk -> embed -> index). The worker itself only knows about the
domain job contract; the actual pipeline lives in the application layer.
"""

from __future__ import annotations

from app.application.documents.use_cases.process_document import ProcessDocumentUseCase
from app.domain.documents.jobs import JobType, ProcessingJob
from app.workers.base import Worker


class IngestionWorker(Worker):
    """Handles DOCUMENT_INGESTION jobs by running the processing pipeline."""

    job_type = JobType.DOCUMENT_INGESTION

    def __init__(self, process_document: ProcessDocumentUseCase) -> None:
        self._process_document = process_document

    async def run(self, job: ProcessingJob) -> None:
        await self._process_document.execute(job.tenant_id, job.document_id)
