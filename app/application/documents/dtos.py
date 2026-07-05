"""DTOs for the documents use cases.

``DocumentView`` is a flattened read model = document identity + the active
version's physical attributes, so existing API consumers keep the same fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.documents.entities import (
    KnowledgeDocument,
    KnowledgeDocumentVersion,
)
from app.domain.documents.metadata import KnowledgeMetadata
from app.domain.documents.source_type import SourceType
from app.shared.constants import DocumentStatus, StorageProviderKind


class DocumentVersionView(BaseModel):
    """Read model of a single immutable document version."""

    model_config = ConfigDict(from_attributes=True)

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
    page_count: int | None
    metadata: dict[str, Any]
    uploaded_by: str | None
    created_at: datetime | None

    @classmethod
    def from_entity(cls, version: KnowledgeDocumentVersion) -> DocumentVersionView:
        return cls.model_validate(version)


class DocumentView(BaseModel):
    """Flattened read model of a document (identity + active version)."""

    model_config = ConfigDict(from_attributes=True)

    # Identity
    id: UUID
    tenant_id: str
    knowledge_space_id: UUID | None
    title: str
    source_type: SourceType
    status: DocumentStatus
    metadata: KnowledgeMetadata
    created_by: str | None
    created_at: datetime | None
    updated_at: datetime | None
    # Active version
    current_version_id: UUID | None
    version_number: int | None
    original_filename: str | None
    filename: str | None
    extension: str | None
    mime_type: str | None
    size: int | None
    checksum_sha256: str | None
    storage_provider: StorageProviderKind | None
    storage_path: str | None
    page_count: int | None
    uploaded_by: str | None

    @classmethod
    def from_document(cls, document: KnowledgeDocument) -> DocumentView:
        v = document.active_version
        return cls(
            id=document.id,
            tenant_id=document.tenant_id,
            knowledge_space_id=document.knowledge_space_id,
            title=document.title,
            source_type=document.source_type,
            status=document.status,
            metadata=document.metadata,
            created_by=document.created_by,
            created_at=document.created_at,
            updated_at=document.updated_at,
            current_version_id=document.current_version_id,
            version_number=v.version_number if v else None,
            original_filename=v.original_filename if v else None,
            filename=v.filename if v else None,
            extension=v.extension if v else None,
            mime_type=v.mime_type if v else None,
            size=v.size if v else None,
            checksum_sha256=v.checksum_sha256 if v else None,
            storage_provider=v.storage_provider if v else None,
            storage_path=v.storage_path if v else None,
            page_count=v.page_count if v else None,
            uploaded_by=v.uploaded_by if v else None,
        )


class UploadDocumentInput(BaseModel):
    """Input to the upload-document use case (creates a document + version 1)."""

    tenant_id: str
    original_filename: str
    content: bytes
    content_type: str
    uploaded_by: str | None = None
    knowledge_space_id: UUID | None = None


class AddDocumentVersionInput(BaseModel):
    """Input to the add-version use case (new immutable version of a document)."""

    tenant_id: str
    document_id: UUID
    original_filename: str
    content: bytes
    content_type: str
    uploaded_by: str | None = None


class ListDocumentsInput(BaseModel):
    """Input to the list-documents use case."""

    tenant_id: str
    knowledge_space_id: UUID | None = None
    limit: int = Field(default=50, gt=0, le=200)
    offset: int = Field(default=0, ge=0)


class ListDocumentsOutput(BaseModel):
    """Paged list of documents."""

    items: list[DocumentView]
    total: int
    limit: int
    offset: int


class GetDocumentInput(BaseModel):
    """Input to the get/delete/list-versions use cases."""

    tenant_id: str
    document_id: UUID


class ListDocumentVersionsOutput(BaseModel):
    """Version history of a document (newest first)."""

    document_id: UUID
    versions: list[DocumentVersionView]


class UpdateDocumentMetadataInput(BaseModel):
    """Input to the update-metadata use case (document-level mutable fields)."""

    tenant_id: str
    document_id: UUID
    metadata: KnowledgeMetadata | None = None
    title: str | None = None
    knowledge_space_id: UUID | None = None
