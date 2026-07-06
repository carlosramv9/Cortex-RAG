"""RabbitMQ ``JobQueue``.

Publishes a small ``{tenant_id, job_id}`` message to a durable queue; the
worker process (``scripts/run_worker.py``) consumes it and fetches the full
``ProcessingJob`` from Postgres before executing it. The connection/channel is
cached at module level (keyed by URL) and the queue declaration is remembered
as done, mirroring the caching pattern used by the other per-request adapters
(``fastembed_provider.py``, ``qdrant_repository.py``) — DI builds a new
``RabbitMQJobQueue`` instance per request, but they all share one AMQP
connection.
"""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

import aio_pika
from aio_pika.abc import AbstractChannel

from app.domain.documents.job_queue import JobQueue

_channel_cache: dict[str, AbstractChannel] = {}
_declared_queues: set[str] = set()
_lock = asyncio.Lock()


async def _get_channel(url: str) -> AbstractChannel:
    channel = _channel_cache.get(url)
    if channel is not None and not channel.is_closed:
        return channel
    async with _lock:
        channel = _channel_cache.get(url)
        if channel is not None and not channel.is_closed:
            return channel
        connection = await aio_pika.connect_robust(url)
        channel = await connection.channel()
        _channel_cache[url] = channel
        return channel


async def _ensure_queue(channel: AbstractChannel, queue_name: str) -> None:
    key = f"{id(channel)}:{queue_name}"
    if key in _declared_queues:
        return
    await channel.declare_queue(queue_name, durable=True)
    _declared_queues.add(key)


class RabbitMQJobQueue(JobQueue):
    """Push-based processing-job queue backed by RabbitMQ."""

    def __init__(self, url: str, queue_name: str) -> None:
        self._url = url
        self._queue_name = queue_name

    async def enqueue(self, *, tenant_id: str, job_id: UUID) -> None:
        channel = await _get_channel(self._url)
        await _ensure_queue(channel, self._queue_name)
        body = json.dumps({"tenant_id": tenant_id, "job_id": str(job_id)}).encode()
        await channel.default_exchange.publish(
            aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key=self._queue_name,
        )
