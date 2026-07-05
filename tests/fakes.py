"""Test doubles for domain ports."""

from __future__ import annotations

from app.domain.shared.event_publisher import EventPublisher
from app.domain.shared.events import DomainEvent
from app.domain.storage.providers import StorageProvider


class InMemoryStorage(StorageProvider):
    """In-memory ``StorageProvider`` for tests."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def save(self, key: str, content: bytes) -> str:
        self.objects[key] = content
        return key

    async def load(self, key: str) -> bytes:
        return self.objects[key]

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)


class CapturingEventPublisher(EventPublisher):
    """Records published events for assertions."""

    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)
