"""HTTP schemas for the documents endpoints.

Document representations reuse the application ``DocumentView`` / list output
(the api layer may depend on application). Only request bodies specific to HTTP
are defined here.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.domain.documents.metadata import KnowledgeMetadata


class UpdateDocumentRequest(BaseModel):
    """Request body of ``PATCH /documents/{id}`` (document-level mutable fields)."""

    metadata: KnowledgeMetadata | None = None
    title: str | None = None
    knowledge_space_id: UUID | None = None
