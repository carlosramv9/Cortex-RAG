"""Value objects for the chunking context."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextChunk:
    """A piece of text produced by a chunking strategy."""

    index: int
    content: str


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    """Parameters controlling how text is chunked."""

    chunk_size: int = 1000
    chunk_overlap: int = 200
