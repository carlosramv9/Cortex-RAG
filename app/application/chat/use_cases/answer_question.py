"""Use case: answer a question using only retrieved context (RAG)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.application.chat.dtos import AnswerQuestionInput, AnswerQuestionOutput, SourceReference
from app.config.settings import ChatSettings
from app.domain.conversations.entities import Conversation, ConversationId, Message
from app.domain.conversations.repositories import ConversationRepository
from app.domain.embeddings.providers import EmbeddingProvider, EmbeddingTaskType
from app.domain.llm.entities import LLMMessage, Role
from app.domain.llm.providers import LLMProvider
from app.domain.shared.exceptions import EntityNotFoundError
from app.domain.vector_store.repositories import VectorRepository


class AnswerQuestionUseCase:
    """Retrieve relevant chunks and let the LLM answer grounded on them."""

    def __init__(
        self,
        embeddings: EmbeddingProvider,
        vectors: VectorRepository,
        llm: LLMProvider,
        conversations: ConversationRepository,
        settings: ChatSettings,
    ) -> None:
        self._embeddings = embeddings
        self._vectors = vectors
        self._llm = llm
        self._conversations = conversations
        self._settings = settings

    async def execute(self, data: AnswerQuestionInput) -> AnswerQuestionOutput:
        embedding = await self._embeddings.embed_text(
            data.question, task_type=EmbeddingTaskType.QUERY
        )
        results = await self._vectors.search(
            embedding.vector,
            limit=data.top_k,
            filters={"tenant_id": data.tenant_id},
        )
        context = "\n\n".join(str(r.payload.get("content", "")) for r in results)

        conversation = await self._load_or_create_conversation(data)

        history = conversation.messages[-self._settings.history_window :]
        llm_messages = [
            LLMMessage(
                role=Role.SYSTEM,
                content=f"{self._settings.system_prompt}\n\nContext:\n{context}",
            ),
            *(LLMMessage(role=m.role, content=m.content) for m in history),
            LLMMessage(role=Role.USER, content=data.question),
        ]
        completion = await self._llm.complete(llm_messages)

        now = datetime.now(UTC)
        conversation.messages.append(
            Message(id=uuid4(), role=Role.USER, content=data.question, created_at=now)
        )
        conversation.messages.append(
            Message(id=uuid4(), role=Role.ASSISTANT, content=completion.content, created_at=now)
        )

        if data.conversation_id is not None:
            await self._conversations.update(conversation)
        else:
            await self._conversations.add(conversation)

        sources = [SourceReference(chunk_id=r.id, score=r.score) for r in results]
        return AnswerQuestionOutput(
            answer=completion.content,
            conversation_id=conversation.id.value,
            sources=sources,
        )

    async def _load_or_create_conversation(self, data: AnswerQuestionInput) -> Conversation:
        if data.conversation_id is None:
            return Conversation(id=ConversationId(uuid4()), tenant_id=data.tenant_id)

        conversation_id = ConversationId(data.conversation_id)
        conversation = await self._conversations.get(data.tenant_id, conversation_id)
        if conversation is None:
            raise EntityNotFoundError(f"Conversation {data.conversation_id} not found.")
        return conversation
