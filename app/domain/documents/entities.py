"""Entities for the documents context.

Pure Python domain model for a Knowledge Engine. A knowledge document is a
*source of knowledge* (PDF today; Word/Excel/HTML/email/Notion/... later). The
model is deliberately format-agnostic.

Traceability chain (never broken):

    KnowledgeChunk -> KnowledgePage -> KnowledgeDocument -> original bytes

so a future answer can point back to the exact document, page, fragment, page
image and (later) text coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.documents.metadata import KnowledgeMetadata
from app.domain.documents.source_type import SourceType
from app.domain.documents.value_objects import BoundingBox
from app.shared.constants import DocumentStatus, StorageProviderKind


@dataclass(slots=True)
class KnowledgeDocumentVersion:
    """An immutable physical file uploaded for a document.

    A document may have many versions; each is a distinct stored file. Versions
    are never modified nor deleted. The original bytes live in storage; only a
    reference (``storage_provider`` + ``storage_path``) is kept.
    """

    id: UUID
    document_id: UUID
    version_number: int
    original_filename: str
    filename: str
    extension: str
    mime_type: str
    size: int
    checksum_sha256: str
    storage_provider: StorageProviderKind
    storage_path: str
    page_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    uploaded_by: str | None = None
    created_at: datetime | None = None


@dataclass(slots=True)
class KnowledgeDocument:
    """Aggregate root: the permanent logical identity of a knowledge document.

    Identity is stable across versions. Physical file attributes (filename,
    size, checksum, storage location, ...) belong to ``KnowledgeDocumentVersion``.
    ``current_version_id`` points at the active version.

    ``active_version`` is a runtime-only convenience the repository populates on
    read; it is not a persisted column.
    """

    id: UUID
    tenant_id: str
    title: str
    source_type: SourceType
    knowledge_space_id: UUID | None = None
    current_version_id: UUID | None = None
    status: DocumentStatus = DocumentStatus.UPLOADED
    metadata: KnowledgeMetadata = field(default_factory=KnowledgeMetadata)
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    active_version: KnowledgeDocumentVersion | None = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


@dataclass(slots=True)
class KnowledgePage:
    """A single page of a document.

    Page images are not generated yet; ``image_path`` is reserved for the
    rendered thumbnail (e.g. ``storage/pages/{document_id}/page_001.webp``).
    """

    id: UUID
    document_id: UUID
    page_number: int
    width: int | None = None
    height: int | None = None
    rotation: int = 0
    image_path: str | None = None
    extracted_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass(slots=True)
class KnowledgeChunk:
    """A retrievable fragment of a page (prepared, not yet fully implemented).

    Every chunk is anchored to a page and a character span, and optionally to a
    bounding box, so retrieval can reconstruct the exact on-page location. The
    whole architecture revolves around this entity, hence it exists from now.
    """

    id: UUID
    document_id: UUID
    page_id: UUID | None
    page_number: int
    char_start: int
    char_end: int
    content: str | None = None
    bbox: BoundingBox | None = None
    created_at: datetime | None = None
