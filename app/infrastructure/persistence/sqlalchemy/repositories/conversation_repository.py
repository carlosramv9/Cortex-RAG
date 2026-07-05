"""Placeholder SQLAlchemy implementation of ``ConversationRepository``."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.conversations.entities import Conversation, ConversationId
from app.domain.conversations.repositories import ConversationRepository


class SqlAlchemyConversationRepository(ConversationRepository):
    """SQLAlchemy-backed conversation repository (placeholder)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, conversation: Conversation) -> None:
        raise NotImplementedError

    async def get(self, conversation_id: ConversationId) -> Conversation | None:
        raise NotImplementedError

    async def update(self, conversation: Conversation) -> None:
        raise NotImplementedError
