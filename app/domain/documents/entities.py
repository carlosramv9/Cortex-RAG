"""Entities for the documents context.

Entities have identity and a lifecycle. Behavior is intentionally omitted in
this scaffolding phase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.documents.value_objects import (
    ChunkId,
    DocumentId,
    DocumentMetadata,
)
from app.shared.constants import DocumentStatus


@dataclass(slots=True)
class Chunk:
    """A contiguous piece of a document's text, unit of embedding/retrieval."""

    id: ChunkId
    document_id: DocumentId
    index: int
    content: str


@dataclass(slots=True)
class Document:
    """Aggregate root of the documents context."""

    id: DocumentId
    metadata: DocumentMetadata
    status: DocumentStatus = DocumentStatus.PENDING
    chunks: list[Chunk] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
