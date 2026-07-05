"""Use case: process a document (parse -> render pages -> chunk -> embed -> index).

Reserved for a later phase. Dependencies are declared as domain ports; the
orchestration is not implemented yet.
"""

from __future__ import annotations

from uuid import UUID

from app.domain.chunking.services import ChunkingStrategy
from app.domain.documents.repositories import DocumentRepository
from app.domain.embeddings.providers import EmbeddingProvider
from app.domain.parsers.providers import ParserProvider
from app.domain.storage.providers import StorageProvider
from app.domain.vector_store.repositories import VectorRepository


class ProcessDocumentUseCase:
    """Turn a stored document into indexed, searchable chunks (not implemented)."""

    def __init__(
        self,
        documents: DocumentRepository,
        storage: StorageProvider,
        parser: ParserProvider,
        chunking: ChunkingStrategy,
        embeddings: EmbeddingProvider,
        vectors: VectorRepository,
    ) -> None:
        self._documents = documents
        self._storage = storage
        self._parser = parser
        self._chunking = chunking
        self._embeddings = embeddings
        self._vectors = vectors

    async def execute(self, tenant_id: str, document_id: UUID) -> None:
        """Execute the use case."""
        raise NotImplementedError
