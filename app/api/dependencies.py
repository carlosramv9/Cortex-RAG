"""Composition root.

The ONLY place where the api layer is allowed to import from infrastructure.
Here domain ports are bound to concrete adapters and assembled into use cases,
then injected into routers via FastAPI ``Depends``. Endpoints never build their
own instances.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.chat.use_cases.answer_question import AnswerQuestionUseCase
from app.application.documents.use_cases.process_document import (
    ProcessDocumentUseCase,
)
from app.application.documents.use_cases.upload_document import (
    UploadDocumentUseCase,
)
from app.application.search.use_cases.semantic_search import SemanticSearchUseCase
from app.config.settings import Settings, get_settings
from app.domain.chunking.services import ChunkingStrategy
from app.domain.conversations.repositories import ConversationRepository
from app.domain.documents.repositories import DocumentRepository
from app.domain.embeddings.providers import EmbeddingProvider
from app.domain.llm.providers import LLMProvider
from app.domain.parsers.providers import ParserProvider
from app.domain.storage.providers import StorageProvider
from app.domain.vector_store.repositories import VectorRepository
from app.infrastructure.chunking.recursive_chunker import RecursiveChunkingStrategy
from app.infrastructure.embeddings.ollama_provider import OllamaEmbeddingProvider
from app.infrastructure.llm.ollama_provider import OllamaLLMProvider
from app.infrastructure.parsers.pymupdf_parser import PyMuPDFParserProvider
from app.infrastructure.persistence.sqlalchemy.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from app.infrastructure.persistence.sqlalchemy.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.infrastructure.persistence.sqlalchemy.session import Database
from app.infrastructure.storage.local_storage import LocalStorageProvider
from app.infrastructure.vector_store.qdrant_repository import QdrantVectorRepository

# --- Configuration --------------------------------------------------------


def get_settings_dep() -> Settings:
    """Provide the settings singleton."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


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
StorageProviderDep = Annotated[StorageProvider, Depends(get_storage_provider)]
EmbeddingProviderDep = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
LLMProviderDep = Annotated[LLMProvider, Depends(get_llm_provider)]
VectorRepositoryDep = Annotated[VectorRepository, Depends(get_vector_repository)]
ParserProviderDep = Annotated[ParserProvider, Depends(get_parser_provider)]
ChunkingStrategyDep = Annotated[ChunkingStrategy, Depends(get_chunking_strategy)]


# --- Use cases -------------------------------------------------------------


def get_upload_document_use_case(
    documents: DocumentRepositoryDep,
    storage: StorageProviderDep,
) -> UploadDocumentUseCase:
    return UploadDocumentUseCase(documents, storage)


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
ProcessDocumentUseCaseDep = Annotated[
    ProcessDocumentUseCase, Depends(get_process_document_use_case)
]
AnswerQuestionUseCaseDep = Annotated[AnswerQuestionUseCase, Depends(get_answer_question_use_case)]
SemanticSearchUseCaseDep = Annotated[SemanticSearchUseCase, Depends(get_semantic_search_use_case)]
