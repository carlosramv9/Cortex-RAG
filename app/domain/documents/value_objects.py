"""Value objects for the documents context.

Value objects are immutable and compared by value. No behavior implemented yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DocumentId:
    """Unique identifier of a document."""

    value: UUID


@dataclass(frozen=True, slots=True)
class ChunkId:
    """Unique identifier of a chunk."""

    value: UUID


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    """Descriptive metadata extracted from or attached to a document."""

    filename: str
    content_type: str
    size_bytes: int
