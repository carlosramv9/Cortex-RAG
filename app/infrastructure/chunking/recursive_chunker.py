"""Placeholder recursive ``ChunkingStrategy``."""

from __future__ import annotations

from app.domain.chunking.entities import ChunkingConfig, TextChunk
from app.domain.chunking.services import ChunkingStrategy


class RecursiveChunkingStrategy(ChunkingStrategy):
    """Splits text recursively by separators (placeholder)."""

    def split(self, text: str, *, config: ChunkingConfig) -> list[TextChunk]:
        raise NotImplementedError
