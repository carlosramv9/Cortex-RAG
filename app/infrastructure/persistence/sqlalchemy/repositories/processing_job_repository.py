"""SQLAlchemy implementation of ``ProcessingJobRepository``."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.documents.jobs import JobType, ProcessingJob
from app.domain.documents.repositories import ProcessingJobRepository
from app.infrastructure.persistence.sqlalchemy.models import ProcessingJobModel
from app.shared.constants import ACTIVE_JOB_STATUSES, ProcessingJobStatus


def _to_entity(model: ProcessingJobModel) -> ProcessingJob:
    return ProcessingJob(
        id=model.id,
        document_id=model.document_id,
        tenant_id=model.tenant_id,
        job_type=JobType(model.job_type),
        status=ProcessingJobStatus(model.status),
        version_id=model.version_id,
        priority=model.priority,
        retry_count=model.retry_count,
        progress=model.progress,
        worker_name=model.worker_name,
        error_message=model.error_message,
        started_at=model.started_at,
        finished_at=model.finished_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_model(entity: ProcessingJob) -> ProcessingJobModel:
    return ProcessingJobModel(
        id=entity.id,
        document_id=entity.document_id,
        version_id=entity.version_id,
        tenant_id=entity.tenant_id,
        job_type=str(entity.job_type),
        status=str(entity.status),
        priority=entity.priority,
        retry_count=entity.retry_count,
        progress=entity.progress,
        worker_name=entity.worker_name,
        error_message=entity.error_message,
        started_at=entity.started_at,
        finished_at=entity.finished_at,
    )


class SqlAlchemyProcessingJobRepository(ProcessingJobRepository):
    """SQLAlchemy-backed processing job repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, job: ProcessingJob) -> None:
        self._session.add(_to_model(job))
        await self._session.flush()

    async def get(self, tenant_id: str, job_id: UUID) -> ProcessingJob | None:
        stmt = select(ProcessingJobModel).where(
            ProcessingJobModel.id == job_id,
            ProcessingJobModel.tenant_id == tenant_id,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_entity(model) if model is not None else None

    async def update(self, job: ProcessingJob) -> None:
        model = await self._session.get(ProcessingJobModel, job.id)
        if model is None:
            return
        model.status = str(job.status)
        model.priority = job.priority
        model.retry_count = job.retry_count
        model.progress = job.progress
        model.worker_name = job.worker_name
        model.error_message = job.error_message
        model.started_at = job.started_at
        model.finished_at = job.finished_at
        await self._session.flush()

    async def get_active_by_type(
        self, document_id: UUID, job_type: JobType
    ) -> ProcessingJob | None:
        stmt = select(ProcessingJobModel).where(
            ProcessingJobModel.document_id == document_id,
            ProcessingJobModel.job_type == str(job_type),
            ProcessingJobModel.status.in_([str(s) for s in ACTIVE_JOB_STATUSES]),
        )
        model = (await self._session.execute(stmt)).scalars().first()
        return _to_entity(model) if model is not None else None

    async def list_jobs(
        self,
        tenant_id: str,
        *,
        document_id: UUID | None = None,
        status: ProcessingJobStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ProcessingJob], int]:
        filters = [ProcessingJobModel.tenant_id == tenant_id]
        if document_id is not None:
            filters.append(ProcessingJobModel.document_id == document_id)
        if status is not None:
            filters.append(ProcessingJobModel.status == str(status))

        total_stmt = select(func.count()).select_from(ProcessingJobModel).where(*filters)
        total = (await self._session.execute(total_stmt)).scalar_one()

        stmt = (
            select(ProcessingJobModel)
            .where(*filters)
            .order_by(ProcessingJobModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models], int(total)

    async def claim_queued(self, *, limit: int) -> list[ProcessingJob]:
        stmt = (
            select(ProcessingJobModel)
            .where(ProcessingJobModel.status == str(ProcessingJobStatus.QUEUED))
            .order_by(
                ProcessingJobModel.priority.desc(),
                ProcessingJobModel.created_at.asc(),
            )
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(m) for m in models]
