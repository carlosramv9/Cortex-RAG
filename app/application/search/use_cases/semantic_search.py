"""Use case: semantic search over indexed chunks."""

from __future__ import annotations

from app.application.search.dtos import SearchInput, SearchOutput
from app.domain.embeddings.providers import EmbeddingProvider
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
        """Execute the use case."""
        raise NotImplementedError
