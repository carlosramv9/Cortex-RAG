"""Port: JobQueue.

Notifies a worker that a processing job is ready to run. Postgres
(``ProcessingJobRepository``) remains the source of truth for job state; this
port is a push-based signal so a worker doesn't have to poll for QUEUED jobs.
Implemented by the infrastructure layer (e.g. a RabbitMQ adapter).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class JobQueue(ABC):
    """Abstract push notification queue for processing jobs."""

    @abstractmethod
    async def enqueue(self, *, tenant_id: str, job_id: UUID) -> None:
        """Signal that job ``job_id`` (owned by ``tenant_id``) is ready to run."""
        raise NotImplementedError
