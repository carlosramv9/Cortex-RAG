"""SQLAlchemy implementation of ``DocumentRepository``.

Maps between ORM records and the pure domain entities. A document read always
populates ``KnowledgeDocument.active_version`` from ``current_version_id``.
Versions are immutable: this repository never updates or deletes version rows.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.documents.entities import (
    KnowledgeDocument,
    KnowledgeDocumentVersion,
)
from app.domain.documents.metadata import KnowledgeMetadata
from app.domain.documents.repositories import DocumentRepository
from app.domain.documents.source_type import SourceType
from app.infrastructure.persistence.sqlalchemy.models import (
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
)
from app.shared.constants import DocumentStatus, StorageProviderKind


def _version_to_entity(
    model: KnowledgeDocumentVersionModel,
) -> KnowledgeDocumentVersion:
    return KnowledgeDocumentVersion(
        id=model.id,
        document_id=model.document_id,
        version_number=model.version_number,
        original_filename=model.original_filename,
        filename=model.filename,
        extension=model.extension,
        mime_type=model.mime_type,
        size=model.size,
        checksum_sha256=model.checksum_sha256,
        storage_provider=StorageProviderKind(model.storage_provider),
        storage_path=model.storage_path,
        page_count=model.page_count,
        metadata=dict(model.meta),
        uploaded_by=model.uploaded_by,
        created_at=model.created_at,
    )


def _version_to_model(
    entity: KnowledgeDocumentVersion,
) -> KnowledgeDocumentVersionModel:
    return KnowledgeDocumentVersionModel(
        id=entity.id,
        document_id=entity.document_id,
        version_number=entity.version_number,
        original_filename=entity.original_filename,
        filename=entity.filename,
        extension=entity.extension,
        mime_type=entity.mime_type,
        size=entity.size,
        checksum_sha256=entity.checksum_sha256,
        storage_provider=str(entity.storage_provider),
        storage_path=entity.storage_path,
        page_count=entity.page_count,
        meta=dict(entity.metadata),
        uploaded_by=entity.uploaded_by,
    )


def _doc_to_entity(
    model: KnowledgeDocumentModel,
    active_version: KnowledgeDocumentVersion | None,
) -> KnowledgeDocument:
    return KnowledgeDocument(
        id=model.id,
        tenant_id=model.tenant_id,
        title=model.title,
        source_type=SourceType(model.source_type),
        knowledge_space_id=model.knowledge_space_id,
        current_version_id=model.current_version_id,
        status=DocumentStatus(model.status),
        metadata=KnowledgeMetadata.model_validate(model.meta),
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        active_version=active_version,
    )


def _doc_to_model(entity: KnowledgeDocument) -> KnowledgeDocumentModel:
    return KnowledgeDocumentModel(
        id=entity.id,
        tenant_id=entity.tenant_id,
        title=entity.title,
        source_type=str(entity.source_type),
        knowledge_space_id=entity.knowledge_space_id,
        current_version_id=entity.current_version_id,
        status=str(entity.status),
        meta=entity.metadata.model_dump(mode="json"),
        created_by=entity.created_by,
        deleted_at=entity.deleted_at,
    )


class SqlAlchemyDocumentRepository(DocumentRepository):
    """SQLAlchemy-backed document + versions repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _load_version(self, version_id: UUID | None) -> KnowledgeDocumentVersion | None:
        if version_id is None:
            return None
        model = await self._session.get(KnowledgeDocumentVersionModel, version_id)
        return _version_to_entity(model) if model is not None else None

    async def add(
        self, document: KnowledgeDocument, initial_version: KnowledgeDocumentVersion
    ) -> None:
        self._session.add(_version_to_model(initial_version))
        self._session.add(_doc_to_model(document))
        await self._session.flush()

    async def add_version(
        self, document: KnowledgeDocument, version: KnowledgeDocumentVersion
    ) -> None:
        self._session.add(_version_to_model(version))
        model = await self._session.get(KnowledgeDocumentModel, document.id)
        if model is not None:
            model.current_version_id = document.current_version_id
            model.status = str(document.status)
        await self._session.flush()

    async def get(self, tenant_id: str, document_id: UUID) -> KnowledgeDocument | None:
        stmt = select(KnowledgeDocumentModel).where(
            KnowledgeDocumentModel.id == document_id,
            KnowledgeDocumentModel.tenant_id == tenant_id,
            KnowledgeDocumentModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        version = await self._load_version(model.current_version_id)
        return _doc_to_entity(model, version)

    async def get_by_checksum(
        self, tenant_id: str, checksum_sha256: str
    ) -> KnowledgeDocument | None:
        stmt = (
            select(KnowledgeDocumentModel)
            .join(
                KnowledgeDocumentVersionModel,
                KnowledgeDocumentVersionModel.document_id == KnowledgeDocumentModel.id,
            )
            .where(
                KnowledgeDocumentVersionModel.checksum_sha256 == checksum_sha256,
                KnowledgeDocumentModel.tenant_id == tenant_id,
                KnowledgeDocumentModel.deleted_at.is_(None),
            )
        )
        model = (await self._session.execute(stmt)).scalars().first()
        if model is None:
            return None
        version = await self._load_version(model.current_version_id)
        return _doc_to_entity(model, version)

    async def list_documents(
        self,
        tenant_id: str,
        *,
        knowledge_space_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[KnowledgeDocument], int]:
        filters = [
            KnowledgeDocumentModel.tenant_id == tenant_id,
            KnowledgeDocumentModel.deleted_at.is_(None),
        ]
        if knowledge_space_id is not None:
            filters.append(KnowledgeDocumentModel.knowledge_space_id == knowledge_space_id)

        total_stmt = select(func.count()).select_from(KnowledgeDocumentModel).where(*filters)
        total = (await self._session.execute(total_stmt)).scalar_one()

        stmt = (
            select(KnowledgeDocumentModel)
            .where(*filters)
            .order_by(KnowledgeDocumentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        models = (await self._session.execute(stmt)).scalars().all()

        version_ids = [m.current_version_id for m in models if m.current_version_id]
        versions: dict[UUID, KnowledgeDocumentVersion] = {}
        if version_ids:
            vstmt = select(KnowledgeDocumentVersionModel).where(
                KnowledgeDocumentVersionModel.id.in_(version_ids)
            )
            for vm in (await self._session.execute(vstmt)).scalars().all():
                versions[vm.id] = _version_to_entity(vm)

        items = [
            _doc_to_entity(
                m,
                versions.get(m.current_version_id) if m.current_version_id else None,
            )
            for m in models
        ]
        return items, int(total)

    async def list_versions(self, document_id: UUID) -> list[KnowledgeDocumentVersion]:
        stmt = (
            select(KnowledgeDocumentVersionModel)
            .where(KnowledgeDocumentVersionModel.document_id == document_id)
            .order_by(KnowledgeDocumentVersionModel.version_number.desc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_version_to_entity(m) for m in models]

    async def update(self, document: KnowledgeDocument) -> None:
        model = await self._session.get(KnowledgeDocumentModel, document.id)
        if model is None or model.tenant_id != document.tenant_id:
            return
        model.title = document.title
        model.knowledge_space_id = document.knowledge_space_id
        model.status = str(document.status)
        model.meta = document.metadata.model_dump(mode="json")
        model.current_version_id = document.current_version_id
        model.deleted_at = document.deleted_at
        await self._session.flush()
