"""Tests for SqlAlchemyProcessingJobRepository."""

from __future__ import annotations

from uuid import uuid4

from app.domain.documents.jobs import JobType
from app.infrastructure.persistence.sqlalchemy.repositories.processing_job_repository import (
    SqlAlchemyProcessingJobRepository,
)
from app.shared.constants import ProcessingJobStatus
from tests.factories import make_job


async def test_add_get_update(
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    job = make_job()
    await job_repo.add(job)

    fetched = await job_repo.get(job.tenant_id, job.id)
    assert fetched is not None
    assert fetched.status == ProcessingJobStatus.QUEUED

    fetched.start("worker-1")
    fetched.advance(ProcessingJobStatus.PARSING, 40)
    await job_repo.update(fetched)

    reloaded = await job_repo.get(job.tenant_id, job.id)
    assert reloaded is not None
    assert reloaded.status == ProcessingJobStatus.PARSING
    assert reloaded.progress == 40
    assert reloaded.worker_name == "worker-1"


async def test_get_is_tenant_scoped(
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    job = make_job(tenant_id="a")
    await job_repo.add(job)
    assert await job_repo.get("b", job.id) is None


async def test_get_active_by_type(
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    doc_id = uuid4()
    active = make_job(document_id=doc_id, status=ProcessingJobStatus.QUEUED)
    await job_repo.add(active)

    found = await job_repo.get_active_by_type(doc_id, JobType.DOCUMENT_INGESTION)
    assert found is not None
    assert found.id == active.id

    # A different type has no active job.
    assert await job_repo.get_active_by_type(doc_id, JobType.OCR) is None


async def test_get_active_ignores_terminal(
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    doc_id = uuid4()
    done = make_job(document_id=doc_id, status=ProcessingJobStatus.COMPLETED)
    await job_repo.add(done)
    assert await job_repo.get_active_by_type(doc_id, JobType.DOCUMENT_INGESTION) is None


async def test_list_jobs_filters(
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    doc_id = uuid4()
    await job_repo.add(make_job(document_id=doc_id))
    await job_repo.add(make_job(status=ProcessingJobStatus.COMPLETED))

    by_doc, total_doc = await job_repo.list_jobs("tenant-a", document_id=doc_id)
    assert total_doc == 1
    assert by_doc[0].document_id == doc_id

    queued, total_q = await job_repo.list_jobs("tenant-a", status=ProcessingJobStatus.QUEUED)
    assert total_q == 1
    assert queued[0].status == ProcessingJobStatus.QUEUED
