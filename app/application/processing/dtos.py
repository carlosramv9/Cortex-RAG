"""DTOs for the processing pipeline use cases."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.documents.jobs import JobType, ProcessingJob
from app.shared.constants import ProcessingJobStatus


class JobView(BaseModel):
    """Read model of a processing job."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    version_id: UUID | None
    tenant_id: str
    job_type: JobType
    status: ProcessingJobStatus
    priority: int
    retry_count: int
    progress: int
    worker_name: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_entity(cls, job: ProcessingJob) -> JobView:
        return cls.model_validate(job)


class CreateProcessingJobInput(BaseModel):
    """Input to the create-processing-job use case."""

    tenant_id: str
    document_id: UUID
    version_id: UUID | None = None
    job_type: JobType
    priority: int | None = None


class GetJobInput(BaseModel):
    """Input to the get-processing-job use case."""

    tenant_id: str
    job_id: UUID


class ListJobsInput(BaseModel):
    """Input to the list-processing-jobs use case."""

    tenant_id: str
    document_id: UUID | None = None
    status: ProcessingJobStatus | None = None
    limit: int = Field(default=50, gt=0, le=200)
    offset: int = Field(default=0, ge=0)


class ListJobsOutput(BaseModel):
    """Paged list of processing jobs."""

    items: list[JobView]
    total: int
    limit: int
    offset: int
