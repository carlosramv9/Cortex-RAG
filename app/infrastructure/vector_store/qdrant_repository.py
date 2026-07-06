"""Qdrant ``VectorRepository``.

One ``AsyncQdrantClient`` per (host, port) is cached at module level, reused
across the per-request adapter instances built by the DI layer (opening a new
client/connection on every request would be wasteful). The collection is
created lazily on first use and then remembered as "ensured" for the process
lifetime — ``vector_size`` must match the configured embedding model's output
dimension, since Qdrant fixes it at creation time.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from qdrant_client import AsyncQdrantClient, models

from app.domain.vector_store.entities import SearchResult, VectorPoint
from app.domain.vector_store.repositories import VectorRepository

_client_cache: dict[tuple[str, int], AsyncQdrantClient] = {}
_ensured_collections: set[str] = set()


def _get_client(host: str, port: int) -> AsyncQdrantClient:
    key = (host, port)
    client = _client_cache.get(key)
    if client is None:
        client = AsyncQdrantClient(host=host, port=port)
        _client_cache[key] = client
    return client


class QdrantVectorRepository(VectorRepository):
    """Vector storage/search backed by Qdrant."""

    def __init__(self, host: str, port: int, collection: str, vector_size: int) -> None:
        self._client = _get_client(host, port)
        self._collection = collection
        self._vector_size = vector_size

    async def _ensure_collection(self) -> None:
        if self._collection in _ensured_collections:
            return
        if not await self._client.collection_exists(self._collection):
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=models.VectorParams(
                    size=self._vector_size, distance=models.Distance.COSINE
                ),
            )
        _ensured_collections.add(self._collection)

    async def upsert(self, points: Sequence[VectorPoint]) -> None:
        await self._ensure_collection()
        await self._client.upsert(
            collection_name=self._collection,
            points=[
                models.PointStruct(
                    id=str(point.id),
                    vector=list(point.vector),
                    payload=point.payload,
                )
                for point in points
            ],
        )

    async def search(
        self,
        vector: Sequence[float],
        *,
        limit: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[SearchResult]:
        await self._ensure_collection()
        query_filter = (
            models.Filter(
                must=[
                    models.FieldCondition(key=key, match=models.MatchValue(value=value))
                    for key, value in filters.items()
                ]
            )
            if filters
            else None
        )
        result = await self._client.query_points(
            collection_name=self._collection,
            query=list(vector),
            limit=limit,
            query_filter=query_filter,
        )
        return [
            SearchResult(id=UUID(str(hit.id)), score=hit.score, payload=hit.payload or {})
            for hit in result.points
        ]

    async def delete(self, ids: Sequence[str]) -> None:
        await self._ensure_collection()
        await self._client.delete(
            collection_name=self._collection,
            points_selector=models.PointIdsList(points=list(ids)),
        )
