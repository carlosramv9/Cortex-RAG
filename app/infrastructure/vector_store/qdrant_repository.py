"""Placeholder Qdrant ``VectorRepository``."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.vector_store.entities import SearchResult, VectorPoint
from app.domain.vector_store.repositories import VectorRepository


class QdrantVectorRepository(VectorRepository):
    """Vector storage/search backed by Qdrant (placeholder)."""

    def __init__(self, host: str, port: int, collection: str) -> None:
        self._host = host
        self._port = port
        self._collection = collection

    async def upsert(self, points: Sequence[VectorPoint]) -> None:
        raise NotImplementedError

    async def search(
        self,
        vector: Sequence[float],
        *,
        limit: int = 10,
    ) -> list[SearchResult]:
        raise NotImplementedError

    async def delete(self, ids: Sequence[str]) -> None:
        raise NotImplementedError
