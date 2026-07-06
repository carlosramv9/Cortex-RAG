"""Worker process entrypoint.

Runs as a long-lived RabbitMQ consumer, out-of-band from the API (no FastAPI
here). Each message names a ``(tenant_id, job_id)``; the job itself is loaded
from Postgres (the source of truth for its state) and driven through its
lifecycle by ``WorkerExecutor``. No FastAPI, no HTTP.

Run with: ``uv run python -m scripts.run_worker``
"""

from __future__ import annotations

import asyncio
import json

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from app.application.documents.use_cases.process_document import ProcessDocumentUseCase
from app.config.settings import get_settings
from app.infrastructure.chunking.recursive_chunker import RecursiveChunkingStrategy
from app.infrastructure.embeddings.fastembed_provider import FastEmbedEmbeddingProvider
from app.infrastructure.events.logging_publisher import LoggingEventPublisher
from app.infrastructure.parsers.pymupdf_parser import PyMuPDFParserProvider
from app.infrastructure.persistence.sqlalchemy.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.infrastructure.persistence.sqlalchemy.repositories.processing_job_repository import (
    SqlAlchemyProcessingJobRepository,
)
from app.infrastructure.persistence.sqlalchemy.session import get_database
from app.infrastructure.queue.rabbitmq_job_queue import RabbitMQJobQueue
from app.infrastructure.storage.local_storage import LocalStorageProvider
from app.infrastructure.vector_store.qdrant_repository import QdrantVectorRepository
from app.shared.constants import ProcessingJobStatus
from app.shared.logging import configure_logging, get_logger
from app.workers.composition import build_worker_executor

logger = get_logger("worker")


async def _handle_message(message: AbstractIncomingMessage) -> None:
    settings = get_settings()
    payload = json.loads(message.body)
    tenant_id, job_id = payload["tenant_id"], payload["job_id"]

    database = get_database(settings)
    try:
        async with database.session() as session:
            jobs = SqlAlchemyProcessingJobRepository(session)
            documents = SqlAlchemyDocumentRepository(session)

            job = await jobs.get(tenant_id, job_id)
            if job is None:
                logger.warning("job_message_unknown", tenant_id=tenant_id, job_id=job_id)
                return
            if job.status != ProcessingJobStatus.QUEUED:
                # Redelivery of an already-started/terminal job (at-least-once
                # delivery): job.start() would raise: skip instead of retrying.
                logger.info(
                    "job_message_skipped",
                    tenant_id=tenant_id,
                    job_id=job_id,
                    status=job.status,
                )
                return

            process_document = ProcessDocumentUseCase(
                documents,
                LocalStorageProvider(settings.storage.local_path),
                PyMuPDFParserProvider(),
                RecursiveChunkingStrategy(),
                FastEmbedEmbeddingProvider(settings.embedding.model),
                QdrantVectorRepository(
                    settings.vector.host,
                    settings.vector.port,
                    settings.vector.collection,
                    settings.vector.vector_size,
                ),
            )
            executor = build_worker_executor(
                jobs,
                LoggingEventPublisher(),
                RabbitMQJobQueue(settings.rabbitmq.url, settings.rabbitmq.queue),
                settings.processing,
                process_document,
            )
            await executor.execute(job)
    finally:
        await database.dispose()


async def _run_forever() -> None:
    settings = get_settings()
    configure_logging(level=settings.app.log_level, json_logs=settings.app.log_json)
    logger.info("worker_starting", queue=settings.rabbitmq.queue)

    connection = await aio_pika.connect_robust(settings.rabbitmq.url)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=settings.rabbitmq.prefetch_count)
        queue = await channel.declare_queue(settings.rabbitmq.queue, durable=True)

        async with queue.iterator() as messages:
            async for message in messages:
                async with message.process(requeue=True):
                    await _handle_message(message)


def main() -> None:
    asyncio.run(_run_forever())


if __name__ == "__main__":
    main()
