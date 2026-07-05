"""Use case: list knowledge documents for a tenant."""

from __future__ import annotations

from app.application.documents.dtos import (
    DocumentView,
    ListDocumentsInput,
    ListDocumentsOutput,
)
from app.domain.documents.repositories import DocumentRepository


class ListDocumentsUseCase:
    """Return a paged list of a tenant's documents."""

    def __init__(self, documents: DocumentRepository) -> None:
        self._documents = documents

    async def execute(self, data: ListDocumentsInput) -> ListDocumentsOutput:
        items, total = await self._documents.list_documents(
            data.tenant_id,
            knowledge_space_id=data.knowledge_space_id,
            limit=data.limit,
            offset=data.offset,
        )
        return ListDocumentsOutput(
            items=[DocumentView.from_document(d) for d in items],
            total=total,
            limit=data.limit,
            offset=data.offset,
        )
