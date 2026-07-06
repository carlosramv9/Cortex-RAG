"""Ports: repositories for the documents context.

``DocumentRepository`` is fully used this phase. The others are prepared ports
for later phases (pages rendering, collections CRUD, async jobs).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.documents.collections import KnowledgeCollection
from app.domain.documents.entities import (
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    KnowledgePage,
)
from app.domain.documents.jobs import JobType, ProcessingJob
from app.shared.constants import ProcessingJobStatus


class DocumentRepository(ABC):
    """Persistence port for the ``KnowledgeDocument`` aggregate + its versions.

    Reads populate ``KnowledgeDocument.active_version`` with the version pointed
    at by ``current_version_id``.
    """

    @abstractmethod
    async def add(
        self, document: KnowledgeDocument, initial_version: KnowledgeDocumentVersion
    ) -> None:
        """Persist a new document together with its first version."""
        raise NotImplementedError

    @abstractmethod
    async def add_version(
        self, document: KnowledgeDocument, version: KnowledgeDocumentVersion
    ) -> None:
        """Append a new immutable version and update the document pointer."""
        raise NotImplementedError

    @abstractmethod
    async def get(self, tenant_id: str, document_id: UUID) -> KnowledgeDocument | None:
        """Return a non-deleted document (with active version) or None."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_checksum(
        self, tenant_id: str, checksum_sha256: str
    ) -> KnowledgeDocument | None:
        """Return the document owning a version with this checksum, or None.

        Used for duplicate detection across all versions of a tenant.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_documents(
        self,
        tenant_id: str,
        *,
        knowledge_space_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[KnowledgeDocument], int]:
        """Return a page of documents (with active version) and total count."""
        raise NotImplementedError

    @abstractmethod
    async def list_versions(self, document_id: UUID) -> list[KnowledgeDocumentVersion]:
        """Return the full version history, newest version_number first."""
        raise NotImplementedError

    @abstractmethod
    async def update(self, document: KnowledgeDocument) -> None:
        """Persist changes to mutable document fields (incl. soft delete).

        Versions are immutable and are never updated here.
        """
        raise NotImplementedError


class PageRepository(ABC):
    """Persistence port for ``KnowledgePage`` (prepared)."""

    @abstractmethod
    async def add_many(self, pages: list[KnowledgePage]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_document(self, document_id: UUID) -> list[KnowledgePage]:
        raise NotImplementedError


class CollectionRepository(ABC):
    """Persistence port for ``KnowledgeCollection`` (prepared)."""

    @abstractmethod
    async def add(self, collection: KnowledgeCollection) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get(self, tenant_id: str, collection_id: UUID) -> KnowledgeCollection | None:
        raise NotImplementedError


class ProcessingJobRepository(ABC):
    """Persistence port for ``ProcessingJob``."""

    @abstractmethod
    async def add(self, job: ProcessingJob) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get(self, tenant_id: str, job_id: UUID) -> ProcessingJob | None:
        raise NotImplementedError

    @abstractmethod
    async def update(self, job: ProcessingJob) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_active_by_type(
        self, document_id: UUID, job_type: JobType
    ) -> ProcessingJob | None:
        """Return a non-terminal job of this type for the document, or None.

        Enforces "only one active job per type".
        """
        raise NotImplementedError

    @abstractmethod
    async def list_jobs(
        self,
        tenant_id: str,
        *,
        document_id: UUID | None = None,
        status: ProcessingJobStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ProcessingJob], int]:
        raise NotImplementedError
