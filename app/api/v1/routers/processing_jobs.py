"""Processing jobs router (read-only).

    GET /processing-jobs        list (paged, tenant-scoped, filterable)
    GET /processing-jobs/{id}   fetch one

No endpoint executes jobs manually — a worker process does that.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import (
    GetProcessingJobUseCaseDep,
    ListProcessingJobsUseCaseDep,
    TenantIdDep,
)
from app.application.processing.dtos import (
    GetJobInput,
    JobView,
    ListJobsInput,
    ListJobsOutput,
)
from app.shared.constants import ProcessingJobStatus

router = APIRouter(prefix="/processing-jobs", tags=["processing-jobs"])


@router.get("", response_model=ListJobsOutput)
async def list_processing_jobs(
    use_case: ListProcessingJobsUseCaseDep,
    tenant_id: TenantIdDep,
    document_id: UUID | None = Query(default=None),
    status: ProcessingJobStatus | None = Query(default=None),
    limit: int = Query(default=50, gt=0, le=200),
    offset: int = Query(default=0, ge=0),
) -> ListJobsOutput:
    """List processing jobs."""
    return await use_case.execute(
        ListJobsInput(
            tenant_id=tenant_id,
            document_id=document_id,
            status=status,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/{job_id}", response_model=JobView)
async def get_processing_job(
    job_id: UUID,
    use_case: GetProcessingJobUseCaseDep,
    tenant_id: TenantIdDep,
) -> JobView:
    """Fetch a single processing job."""
    return await use_case.execute(GetJobInput(tenant_id=tenant_id, job_id=job_id))
