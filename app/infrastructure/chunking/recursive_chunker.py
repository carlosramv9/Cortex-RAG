"""Recursive ``ChunkingStrategy``.

Delegates the actual splitting to ``langchain-text-splitters`` (a small,
standalone package — not the full LangChain framework, which is deliberately
kept out of this codebase). Confined to this single infrastructure adapter:
the domain and application layers only ever see ``TextChunk``.
"""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.domain.chunking.entities import ChunkingConfig, TextChunk
from app.domain.chunking.services import ChunkingStrategy


class RecursiveChunkingStrategy(ChunkingStrategy):
    """Splits text recursively by separators, respecting size/overlap."""

    def split(self, text: str, *, config: ChunkingConfig) -> list[TextChunk]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )
        return [
            TextChunk(index=i, content=content)
            for i, content in enumerate(splitter.split_text(text))
        ]
