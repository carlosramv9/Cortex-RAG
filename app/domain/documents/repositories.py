"""Port: DocumentRepository.

Persistence abstraction for the Document aggregate. Implemented by the
infrastructure layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.documents.entities import Document
from app.domain.documents.value_objects import DocumentId


class DocumentRepository(ABC):
    """Abstract repository for documents."""

    @abstractmethod
    async def add(self, document: Document) -> None:
        """Persist a new document."""
        raise NotImplementedError

    @abstractmethod
    async def get(self, document_id: DocumentId) -> Document | None:
        """Return a document by id, or None if absent."""
        raise NotImplementedError

    @abstractmethod
    async def list(self, *, limit: int, offset: int) -> list[Document]:
        """Return a page of documents."""
        raise NotImplementedError

    @abstractmethod
    async def update(self, document: Document) -> None:
        """Persist changes to an existing document."""
        raise NotImplementedError
