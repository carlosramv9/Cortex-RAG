"""Placeholder SQLAlchemy implementation of ``DocumentRepository``.

Wired but not yet implemented — every method raises ``NotImplementedError``.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.documents.entities import Document
from app.domain.documents.repositories import DocumentRepository
from app.domain.documents.value_objects import DocumentId


class SqlAlchemyDocumentRepository(DocumentRepository):
    """SQLAlchemy-backed document repository (placeholder)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: Document) -> None:
        raise NotImplementedError

    async def get(self, document_id: DocumentId) -> Document | None:
        raise NotImplementedError

    async def list(self, *, limit: int, offset: int) -> list[Document]:
        raise NotImplementedError

    async def update(self, document: Document) -> None:
        raise NotImplementedError
