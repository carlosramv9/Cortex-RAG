"""Use case: fetch a single knowledge document."""

from __future__ import annotations

from app.application.documents.dtos import DocumentView, GetDocumentInput
from app.domain.documents.repositories import DocumentRepository
from app.domain.shared.exceptions import EntityNotFoundError


class GetDocumentUseCase:
    """Return a document by id, scoped to its tenant."""

    def __init__(self, documents: DocumentRepository) -> None:
        self._documents = documents

    async def execute(self, data: GetDocumentInput) -> DocumentView:
        document = await self._documents.get(data.tenant_id, data.document_id)
        if document is None:
            raise EntityNotFoundError(f"Document {data.document_id} not found.")
        return DocumentView.from_document(document)
