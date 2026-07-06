"""Use case: process a document (parse -> chunk -> embed -> index).

Turns the stored bytes of a document's active version into indexed, searchable
vectors. Chunk vector ids are derived deterministically from
``(document_id, chunk_index)`` so re-running this use case (e.g. a retried
job) upserts over the same points instead of duplicating them.
"""

from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.chunking.entities import ChunkingConfig
from app.domain.chunking.services import ChunkingStrategy
from app.domain.documents.repositories import DocumentRepository
from app.domain.embeddings.providers import EmbeddingProvider, EmbeddingTaskType
from app.domain.parsers.providers import ParserProvider
from app.domain.shared.exceptions import EntityNotFoundError, ValidationError
from app.domain.storage.providers import StorageProvider
from app.domain.vector_store.entities import VectorPoint
from app.domain.vector_store.repositories import VectorRepository
from app.shared.constants import DocumentStatus


def _chunk_vector_id(document_id: UUID, chunk_index: int) -> UUID:
    return uuid5(NAMESPACE_URL, f"knowledge-chunk:{document_id}:{chunk_index}")


class ProcessDocumentUseCase:
    """Turn a stored document into indexed, searchable chunks."""

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
        document = await self._documents.get(tenant_id, document_id)
        if document is None:
            raise EntityNotFoundError(f"Document {document_id} not found for tenant {tenant_id}.")
        version = document.active_version
        if version is None:
            raise ValidationError(f"Document {document_id} has no active version to process.")

        content = await self._storage.load(version.storage_path)
        parsed = await self._parser.parse(content, content_type=version.mime_type)
        chunks = self._chunking.split(parsed.text, config=ChunkingConfig())

        if chunks:
            vectors = await self._embeddings.embed_batch(
                [chunk.content for chunk in chunks], task_type=EmbeddingTaskType.DOCUMENT
            )
            points = [
                VectorPoint(
                    id=_chunk_vector_id(document.id, chunk.index),
                    vector=embedding.vector,
                    payload={
                        "tenant_id": tenant_id,
                        "document_id": str(document.id),
                        "chunk_index": chunk.index,
                        "content": chunk.content,
                    },
                )
                for chunk, embedding in zip(chunks, vectors, strict=True)
            ]
            await self._vectors.upsert(points)

        document.status = DocumentStatus.PROCESSED
        await self._documents.update(document)
