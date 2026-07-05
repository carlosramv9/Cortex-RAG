"""Use case: fetch a single processing job."""

from __future__ import annotations

from app.application.processing.dtos import GetJobInput, JobView
from app.domain.documents.repositories import ProcessingJobRepository
from app.domain.shared.exceptions import EntityNotFoundError


class GetProcessingJobUseCase:
    """Return a processing job by id, scoped to its tenant."""

    def __init__(self, jobs: ProcessingJobRepository) -> None:
        self._jobs = jobs

    async def execute(self, data: GetJobInput) -> JobView:
        job = await self._jobs.get(data.tenant_id, data.job_id)
        if job is None:
            raise EntityNotFoundError(f"Processing job {data.job_id} not found.")
        return JobView.from_entity(job)
