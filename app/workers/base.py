"""Worker interface.

Workers depend only on the domain (ProcessingJob + JobType). They know nothing
about FastAPI, HTTP or the transport. A worker performs the actual work for a
job type. Concrete parsing/AI workers arrive in later phases.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.documents.jobs import JobType, ProcessingJob


class Worker(ABC):
    """Handles processing jobs of a single ``job_type``."""

    job_type: JobType

    @property
    def name(self) -> str:
        """Identifier recorded on the job (``worker_name``)."""
        return type(self).__name__

    @abstractmethod
    async def run(self, job: ProcessingJob) -> None:
        """Do the work. May call ``job.advance(phase, progress)`` to report
        intermediate phases. Raise to signal failure."""
        raise NotImplementedError
