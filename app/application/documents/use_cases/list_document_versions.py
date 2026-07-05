"""Use case: list a document's version history.

Prepared for the future ``GET /documents/{id}/versions`` endpoint (not wired
yet). Returns versions newest-first.
"""

from __future__ import annotations

from app.application.documents.dtos import (
    DocumentVersionView,
    GetDocumentInput,
    ListDocumentVersionsOutput,
)
from app.domain.documents.repositories import DocumentRepository
from app.domain.shared.exceptions import EntityNotFoundError


class ListDocumentVersionsUseCase:
    """Return the immutable version history of a document."""

    def __init__(self, documents: DocumentRepository) -> None:
        self._documents = documents

    async def execute(self, data: GetDocumentInput) -> ListDocumentVersionsOutput:
        document = await self._documents.get(data.tenant_id, data.document_id)
        if document is None:
            raise EntityNotFoundError(f"Document {data.document_id} not found.")

        versions = await self._documents.list_versions(document.id)
        return ListDocumentVersionsOutput(
            document_id=document.id,
            versions=[DocumentVersionView.from_entity(v) for v in versions],
        )
