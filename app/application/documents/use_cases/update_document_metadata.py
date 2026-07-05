"""Use case: update a document's metadata (and light mutable fields)."""

from __future__ import annotations

from app.application.documents.dtos import (
    DocumentView,
    UpdateDocumentMetadataInput,
)
from app.domain.documents.events import DocumentMetadataUpdated
from app.domain.documents.repositories import DocumentRepository
from app.domain.shared.event_publisher import EventPublisher
from app.domain.shared.exceptions import EntityNotFoundError


class UpdateDocumentMetadataUseCase:
    """Merge new metadata and update mutable fields of a document."""

    def __init__(self, documents: DocumentRepository, events: EventPublisher) -> None:
        self._documents = documents
        self._events = events

    async def execute(self, data: UpdateDocumentMetadataInput) -> DocumentView:
        document = await self._documents.get(data.tenant_id, data.document_id)
        if document is None:
            raise EntityNotFoundError(f"Document {data.document_id} not found.")

        if data.metadata is not None:
            document.metadata = data.metadata
        if data.title is not None:
            document.title = data.title
        if data.knowledge_space_id is not None:
            document.knowledge_space_id = data.knowledge_space_id

        await self._documents.update(document)

        await self._events.publish(
            DocumentMetadataUpdated(
                document_id=document.id,
                tenant_id=document.tenant_id,
                metadata=document.metadata.model_dump(mode="json"),
            )
        )
        return DocumentView.from_document(document)
