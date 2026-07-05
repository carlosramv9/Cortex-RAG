"""Use case: upload a document.

Dependencies are injected as domain ports. Business logic is intentionally not
implemented in this scaffolding phase.
"""

from __future__ import annotations

from app.application.documents.dtos import (
    UploadDocumentInput,
    UploadDocumentOutput,
)
from app.domain.documents.repositories import DocumentRepository
from app.domain.storage.providers import StorageProvider


class UploadDocumentUseCase:
    """Persist a raw document and register it for later processing."""

    def __init__(
        self,
        documents: DocumentRepository,
        storage: StorageProvider,
    ) -> None:
        self._documents = documents
        self._storage = storage

    async def execute(self, data: UploadDocumentInput) -> UploadDocumentOutput:
        """Execute the use case."""
        raise NotImplementedError
