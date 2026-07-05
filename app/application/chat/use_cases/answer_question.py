"""Use case: answer a question using only retrieved context (RAG)."""

from __future__ import annotations

from app.application.chat.dtos import AnswerQuestionInput, AnswerQuestionOutput
from app.domain.conversations.repositories import ConversationRepository
from app.domain.embeddings.providers import EmbeddingProvider
from app.domain.llm.providers import LLMProvider
from app.domain.vector_store.repositories import VectorRepository


class AnswerQuestionUseCase:
    """Retrieve relevant chunks and let the LLM answer grounded on them."""

    def __init__(
        self,
        embeddings: EmbeddingProvider,
        vectors: VectorRepository,
        llm: LLMProvider,
        conversations: ConversationRepository,
    ) -> None:
        self._embeddings = embeddings
        self._vectors = vectors
        self._llm = llm
        self._conversations = conversations

    async def execute(self, data: AnswerQuestionInput) -> AnswerQuestionOutput:
        """Execute the use case."""
        raise NotImplementedError
