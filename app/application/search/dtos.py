"""DTOs for the semantic-search use case."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class SearchInput(BaseModel):
    """Input to the semantic-search use case."""

    query: str
    top_k: int = 10


class SearchHit(BaseModel):
    """A single search result."""

    chunk_id: UUID
    score: float
    content: str


class SearchOutput(BaseModel):
    """Result of the semantic-search use case."""

    hits: list[SearchHit]
