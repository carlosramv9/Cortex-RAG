"""HTTP schemas for the chat endpoint."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request of ``POST /chat``."""

    question: str = Field(min_length=1)
    conversation_id: UUID | None = None
    top_k: int = Field(default=5, gt=0, le=50)


class ChatSource(BaseModel):
    """A source chunk grounding the answer."""

    chunk_id: UUID
    score: float


class ChatResponse(BaseModel):
    """Response of ``POST /chat``."""

    answer: str
    conversation_id: UUID
    sources: list[ChatSource]
