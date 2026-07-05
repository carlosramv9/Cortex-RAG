"""HTTP schemas for the documents endpoints."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.shared.constants import DocumentStatus


class UploadDocumentResponse(BaseModel):
    """Response of ``POST /documents/upload``."""

    document_id: UUID
    status: DocumentStatus


class ProcessDocumentRequest(BaseModel):
    """Request of ``POST /documents/process``."""

    document_id: UUID


class ProcessDocumentResponse(BaseModel):
    """Response of ``POST /documents/process``."""

    document_id: UUID
    status: DocumentStatus
    chunk_count: int
