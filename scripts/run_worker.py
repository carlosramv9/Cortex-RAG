"""Worker process entrypoint.

Runs the job dispatcher out-of-band from the API (no FastAPI here). Executes one
batch of queued jobs and exits; wrap in a scheduler/loop or replace the
dispatcher with a Celery-backed one for production.

Run with: ``uv run python -m scripts.run_worker``
"""

from __future__ import annotations

import asyncio

from app.config.settings import get_settings
from app.infrastructure.events.logging_publisher import LoggingEventPublisher
from app.infrastructure.persistence.sqlalchemy.repositories.processing_job_repository import (
    SqlAlchemyProcessingJobRepository,
)
from app.infrastructure.persistence.sqlalchemy.session import get_database
from app.shared.logging import configure_logging, get_logger
from app.workers.composition import build_dispatcher


async def _run_once() -> int:
    settings = get_settings()
    configure_logging(level=settings.app.log_level, json_logs=settings.app.log_json)
    logger = get_logger("worker")

    database = get_database(settings)
    try:
        async with database.session() as session:
            jobs = SqlAlchemyProcessingJobRepository(session)
            dispatcher = build_dispatcher(jobs, LoggingEventPublisher(), settings.processing)
            dispatched = await dispatcher.dispatch_pending()
        logger.info("worker_batch_done", dispatched=dispatched)
        return dispatched
    finally:
        await database.dispose()


def main() -> None:
    asyncio.run(_run_once())


if __name__ == "__main__":
    main()
