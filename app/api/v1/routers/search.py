"""Search router — semantic search over indexed chunks."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import SemanticSearchUseCaseDep, TenantIdDep
from app.api.v1.schemas.search import SearchHitResponse, SearchRequest, SearchResponse
from app.application.search.dtos import SearchInput

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(
    payload: SearchRequest,
    use_case: SemanticSearchUseCaseDep,
    tenant_id: TenantIdDep,
) -> SearchResponse:
    """Semantic search over indexed chunks."""
    output = await use_case.execute(
        SearchInput(tenant_id=tenant_id, query=payload.query, top_k=payload.top_k)
    )
    return SearchResponse(
        hits=[
            SearchHitResponse(chunk_id=h.chunk_id, score=h.score, content=h.content)
            for h in output.hits
        ]
    )
