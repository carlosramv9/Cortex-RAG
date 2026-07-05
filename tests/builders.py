"""Builders assembling use cases for tests."""

from __future__ import annotations

from app.application.documents.use_cases.upload_document import UploadDocumentUseCase
from app.application.processing.use_cases.create_processing_job import (
    CreateProcessingJobUseCase,
)
from app.config.settings import ProcessingSettings, UploadSettings
from app.domain.documents.repositories import (
    DocumentRepository,
    ProcessingJobRepository,
)
from app.domain.shared.event_publisher import EventPublisher
from app.domain.storage.providers import StorageProvider
from tests.fakes import CapturingEventPublisher, InMemoryStorage


def build_upload_use_case(
    documents: DocumentRepository,
    jobs: ProcessingJobRepository,
    *,
    storage: StorageProvider | None = None,
    events: EventPublisher | None = None,
    upload_settings: UploadSettings | None = None,
) -> UploadDocumentUseCase:
    """Assemble an UploadDocumentUseCase wired with a create-job use case."""
    events = events or CapturingEventPublisher()
    create_job = CreateProcessingJobUseCase(jobs, events, ProcessingSettings())
    return UploadDocumentUseCase(
        documents,
        storage or InMemoryStorage(),
        events,
        upload_settings or UploadSettings(),
        create_job,
    )
