"""Domain events for the documents context."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.documents.value_objects import DocumentId
from app.domain.shared.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentUploaded(DomainEvent):
    """Emitted when a document has been uploaded and persisted."""

    document_id: DocumentId


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentProcessed(DomainEvent):
    """Emitted when a document has been parsed, chunked and embedded."""

    document_id: DocumentId
    chunk_count: int
