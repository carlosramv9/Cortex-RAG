"""DTOs for the documents use cases.

Application-level data contracts, decoupled from both the HTTP schemas (api)
and the domain entities.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.shared.constants import DocumentStatus


class UploadDocumentInput(BaseModel):
    """Input to the upload-document use case."""

    filename: str
    content_type: str
    content: bytes


class UploadDocumentOutput(BaseModel):
    """Result of the upload-document use case."""

    document_id: UUID
    status: DocumentStatus


class ProcessDocumentInput(BaseModel):
    """Input to the process-document use case."""

    document_id: UUID


class ProcessDocumentOutput(BaseModel):
    """Result of the process-document use case."""

    document_id: UUID
    status: DocumentStatus
    chunk_count: int
