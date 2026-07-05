"""JobDispatcher: pulls queued jobs and hands them to the executor.

This is the seam to replace with Celery (or any queue) later: swap this
in-process dispatcher for a broker-backed one without touching domain, workers
or the executor.
"""

from __future__ import annotations

from app.domain.documents.repositories import ProcessingJobRepository
from app.workers.executor import WorkerExecutor


class JobDispatcher:
    """In-process dispatcher: claims QUEUED jobs and executes them."""

    def __init__(
        self,
        jobs: ProcessingJobRepository,
        executor: WorkerExecutor,
        *,
        batch_size: int = 10,
    ) -> None:
        self._jobs = jobs
        self._executor = executor
        self._batch_size = batch_size

    async def dispatch_pending(self) -> int:
        """Execute one batch of queued jobs; return how many were dispatched."""
        pending = await self._jobs.claim_queued(limit=self._batch_size)
        for job in pending:
            await self._executor.execute(job)
        return len(pending)
