"""Entities/value objects for the vector store context."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class VectorPoint:
    """A stored point: an id, its vector, and arbitrary metadata payload."""

    id: UUID
    vector: tuple[float, ...]
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A single semantic-search hit."""

    id: UUID
    score: float
    payload: dict[str, object] = field(default_factory=dict)
