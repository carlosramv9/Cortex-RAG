"""Use case: list processing jobs for a tenant."""

from __future__ import annotations

from app.application.processing.dtos import JobView, ListJobsInput, ListJobsOutput
from app.domain.documents.repositories import ProcessingJobRepository


class ListProcessingJobsUseCase:
    """Return a paged list of processing jobs."""

    def __init__(self, jobs: ProcessingJobRepository) -> None:
        self._jobs = jobs

    async def execute(self, data: ListJobsInput) -> ListJobsOutput:
        items, total = await self._jobs.list_jobs(
            data.tenant_id,
            document_id=data.document_id,
            status=data.status,
            limit=data.limit,
            offset=data.offset,
        )
        return ListJobsOutput(
            items=[JobView.from_entity(j) for j in items],
            total=total,
            limit=data.limit,
            offset=data.offset,
        )
