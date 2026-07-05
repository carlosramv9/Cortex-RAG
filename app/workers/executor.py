"""WorkerExecutor: runs a single job through its lifecycle.

Drives the state machine (start -> run -> complete / fail), persists every
transition and publishes domain events. Retry policy: on failure, if the job
has retries left it is re-queued; otherwise it fails terminally.

Depends only on domain ports (repository, event publisher). Transport-agnostic.
"""

from __future__ import annotations

from app.domain.documents.events import (
    ProcessingJobCompleted,
    ProcessingJobFailed,
    ProcessingJobStarted,
)
from app.domain.documents.jobs import ProcessingJob
from app.domain.documents.repositories import ProcessingJobRepository
from app.domain.shared.event_publisher import EventPublisher
from app.workers.registry import WorkerRegistry


class WorkerExecutor:
    """Executes one processing job."""

    def __init__(
        self,
        jobs: ProcessingJobRepository,
        events: EventPublisher,
        registry: WorkerRegistry,
        *,
        max_retries: int = 3,
    ) -> None:
        self._jobs = jobs
        self._events = events
        self._registry = registry
        self._max_retries = max_retries

    async def execute(self, job: ProcessingJob) -> ProcessingJob:
        worker = self._registry.get(job.job_type)
        if worker is None:
            job.fail(f"No worker registered for job type '{job.job_type}'.")
            await self._jobs.update(job)
            await self._publish_failed(job)
            return job

        job.start(worker.name)
        await self._jobs.update(job)
        await self._events.publish(
            ProcessingJobStarted(
                job_id=job.id,
                document_id=job.document_id,
                tenant_id=job.tenant_id,
                worker_name=worker.name,
            )
        )

        try:
            await worker.run(job)
        except Exception as exc:
            job.fail(str(exc))
            if job.can_retry(self._max_retries):
                job.retry()
                await self._jobs.update(job)
            else:
                await self._jobs.update(job)
                await self._publish_failed(job)
            return job

        job.complete()
        await self._jobs.update(job)
        await self._events.publish(
            ProcessingJobCompleted(
                job_id=job.id,
                document_id=job.document_id,
                tenant_id=job.tenant_id,
            )
        )
        return job

    async def _publish_failed(self, job: ProcessingJob) -> None:
        await self._events.publish(
            ProcessingJobFailed(
                job_id=job.id,
                document_id=job.document_id,
                tenant_id=job.tenant_id,
                error_message=job.error_message or "",
                retry_count=job.retry_count,
            )
        )
