"""Port: ChunkingStrategy.

Strategy abstraction for splitting text into chunks (recursive, semantic, ...).
Implemented by the infrastructure layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.chunking.entities import ChunkingConfig, TextChunk


class ChunkingStrategy(ABC):
    """Abstract chunking strategy."""

    @abstractmethod
    def split(self, text: str, *, config: ChunkingConfig) -> list[TextChunk]:
        """Split ``text`` into chunks according to ``config``."""
        raise NotImplementedError
