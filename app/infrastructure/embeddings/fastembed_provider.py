"""FastEmbed ``EmbeddingProvider``.

Runs embeddings in-process via ONNX (fastembed), no external server, no API
key. ``TextEmbedding`` loading is expensive (reads the model file), so loaded
instances are cached per model name at module level: many
``FastEmbedEmbeddingProvider`` objects (one per request, per the DI pattern)
share the same underlying model.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from fastembed import TextEmbedding

from app.domain.embeddings.entities import Embedding
from app.domain.embeddings.providers import EmbeddingProvider, EmbeddingTaskType

_model_cache: dict[str, TextEmbedding] = {}


def _get_model(model_name: str) -> TextEmbedding:
    model = _model_cache.get(model_name)
    if model is None:
        model = TextEmbedding(model_name=model_name)
        _model_cache[model_name] = model
    return model


class FastEmbedEmbeddingProvider(EmbeddingProvider):
    """Generates embeddings locally via fastembed (e.g. BAAI/bge-m3)."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name

    async def embed_text(
        self, text: str, *, task_type: EmbeddingTaskType = EmbeddingTaskType.DOCUMENT
    ) -> Embedding:
        embeddings = await self.embed_batch([text], task_type=task_type)
        return embeddings[0]

    async def embed_batch(
        self,
        texts: Sequence[str],
        *,
        task_type: EmbeddingTaskType = EmbeddingTaskType.DOCUMENT,
    ) -> list[Embedding]:
        model = _get_model(self._model_name)

        def _run() -> list[list[float]]:
            embed_fn = (
                model.passage_embed if task_type == EmbeddingTaskType.DOCUMENT else model.query_embed
            )
            return [vector.tolist() for vector in embed_fn(list(texts))]

        vectors = await asyncio.to_thread(_run)
        return [Embedding(vector=tuple(v), model=self._model_name) for v in vectors]
