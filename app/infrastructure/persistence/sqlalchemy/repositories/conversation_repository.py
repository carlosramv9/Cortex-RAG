"""SQLAlchemy implementation of ``ConversationRepository``.

Messages are immutable and ordered by an explicit ``seq`` (assigned here, not
relied upon from timestamps, which can tie). ``update`` persists only the
messages not yet stored — identified by id — so callers may pass the whole
in-memory ``Conversation`` (existing + newly appended messages) without
duplicating rows.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.conversations.entities import Conversation, ConversationId, Message
from app.domain.conversations.repositories import ConversationRepository
from app.domain.llm.entities import Role
from app.infrastructure.persistence.sqlalchemy.models import (
    ConversationMessageModel,
    ConversationModel,
)


def _message_to_model(message: Message, conversation_id: ConversationId, seq: int) -> ConversationMessageModel:
    return ConversationMessageModel(
        id=message.id,
        conversation_id=conversation_id.value,
        seq=seq,
        role=str(message.role),
        content=message.content,
    )


def _message_to_entity(model: ConversationMessageModel) -> Message:
    return Message(
        id=model.id,
        role=Role(model.role),
        content=model.content,
        created_at=model.created_at,
    )


class SqlAlchemyConversationRepository(ConversationRepository):
    """SQLAlchemy-backed conversation repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, conversation: Conversation) -> None:
        self._session.add(
            ConversationModel(id=conversation.id.value, tenant_id=conversation.tenant_id)
        )
        # Flushed separately: SQLAlchemy's insertmany batching for the
        # multi-row conversation_messages insert does not reliably order
        # itself after a single-row insert into a different (FK-parent)
        # table within the same flush.
        await self._session.flush()

        for seq, message in enumerate(conversation.messages):
            self._session.add(_message_to_model(message, conversation.id, seq))
        await self._session.flush()

    async def get(self, tenant_id: str, conversation_id: ConversationId) -> Conversation | None:
        model = await self._session.get(ConversationModel, conversation_id.value)
        if model is None or model.tenant_id != tenant_id:
            return None

        stmt = (
            select(ConversationMessageModel)
            .where(ConversationMessageModel.conversation_id == conversation_id.value)
            .order_by(ConversationMessageModel.seq)
        )
        messages = [_message_to_entity(m) for m in (await self._session.execute(stmt)).scalars()]
        return Conversation(
            id=conversation_id,
            tenant_id=model.tenant_id,
            messages=messages,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def update(self, conversation: Conversation) -> None:
        model = await self._session.get(ConversationModel, conversation.id.value)
        if model is None:
            return

        existing_stmt = select(ConversationMessageModel.id).where(
            ConversationMessageModel.conversation_id == conversation.id.value
        )
        existing_ids = {row for row in (await self._session.execute(existing_stmt)).scalars()}

        for seq, message in enumerate(conversation.messages):
            if message.id not in existing_ids:
                self._session.add(_message_to_model(message, conversation.id, seq))
        await self._session.flush()
