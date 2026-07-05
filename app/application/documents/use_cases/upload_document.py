"""Use case: upload a knowledge document.

Creates the permanent ``KnowledgeDocument`` identity together with its first
immutable ``KnowledgeDocumentVersion``. Flow: validate -> store bytes ->
checksum -> create document + version 1 -> persist -> publish
``DocumentUploaded``. Not processed here; status ``UPLOADED``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.application.documents.dtos import DocumentView, UploadDocumentInput
from app.application.documents.validation import validate_upload
from app.application.processing.dtos import CreateProcessingJobInput
from app.application.processing.use_cases.create_processing_job import (
    CreateProcessingJobUseCase,
)
from app.config.settings import UploadSettings
from app.domain.documents.entities import (
    KnowledgeDocument,
    KnowledgeDocumentVersion,
)
from app.domain.documents.events import DocumentUploaded
from app.domain.documents.jobs import JobType
from app.domain.documents.repositories import DocumentRepository
from app.domain.documents.source_type import SourceType
from app.domain.documents.storage_policy import build_document_version_key
from app.domain.shared.event_publisher import EventPublisher
from app.domain.shared.exceptions import ConflictError
from app.domain.storage.providers import StorageProvider
from app.shared.constants import DocumentStatus, StorageProviderKind
from app.shared.hashing import sha256_hex


class UploadDocumentUseCase:
    """Validate, store and register a new document with its first version."""

    def __init__(
        self,
        documents: DocumentRepository,
        storage: StorageProvider,
        events: EventPublisher,
        upload_settings: UploadSettings,
        create_job: CreateProcessingJobUseCase,
    ) -> None:
        self._documents = documents
        self._storage = storage
        self._events = events
        self._settings = upload_settings
        self._create_job = create_job

    async def execute(self, data: UploadDocumentInput) -> DocumentView:
        extension = validate_upload(
            self._settings,
            original_filename=data.original_filename,
            content=data.content,
            content_type=data.content_type,
        )
        checksum = sha256_hex(data.content)

        existing = await self._documents.get_by_checksum(data.tenant_id, checksum)
        if existing is not None:
            raise ConflictError(
                f"Document already exists with checksum {checksum} (id={existing.id})."
            )

        document_id = uuid4()
        version_id = uuid4()
        now = datetime.now(UTC)
        storage_key = build_document_version_key(
            tenant_id=data.tenant_id,
            document_id=document_id,
            version_id=version_id,
            extension=extension,
            uploaded_at=now,
        )
        await self._storage.save(storage_key, data.content)

        version = KnowledgeDocumentVersion(
            id=version_id,
            document_id=document_id,
            version_number=1,
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
        document = KnowledgeDocument(
            id=document_id,
            tenant_id=data.tenant_id,
            title=data.original_filename,
            source_type=SourceType.from_extension(extension),
            knowledge_space_id=data.knowledge_space_id,
            current_version_id=version_id,
            status=DocumentStatus.UPLOADED,
            created_by=data.uploaded_by,
            created_at=now,
            updated_at=now,
            active_version=version,
        )
        await self._documents.add(document, version)

        await self._events.publish(
            DocumentUploaded(
                document_id=document.id,
                tenant_id=document.tenant_id,
                version_id=version.id,
                version_number=version.version_number,
                checksum_sha256=checksum,
            )
        )

        # Register async processing (status QUEUED). Not executed in-request.
        await self._create_job.execute(
            CreateProcessingJobInput(
                tenant_id=document.tenant_id,
                document_id=document.id,
                version_id=version.id,
                job_type=JobType.DOCUMENT_INGESTION,
            )
        )
        return DocumentView.from_document(document)
