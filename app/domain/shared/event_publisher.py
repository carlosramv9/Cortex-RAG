"""Port: EventPublisher.

Publishes domain events. In this phase a logging adapter is enough; a real
message bus can be plugged in later without touching the domain.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.shared.events import DomainEvent


class EventPublisher(ABC):
    """Abstract publisher of domain events."""

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """Publish a single domain event."""
        raise NotImplementedError
