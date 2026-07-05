"""HTTP schemas for the search endpoint."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Request of ``POST /search``."""

    query: str = Field(min_length=1)
    top_k: int = Field(default=10, gt=0, le=100)


class SearchHitResponse(BaseModel):
    """A single search hit."""

    chunk_id: UUID
    score: float
    content: str


class SearchResponse(BaseModel):
    """Response of ``POST /search``."""

    hits: list[SearchHitResponse]
