"""Port: EmbeddingProvider.

Turns text into embeddings. Implemented by the infrastructure layer (e.g. a
local fastembed/bge-m3 adapter).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import StrEnum

from app.domain.embeddings.entities import Embedding


class EmbeddingTaskType(StrEnum):
    """Intent behind an embedding call.

    Some embedding models produce better vectors when the text is prefixed
    according to its role (indexed document vs. search query). Kept here as a
    neutral concept so the domain never speaks a provider's own vocabulary
    (e.g. Gemini's ``RETRIEVAL_DOCUMENT``/``RETRIEVAL_QUERY``); each adapter
    translates it internally, including doing nothing if its model needs no prefix.
    """

    DOCUMENT = "document"
    QUERY = "query"


class EmbeddingProvider(ABC):
    """Abstract embedding provider."""

    @abstractmethod
    async def embed_text(
        self, text: str, *, task_type: EmbeddingTaskType = EmbeddingTaskType.DOCUMENT
    ) -> Embedding:
        """Embed a single piece of text."""
        raise NotImplementedError

    @abstractmethod
    async def embed_batch(
        self,
        texts: Sequence[str],
        *,
        task_type: EmbeddingTaskType = EmbeddingTaskType.DOCUMENT,
    ) -> list[Embedding]:
        """Embed a batch of texts."""
        raise NotImplementedError
