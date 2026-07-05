"""Port: EmbeddingProvider.

Turns text into embeddings. Implemented by the infrastructure layer (e.g. an
Ollama/bge-m3 adapter).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.embeddings.entities import Embedding


class EmbeddingProvider(ABC):
    """Abstract embedding provider."""

    @abstractmethod
    async def embed_text(self, text: str) -> Embedding:
        """Embed a single piece of text."""
        raise NotImplementedError

    @abstractmethod
    async def embed_batch(self, texts: Sequence[str]) -> list[Embedding]:
        """Embed a batch of texts."""
        raise NotImplementedError
