"""Worker composition helpers.

Builds the registry / executor wiring. Kept out of the FastAPI composition
root: workers run in their own process (see scripts/run_worker.py).
"""

from __future__ import annotations

from app.application.documents.use_cases.process_document import ProcessDocumentUseCase
from app.config.settings import ProcessingSettings
from app.domain.documents.job_queue import JobQueue
from app.domain.documents.repositories import ProcessingJobRepository
from app.domain.shared.event_publisher import EventPublisher
from app.workers.executor import WorkerExecutor
from app.workers.ingestion import IngestionWorker
from app.workers.registry import WorkerRegistry


def build_worker_registry(process_document: ProcessDocumentUseCase) -> WorkerRegistry:
    """Create a registry with all known workers registered."""
    registry = WorkerRegistry()
    registry.register(IngestionWorker(process_document))
    return registry


def build_worker_executor(
    jobs: ProcessingJobRepository,
    events: EventPublisher,
    queue: JobQueue,
    settings: ProcessingSettings,
    process_document: ProcessDocumentUseCase,
) -> WorkerExecutor:
    """Assemble registry + executor for a single job's lifecycle."""
    return WorkerExecutor(
        jobs,
        events,
        build_worker_registry(process_document),
        queue,
        max_retries=settings.max_retries,
    )
