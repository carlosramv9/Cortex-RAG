"""Search router (scaffolding — returns 501)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.schemas.search import SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(payload: SearchRequest) -> SearchResponse:
    """Semantic search over indexed chunks."""
    raise NotImplementedError
