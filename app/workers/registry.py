"""WorkerRegistry: maps a JobType to its Worker."""

from __future__ import annotations

from app.domain.documents.jobs import JobType
from app.workers.base import Worker


class WorkerRegistry:
    """Registry of workers keyed by job type."""

    def __init__(self) -> None:
        self._workers: dict[JobType, Worker] = {}

    def register(self, worker: Worker) -> None:
        self._workers[worker.job_type] = worker

    def get(self, job_type: JobType) -> Worker | None:
        return self._workers.get(job_type)

    def __contains__(self, job_type: JobType) -> bool:
        return job_type in self._workers
