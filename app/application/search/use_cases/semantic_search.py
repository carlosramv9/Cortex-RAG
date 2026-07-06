"""Use case: semantic search over indexed chunks."""

from __future__ import annotations

from app.application.search.dtos import SearchHit, SearchInput, SearchOutput
from app.domain.embeddings.providers import EmbeddingProvider, EmbeddingTaskType
from app.domain.vector_store.repositories import VectorRepository


class SemanticSearchUseCase:
    """Embed the query and return the nearest chunks."""

    def __init__(
        self,
        embeddings: EmbeddingProvider,
        vectors: VectorRepository,
    ) -> None:
        self._embeddings = embeddings
        self._vectors = vectors

    async def execute(self, data: SearchInput) -> SearchOutput:
        embedding = await self._embeddings.embed_text(
            data.query, task_type=EmbeddingTaskType.QUERY
        )
        results = await self._vectors.search(
            embedding.vector,
            limit=data.top_k,
            filters={"tenant_id": data.tenant_id},
        )
        hits = [
            SearchHit(
                chunk_id=result.id,
                score=result.score,
                content=str(result.payload.get("content", "")),
            )
            for result in results
        ]
        return SearchOutput(hits=hits)
