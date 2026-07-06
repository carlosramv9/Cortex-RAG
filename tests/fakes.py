"""Test doubles for domain ports."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.domain.conversations.entities import Conversation, ConversationId
from app.domain.conversations.repositories import ConversationRepository
from app.domain.documents.job_queue import JobQueue
from app.domain.embeddings.entities import Embedding
from app.domain.embeddings.providers import EmbeddingProvider, EmbeddingTaskType
from app.domain.llm.entities import LLMCompletion, LLMMessage
from app.domain.llm.providers import LLMProvider
from app.domain.shared.event_publisher import EventPublisher
from app.domain.shared.events import DomainEvent
from app.domain.storage.providers import StorageProvider
from app.domain.vector_store.entities import SearchResult, VectorPoint
from app.domain.vector_store.repositories import VectorRepository


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


class InMemoryJobQueue(JobQueue):
    """Records enqueued (tenant_id, job_id) pairs for assertions."""

    def __init__(self) -> None:
        self.enqueued: list[tuple[str, UUID]] = []

    async def enqueue(self, *, tenant_id: str, job_id: UUID) -> None:
        self.enqueued.append((tenant_id, job_id))


class FakeEmbeddingProvider(EmbeddingProvider):
    """Returns a fixed embedding regardless of input; records task types used."""

    def __init__(self) -> None:
        self.calls: list[EmbeddingTaskType] = []

    async def embed_text(
        self, text: str, *, task_type: EmbeddingTaskType = EmbeddingTaskType.DOCUMENT
    ) -> Embedding:
        self.calls.append(task_type)
        return Embedding(vector=(1.0, 0.0), model="fake")

    async def embed_batch(
        self,
        texts: Sequence[str],
        *,
        task_type: EmbeddingTaskType = EmbeddingTaskType.DOCUMENT,
    ) -> list[Embedding]:
        self.calls.append(task_type)
        return [Embedding(vector=(1.0, 0.0), model="fake") for _ in texts]


class InMemoryVectorRepository(VectorRepository):
    """In-memory ``VectorRepository`` supporting exact-match payload filters."""

    def __init__(self) -> None:
        self.points: dict[UUID, VectorPoint] = {}

    async def upsert(self, points: Sequence[VectorPoint]) -> None:
        for point in points:
            self.points[point.id] = point

    async def search(
        self,
        vector: Sequence[float],
        *,
        limit: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[SearchResult]:
        items = list(self.points.values())
        if filters:
            items = [
                p for p in items if all(p.payload.get(k) == v for k, v in filters.items())
            ]
        return [SearchResult(id=p.id, score=1.0, payload=p.payload) for p in items[:limit]]

    async def delete(self, ids: Sequence[str]) -> None:
        for raw_id in ids:
            self.points.pop(UUID(raw_id), None)


class FakeLLMProvider(LLMProvider):
    """Returns a fixed answer; records the messages it was called with."""

    def __init__(self, response: str = "fake answer") -> None:
        self.response = response
        self.received: list[LLMMessage] = []

    async def complete(self, messages: Sequence[LLMMessage]) -> LLMCompletion:
        self.received = list(messages)
        return LLMCompletion(content=self.response, model="fake")


class InMemoryConversationRepository(ConversationRepository):
    """In-memory, tenant-scoped ``ConversationRepository`` for tests."""

    def __init__(self) -> None:
        self.store: dict[UUID, Conversation] = {}

    async def add(self, conversation: Conversation) -> None:
        self.store[conversation.id.value] = conversation

    async def get(self, tenant_id: str, conversation_id: ConversationId) -> Conversation | None:
        conversation = self.store.get(conversation_id.value)
        if conversation is None or conversation.tenant_id != tenant_id:
            return None
        return conversation

    async def update(self, conversation: Conversation) -> None:
        self.store[conversation.id.value] = conversation
