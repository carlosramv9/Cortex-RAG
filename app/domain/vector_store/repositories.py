"""Port: VectorRepository.

Abstraction over the vector database (e.g. Qdrant). Implemented by the
infrastructure layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.vector_store.entities import SearchResult, VectorPoint


class VectorRepository(ABC):
    """Abstract vector repository."""

    @abstractmethod
    async def upsert(self, points: Sequence[VectorPoint]) -> None:
        """Insert or update vector points."""
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        vector: Sequence[float],
        *,
        limit: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[SearchResult]:
        """Return the nearest points to ``vector``.

        ``filters`` is an exact-match payload filter (e.g. ``{"tenant_id": "acme"}``);
        callers MUST scope searches by tenant to avoid cross-tenant leakage.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, ids: Sequence[str]) -> None:
        """Delete points by id."""
        raise NotImplementedError
