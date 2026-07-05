"""Entities and value objects for the conversations context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.llm.entities import Role


@dataclass(frozen=True, slots=True)
class ConversationId:
    """Unique identifier of a conversation."""

    value: UUID


@dataclass(slots=True)
class Message:
    """A single message within a conversation."""

    role: Role
    content: str
    created_at: datetime | None = None


@dataclass(slots=True)
class Conversation:
    """Aggregate root: an ordered history of messages."""

    id: ConversationId
    messages: list[Message] = field(default_factory=list)
    created_at: datetime | None = None
