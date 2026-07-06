"""Tests for CreateProcessingJobUseCase (one active job per type)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.application.processing.dtos import CreateProcessingJobInput
from app.application.processing.use_cases.create_processing_job import (
    CreateProcessingJobUseCase,
)
from app.config.settings import ProcessingSettings
from app.domain.documents.events import ProcessingJobCreated
from app.domain.documents.jobs import JobType
from app.domain.shared.exceptions import ConflictError
from app.infrastructure.persistence.sqlalchemy.repositories.processing_job_repository import (
    SqlAlchemyProcessingJobRepository,
)
from app.shared.constants import ProcessingJobStatus
from tests.fakes import CapturingEventPublisher, InMemoryJobQueue


async def test_create_enqueues_and_emits_event(
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    events = CapturingEventPublisher()
    queue = InMemoryJobQueue()
    uc = CreateProcessingJobUseCase(job_repo, events, ProcessingSettings(), queue)

    view = await uc.execute(
        CreateProcessingJobInput(
            tenant_id="tenant-a",
            document_id=uuid4(),
            job_type=JobType.DOCUMENT_INGESTION,
        )
    )

    assert view.status == ProcessingJobStatus.QUEUED
    assert isinstance(events.events[0], ProcessingJobCreated)
    assert queue.enqueued == [("tenant-a", view.id)]


async def test_only_one_active_job_per_type(
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    uc = CreateProcessingJobUseCase(
        job_repo, CapturingEventPublisher(), ProcessingSettings(), InMemoryJobQueue()
    )
    doc_id = uuid4()
    data = CreateProcessingJobInput(
        tenant_id="tenant-a",
        document_id=doc_id,
        job_type=JobType.DOCUMENT_INGESTION,
    )
    await uc.execute(data)

    with pytest.raises(ConflictError):
        await uc.execute(data)


async def test_different_types_coexist(
    job_repo: SqlAlchemyProcessingJobRepository,
) -> None:
    uc = CreateProcessingJobUseCase(
        job_repo, CapturingEventPublisher(), ProcessingSettings(), InMemoryJobQueue()
    )
    doc_id = uuid4()
    await uc.execute(
        CreateProcessingJobInput(
            tenant_id="tenant-a",
            document_id=doc_id,
            job_type=JobType.DOCUMENT_INGESTION,
        )
    )
    # Same document, different type -> allowed.
    view = await uc.execute(
        CreateProcessingJobInput(
            tenant_id="tenant-a",
            document_id=doc_id,
            job_type=JobType.OCR,
        )
    )
    assert view.job_type == JobType.OCR
