"""Port: ConversationRepository."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.conversations.entities import Conversation, ConversationId


class ConversationRepository(ABC):
    """Abstract repository for conversations."""

    @abstractmethod
    async def add(self, conversation: Conversation) -> None:
        """Persist a new conversation."""
        raise NotImplementedError

    @abstractmethod
    async def get(self, tenant_id: str, conversation_id: ConversationId) -> Conversation | None:
        """Return a tenant-scoped conversation by id, or None if absent."""
        raise NotImplementedError

    @abstractmethod
    async def update(self, conversation: Conversation) -> None:
        """Persist changes to an existing conversation."""
        raise NotImplementedError
