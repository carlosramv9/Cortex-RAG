"""Composition root.

The ONLY place where the api layer is allowed to import from infrastructure.
Here domain ports are bound to concrete adapters and assembled into use cases,
then injected into routers via FastAPI ``Depends``. Endpoints never build their
own instances.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.chat.use_cases.answer_question import AnswerQuestionUseCase
from app.application.documents.use_cases.delete_document import DeleteDocumentUseCase
from app.application.documents.use_cases.get_document import GetDocumentUseCase
from app.application.documents.use_cases.list_documents import ListDocumentsUseCase
from app.application.documents.use_cases.process_document import (
    ProcessDocumentUseCase,
)
from app.application.documents.use_cases.update_document_metadata import (
    UpdateDocumentMetadataUseCase,
)
from app.application.documents.use_cases.upload_document import (
    UploadDocumentUseCase,
)
from app.application.processing.use_cases.create_processing_job import (
    CreateProcessingJobUseCase,
)
from app.application.processing.use_cases.get_processing_job import (
    GetProcessingJobUseCase,
)
from app.application.processing.use_cases.list_processing_jobs import (
    ListProcessingJobsUseCase,
)
from app.application.search.use_cases.semantic_search import SemanticSearchUseCase
from app.config.settings import (
    ProcessingSettings,
    Settings,
    UploadSettings,
    get_settings,
)
from app.domain.chunking.services import ChunkingStrategy
from app.domain.conversations.repositories import ConversationRepository
from app.domain.documents.repositories import (
    DocumentRepository,
    ProcessingJobRepository,
)
from app.domain.embeddings.providers import EmbeddingProvider
from app.domain.llm.providers import LLMProvider
from app.domain.parsers.providers import ParserProvider
from app.domain.shared.event_publisher import EventPublisher
from app.domain.storage.providers import StorageProvider
from app.domain.vector_store.repositories import VectorRepository
from app.infrastructure.chunking.recursive_chunker import RecursiveChunkingStrategy
from app.infrastructure.embeddings.ollama_provider import OllamaEmbeddingProvider
from app.infrastructure.events.logging_publisher import LoggingEventPublisher
from app.infrastructure.llm.ollama_provider import OllamaLLMProvider
from app.infrastructure.parsers.pymupdf_parser import PyMuPDFParserProvider
from app.infrastructure.persistence.sqlalchemy.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from app.infrastructure.persistence.sqlalchemy.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.infrastructure.persistence.sqlalchemy.repositories.processing_job_repository import (
    SqlAlchemyProcessingJobRepository,
)
from app.infrastructure.persistence.sqlalchemy.session import Database
from app.infrastructure.storage.local_storage import LocalStorageProvider
from app.infrastructure.vector_store.qdrant_repository import QdrantVectorRepository

# --- Configuration --------------------------------------------------------


def get_settings_dep() -> Settings:
    """Provide the settings singleton."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


def get_upload_settings(settings: SettingsDep) -> UploadSettings:
    """Provide the upload validation policy."""
    return settings.upload


UploadSettingsDep = Annotated[UploadSettings, Depends(get_upload_settings)]


def get_processing_settings(settings: SettingsDep) -> ProcessingSettings:
    """Provide the processing pipeline settings."""
    return settings.processing


ProcessingSettingsDep = Annotated[ProcessingSettings, Depends(get_processing_settings)]


# --- Request identity (multi-tenant) --------------------------------------


def get_tenant_id(x_tenant_id: str = Header(default="default")) -> str:
    """Resolve the tenant from the ``X-Tenant-Id`` header (defaults to 'default')."""
    return x_tenant_id


def get_uploaded_by(x_user_id: str | None = Header(default=None)) -> str | None:
    """Resolve the acting user from the ``X-User-Id`` header (optional)."""
    return x_user_id


TenantIdDep = Annotated[str, Depends(get_tenant_id)]
UploadedByDep = Annotated[str | None, Depends(get_uploaded_by)]


# --- Cross-cutting adapters -------------------------------------------------


def get_event_publisher() -> EventPublisher:
    return LoggingEventPublisher()


EventPublisherDep = Annotated[EventPublisher, Depends(get_event_publisher)]


# --- Database / session ----------------------------------------------------


def get_database(request: Request) -> Database:
    """Return the ``Database`` created at startup (app.state)."""
    return request.app.state.database  # type: ignore[no-any-return]


DatabaseDep = Annotated[Database, Depends(get_database)]


async def get_session(database: DatabaseDep) -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped async session."""
    async with database.session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- Domain ports -> concrete adapters ------------------------------------


def get_document_repository(session: SessionDep) -> DocumentRepository:
    return SqlAlchemyDocumentRepository(session)


def get_conversation_repository(session: SessionDep) -> ConversationRepository:
    return SqlAlchemyConversationRepository(session)


def get_processing_job_repository(session: SessionDep) -> ProcessingJobRepository:
    return SqlAlchemyProcessingJobRepository(session)


def get_storage_provider(settings: SettingsDep) -> StorageProvider:
    return LocalStorageProvider(settings.storage.local_path)


def get_embedding_provider(settings: SettingsDep) -> EmbeddingProvider:
    return OllamaEmbeddingProvider(settings.llm.base_url, settings.embedding.model)


def get_llm_provider(settings: SettingsDep) -> LLMProvider:
    return OllamaLLMProvider(settings.llm.base_url, settings.llm.model)


def get_vector_repository(settings: SettingsDep) -> VectorRepository:
    return QdrantVectorRepository(
        settings.vector.host,
        settings.vector.port,
        settings.vector.collection,
    )


def get_parser_provider() -> ParserProvider:
    return PyMuPDFParserProvider()


def get_chunking_strategy() -> ChunkingStrategy:
    return RecursiveChunkingStrategy()


DocumentRepositoryDep = Annotated[DocumentRepository, Depends(get_document_repository)]
ConversationRepositoryDep = Annotated[ConversationRepository, Depends(get_conversation_repository)]
ProcessingJobRepositoryDep = Annotated[
    ProcessingJobRepository, Depends(get_processing_job_repository)
]
StorageProviderDep = Annotated[StorageProvider, Depends(get_storage_provider)]
EmbeddingProviderDep = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
LLMProviderDep = Annotated[LLMProvider, Depends(get_llm_provider)]
VectorRepositoryDep = Annotated[VectorRepository, Depends(get_vector_repository)]
ParserProviderDep = Annotated[ParserProvider, Depends(get_parser_provider)]
ChunkingStrategyDep = Annotated[ChunkingStrategy, Depends(get_chunking_strategy)]


# --- Use cases -------------------------------------------------------------


def get_create_processing_job_use_case(
    jobs: ProcessingJobRepositoryDep,
    events: EventPublisherDep,
    processing_settings: ProcessingSettingsDep,
) -> CreateProcessingJobUseCase:
    return CreateProcessingJobUseCase(jobs, events, processing_settings)


CreateProcessingJobUseCaseDep = Annotated[
    CreateProcessingJobUseCase, Depends(get_create_processing_job_use_case)
]


def get_upload_document_use_case(
    documents: DocumentRepositoryDep,
    storage: StorageProviderDep,
    events: EventPublisherDep,
    upload_settings: UploadSettingsDep,
    create_job: CreateProcessingJobUseCaseDep,
) -> UploadDocumentUseCase:
    return UploadDocumentUseCase(documents, storage, events, upload_settings, create_job)


def get_list_processing_jobs_use_case(
    jobs: ProcessingJobRepositoryDep,
) -> ListProcessingJobsUseCase:
    return ListProcessingJobsUseCase(jobs)


def get_get_processing_job_use_case(
    jobs: ProcessingJobRepositoryDep,
) -> GetProcessingJobUseCase:
    return GetProcessingJobUseCase(jobs)


ListProcessingJobsUseCaseDep = Annotated[
    ListProcessingJobsUseCase, Depends(get_list_processing_jobs_use_case)
]
GetProcessingJobUseCaseDep = Annotated[
    GetProcessingJobUseCase, Depends(get_get_processing_job_use_case)
]


def get_get_document_use_case(
    documents: DocumentRepositoryDep,
) -> GetDocumentUseCase:
    return GetDocumentUseCase(documents)


def get_list_documents_use_case(
    documents: DocumentRepositoryDep,
) -> ListDocumentsUseCase:
    return ListDocumentsUseCase(documents)


def get_delete_document_use_case(
    documents: DocumentRepositoryDep,
    events: EventPublisherDep,
) -> DeleteDocumentUseCase:
    return DeleteDocumentUseCase(documents, events)


def get_update_document_metadata_use_case(
    documents: DocumentRepositoryDep,
    events: EventPublisherDep,
) -> UpdateDocumentMetadataUseCase:
    return UpdateDocumentMetadataUseCase(documents, events)


def get_process_document_use_case(
    documents: DocumentRepositoryDep,
    storage: StorageProviderDep,
    parser: ParserProviderDep,
    chunking: ChunkingStrategyDep,
    embeddings: EmbeddingProviderDep,
    vectors: VectorRepositoryDep,
) -> ProcessDocumentUseCase:
    return ProcessDocumentUseCase(documents, storage, parser, chunking, embeddings, vectors)


def get_answer_question_use_case(
    embeddings: EmbeddingProviderDep,
    vectors: VectorRepositoryDep,
    llm: LLMProviderDep,
    conversations: ConversationRepositoryDep,
) -> AnswerQuestionUseCase:
    return AnswerQuestionUseCase(embeddings, vectors, llm, conversations)


def get_semantic_search_use_case(
    embeddings: EmbeddingProviderDep,
    vectors: VectorRepositoryDep,
) -> SemanticSearchUseCase:
    return SemanticSearchUseCase(embeddings, vectors)


UploadDocumentUseCaseDep = Annotated[UploadDocumentUseCase, Depends(get_upload_document_use_case)]
GetDocumentUseCaseDep = Annotated[GetDocumentUseCase, Depends(get_get_document_use_case)]
ListDocumentsUseCaseDep = Annotated[ListDocumentsUseCase, Depends(get_list_documents_use_case)]
DeleteDocumentUseCaseDep = Annotated[DeleteDocumentUseCase, Depends(get_delete_document_use_case)]
UpdateDocumentMetadataUseCaseDep = Annotated[
    UpdateDocumentMetadataUseCase, Depends(get_update_document_metadata_use_case)
]
ProcessDocumentUseCaseDep = Annotated[
    ProcessDocumentUseCase, Depends(get_process_document_use_case)
]
AnswerQuestionUseCaseDep = Annotated[AnswerQuestionUseCase, Depends(get_answer_question_use_case)]
SemanticSearchUseCaseDep = Annotated[SemanticSearchUseCase, Depends(get_semantic_search_use_case)]
