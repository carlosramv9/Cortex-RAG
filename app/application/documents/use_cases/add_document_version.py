"""Use case: add a new immutable version to an existing document.

Prepared for the future ``POST /documents/{id}/versions`` endpoint (not wired
yet). Fully functional and tested. The new version becomes the active one; older
versions are preserved untouched.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.application.documents.dtos import (
    AddDocumentVersionInput,
    DocumentVersionView,
)
from app.application.documents.validation import validate_upload
from app.config.settings import UploadSettings
from app.domain.documents.entities import KnowledgeDocumentVersion
from app.domain.documents.events import DocumentVersionAdded
from app.domain.documents.repositories import DocumentRepository
from app.domain.documents.storage_policy import build_document_version_key
from app.domain.shared.event_publisher import EventPublisher
from app.domain.shared.exceptions import EntityNotFoundError
from app.domain.storage.providers import StorageProvider
from app.shared.constants import StorageProviderKind
from app.shared.hashing import sha256_hex


class AddDocumentVersionUseCase:
    """Store a new file and register it as the document's active version."""

    def __init__(
        self,
        documents: DocumentRepository,
        storage: StorageProvider,
        events: EventPublisher,
        upload_settings: UploadSettings,
    ) -> None:
        self._documents = documents
        self._storage = storage
        self._events = events
        self._settings = upload_settings

    async def execute(self, data: AddDocumentVersionInput) -> DocumentVersionView:
        document = await self._documents.get(data.tenant_id, data.document_id)
        if document is None:
            raise EntityNotFoundError(f"Document {data.document_id} not found.")

        extension = validate_upload(
            self._settings,
            original_filename=data.original_filename,
            content=data.content,
            content_type=data.content_type,
        )
        checksum = sha256_hex(data.content)

        existing_versions = await self._documents.list_versions(document.id)
        next_number = (
            max(v.version_number for v in existing_versions) + 1 if existing_versions else 1
        )

        version_id = uuid4()
        now = datetime.now(UTC)
        storage_key = build_document_version_key(
            tenant_id=data.tenant_id,
            document_id=document.id,
            version_id=version_id,
            extension=extension,
            uploaded_at=now,
        )
        await self._storage.save(storage_key, data.content)

        version = KnowledgeDocumentVersion(
            id=version_id,
            document_id=document.id,
            version_number=next_number,
            original_filename=data.original_filename,
            filename=f"{version_id}.{extension}",
            extension=extension,
            mime_type=data.content_type,
            size=len(data.content),
            checksum_sha256=checksum,
            storage_provider=StorageProviderKind.LOCAL,
            storage_path=storage_key,
            uploaded_by=data.uploaded_by,
            created_at=now,
        )

        document.current_version_id = version_id
        await self._documents.add_version(document, version)

        await self._events.publish(
            DocumentVersionAdded(
                document_id=document.id,
                tenant_id=document.tenant_id,
                version_id=version.id,
                version_number=version.version_number,
                checksum_sha256=checksum,
            )
        )
        return DocumentVersionView.from_entity(version)
