"""Tests for the worker executor and dispatcher."""

from __future__ import annotations

from app.domain.documents.events import (
    ProcessingJobCompleted,
    ProcessingJobFailed,
    ProcessingJobStarted,
)
from app.domain.documents.jobs import JobType, ProcessingJob
from app.infrastructure.persistence.sqlalchemy.repositories.processing_job_repository import (
    SqlAlchemyProcessingJobRepository,
)
from app.shared.constants import ProcessingJobStatus
from app.workers.base import Worker
from app.workers.executor import WorkerExecutor
from app.workers.registry import WorkerRegistry
from tests.factories import make_job
from tests.fakes import CapturingEventPublisher, InMemoryJobQueue


class _SuccessWorker(Worker):
    job_type = JobType.DOCUMENT_INGESTION

    async def run(self, job: ProcessingJob) -> None:
        job.advance(ProcessingJobStatus.CHUNKING, 50)


class _FailingWorker(Worker):
    job_type = JobType.DOCUMENT_INGESTION

    async def run(self, job: ProcessingJob) -> None:
        raise RuntimeError("kaboom")


def _registry(worker: Worker) -> WorkerRegistry:
    registry = WorkerRegistry()
    registry.register(worker)
    return registry


async def test_executor_completes_job(
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    job = make_job()
    await job_repo.add(job)
    events = CapturingEventPublisher()
    executor = WorkerExecutor(job_repo, events, _registry(_SuccessWorker()), InMemoryJobQueue())

    result = await executor.execute(job)

    assert result.status == ProcessingJobStatus.COMPLETED
    assert result.progress == 100
    types = [type(e) for e in events.events]
    assert ProcessingJobStarted in types
    assert ProcessingJobCompleted in types

    persisted = await job_repo.get(job.tenant_id, job.id)
    assert persisted is not None
    assert persisted.status == ProcessingJobStatus.COMPLETED
    assert persisted.worker_name == "_SuccessWorker"


async def test_executor_fails_without_worker(
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    job = make_job()
    await job_repo.add(job)
    events = CapturingEventPublisher()
    executor = WorkerExecutor(job_repo, events, WorkerRegistry(), InMemoryJobQueue())

    result = await executor.execute(job)

    assert result.status == ProcessingJobStatus.FAILED
    assert any(isinstance(e, ProcessingJobFailed) for e in events.events)


async def test_executor_fails_terminally_when_no_retries(
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    job = make_job()
    await job_repo.add(job)
    events = CapturingEventPublisher()
    executor = WorkerExecutor(
        job_repo, events, _registry(_FailingWorker()), InMemoryJobQueue(), max_retries=0
    )

    result = await executor.execute(job)

    assert result.status == ProcessingJobStatus.FAILED
    assert result.error_message == "kaboom"
    assert any(isinstance(e, ProcessingJobFailed) for e in events.events)


async def test_executor_requeues_then_fails(
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    job = make_job()
    await job_repo.add(job)
    events = CapturingEventPublisher()
    queue = InMemoryJobQueue()
    executor = WorkerExecutor(job_repo, events, _registry(_FailingWorker()), queue, max_retries=1)

    # First run: fails but is re-queued (one retry allowed) and re-enqueued.
    await executor.execute(job)
    assert job.status == ProcessingJobStatus.QUEUED
    assert job.retry_count == 1
    assert not any(isinstance(e, ProcessingJobFailed) for e in events.events)
    assert queue.enqueued == [(job.tenant_id, job.id)]

    # Second run: no retries left -> terminal FAILED + event, no further enqueue.
    await executor.execute(job)
    assert job.status == ProcessingJobStatus.FAILED
    assert any(isinstance(e, ProcessingJobFailed) for e in events.events)
    assert queue.enqueued == [(job.tenant_id, job.id)]
