"""Worker composition helpers.

Builds the registry / executor / dispatcher wiring. Kept out of the FastAPI
composition root: workers run in their own process (see scripts/run_worker.py).
"""

from __future__ import annotations

from app.config.settings import ProcessingSettings
from app.domain.documents.repositories import ProcessingJobRepository
from app.domain.shared.event_publisher import EventPublisher
from app.workers.dispatcher import JobDispatcher
from app.workers.executor import WorkerExecutor
from app.workers.ingestion import NoOpIngestionWorker
from app.workers.registry import WorkerRegistry


def build_worker_registry() -> WorkerRegistry:
    """Create a registry with all known workers registered."""
    registry = WorkerRegistry()
    registry.register(NoOpIngestionWorker())
    return registry


def build_dispatcher(
    jobs: ProcessingJobRepository,
    events: EventPublisher,
    settings: ProcessingSettings,
) -> JobDispatcher:
    """Assemble registry + executor + dispatcher."""
    executor = WorkerExecutor(
        jobs,
        events,
        build_worker_registry(),
        max_retries=settings.max_retries,
    )
    return JobDispatcher(jobs, executor, batch_size=settings.dispatch_batch_size)
