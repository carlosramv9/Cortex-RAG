"""Logging ``EventPublisher``.

Emits domain events as structured logs. A real message bus (e.g. Kafka,
RabbitMQ, an outbox) can replace this later without touching the domain or the
use cases.
"""

from __future__ import annotations

from dataclasses import asdict

from app.domain.shared.event_publisher import EventPublisher
from app.domain.shared.events import DomainEvent
from app.shared.logging import get_logger

logger = get_logger(__name__)


class LoggingEventPublisher(EventPublisher):
    """Publishes events to the structured log."""

    async def publish(self, event: DomainEvent) -> None:
        logger.info(
            "domain_event",
            event_type=type(event).__name__,
            **{k: str(v) for k, v in asdict(event).items()},
        )
