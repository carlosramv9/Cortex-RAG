"""Placeholder Ollama ``EmbeddingProvider`` (e.g. bge-m3)."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.embeddings.entities import Embedding
from app.domain.embeddings.providers import EmbeddingProvider


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Generates embeddings via a local Ollama server (placeholder)."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url
        self._model = model

    async def embed_text(self, text: str) -> Embedding:
        raise NotImplementedError

    async def embed_batch(self, texts: Sequence[str]) -> list[Embedding]:
        raise NotImplementedError
