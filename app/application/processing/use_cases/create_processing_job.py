"""Use case: enqueue a processing job (status QUEUED).

Enforces "only one active job per type per document". Does NOT execute the job
— a worker picks it up later.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.application.processing.dtos import CreateProcessingJobInput, JobView
from app.config.settings import ProcessingSettings
from app.domain.documents.events import ProcessingJobCreated
from app.domain.documents.jobs import ProcessingJob
from app.domain.documents.repositories import ProcessingJobRepository
from app.domain.shared.event_publisher import EventPublisher
from app.domain.shared.exceptions import ConflictError
from app.shared.constants import ProcessingJobStatus


class CreateProcessingJobUseCase:
    """Create and enqueue a processing job."""

    def __init__(
        self,
        jobs: ProcessingJobRepository,
        events: EventPublisher,
        settings: ProcessingSettings,
    ) -> None:
        self._jobs = jobs
        self._events = events
        self._settings = settings

    async def execute(self, data: CreateProcessingJobInput) -> JobView:
        active = await self._jobs.get_active_by_type(data.document_id, data.job_type)
        if active is not None:
            raise ConflictError(
                f"An active '{data.job_type}' job already exists for document "
                f"{data.document_id} (id={active.id})."
            )

        now = datetime.now(UTC)
        job = ProcessingJob(
            id=uuid4(),
            document_id=data.document_id,
            tenant_id=data.tenant_id,
            job_type=data.job_type,
            version_id=data.version_id,
            status=ProcessingJobStatus.QUEUED,
            priority=(
                data.priority if data.priority is not None else self._settings.default_priority
            ),
            created_at=now,
            updated_at=now,
        )
        await self._jobs.add(job)

        await self._events.publish(
            ProcessingJobCreated(
                job_id=job.id,
                document_id=job.document_id,
                tenant_id=job.tenant_id,
                job_type=str(job.job_type),
            )
        )
        return JobView.from_entity(job)
