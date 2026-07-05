"""Use case: soft-delete a knowledge document.

Soft delete only: the original bytes are never removed (traceability +
integrity). The record is marked ``DELETED`` with a ``deleted_at`` timestamp.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.documents.dtos import GetDocumentInput
from app.domain.documents.events import DocumentDeleted
from app.domain.documents.repositories import DocumentRepository
from app.domain.shared.event_publisher import EventPublisher
from app.domain.shared.exceptions import EntityNotFoundError
from app.shared.constants import DocumentStatus


class DeleteDocumentUseCase:
    """Mark a document as deleted without discarding its stored bytes."""

    def __init__(self, documents: DocumentRepository, events: EventPublisher) -> None:
        self._documents = documents
        self._events = events

    async def execute(self, data: GetDocumentInput) -> None:
        document = await self._documents.get(data.tenant_id, data.document_id)
        if document is None:
            raise EntityNotFoundError(f"Document {data.document_id} not found.")

        document.status = DocumentStatus.DELETED
        document.deleted_at = datetime.now(UTC)
        await self._documents.update(document)

        await self._events.publish(
            DocumentDeleted(
                document_id=document.id,
                tenant_id=document.tenant_id,
            )
        )
