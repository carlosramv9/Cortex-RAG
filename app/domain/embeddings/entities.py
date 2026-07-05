"""Value objects for the embeddings context."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Embedding:
    """A dense vector representation of a piece of text."""

    vector: tuple[float, ...]
    model: str

    @property
    def dimension(self) -> int:
        return len(self.vector)
