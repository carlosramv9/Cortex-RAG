"""DTOs for the chat use case."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class SourceReference(BaseModel):
    """A retrieved chunk used to ground the answer."""

    chunk_id: UUID
    score: float


class AnswerQuestionInput(BaseModel):
    """Input to the answer-question use case."""

    question: str
    conversation_id: UUID | None = None
    top_k: int = 5


class AnswerQuestionOutput(BaseModel):
    """Result of the answer-question use case."""

    answer: str
    conversation_id: UUID
    sources: list[SourceReference]
