"""Tests for SemanticSearchUseCase and AnswerQuestionUseCase (with fakes)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.application.chat.dtos import AnswerQuestionInput
from app.application.chat.use_cases.answer_question import AnswerQuestionUseCase
from app.application.search.dtos import SearchInput
from app.application.search.use_cases.semantic_search import SemanticSearchUseCase
from app.config.settings import ChatSettings
from app.domain.embeddings.providers import EmbeddingTaskType
from app.domain.llm.entities import Role
from app.domain.shared.exceptions import EntityNotFoundError
from app.domain.vector_store.entities import VectorPoint
from tests.fakes import (
    FakeEmbeddingProvider,
    FakeLLMProvider,
    InMemoryConversationRepository,
    InMemoryVectorRepository,
)


async def _seed_chunk(vectors: InMemoryVectorRepository, tenant_id: str, content: str) -> None:
    await vectors.upsert(
        [
            VectorPoint(
                id=uuid4(),
                vector=(1.0, 0.0),
                payload={"tenant_id": tenant_id, "content": content},
            )
        ]
    )


async def test_semantic_search_scopes_by_tenant() -> None:
    embeddings = FakeEmbeddingProvider()
    vectors = InMemoryVectorRepository()
    await _seed_chunk(vectors, "tenant-a", "chunk from A")
    await _seed_chunk(vectors, "tenant-b", "chunk from B")

    use_case = SemanticSearchUseCase(embeddings, vectors)
    result = await use_case.execute(SearchInput(tenant_id="tenant-a", query="hello"))

    assert len(result.hits) == 1
    assert result.hits[0].content == "chunk from A"
    assert embeddings.calls == [EmbeddingTaskType.QUERY]


async def test_answer_question_creates_conversation_and_persists_turn() -> None:
    embeddings = FakeEmbeddingProvider()
    vectors = InMemoryVectorRepository()
    await _seed_chunk(vectors, "tenant-a", "Paris is the capital of France.")
    llm = FakeLLMProvider(response="Paris.")
    conversations = InMemoryConversationRepository()
    use_case = AnswerQuestionUseCase(
        embeddings, vectors, llm, conversations, ChatSettings(history_window=20)
    )

    output = await use_case.execute(
        AnswerQuestionInput(tenant_id="tenant-a", question="What is the capital of France?")
    )

    assert output.answer == "Paris."
    assert len(output.sources) == 1
    stored = conversations.store[output.conversation_id]
    assert len(stored.messages) == 2
    assert stored.messages[0].role == Role.USER
    assert stored.messages[1].role == Role.ASSISTANT
    # System message carries the retrieved context grounding the answer.
    assert "Paris is the capital" in llm.received[0].content
    assert llm.received[0].role == Role.SYSTEM


async def test_answer_question_continues_existing_conversation_with_history_window() -> None:
    embeddings = FakeEmbeddingProvider()
    vectors = InMemoryVectorRepository()
    llm = FakeLLMProvider(response="second answer")
    conversations = InMemoryConversationRepository()
    use_case = AnswerQuestionUseCase(
        embeddings, vectors, llm, conversations, ChatSettings(history_window=1)
    )

    first = await use_case.execute(
        AnswerQuestionInput(tenant_id="tenant-a", question="first question")
    )
    await use_case.execute(
        AnswerQuestionInput(
            tenant_id="tenant-a",
            question="second question",
            conversation_id=first.conversation_id,
        )
    )

    stored = conversations.store[first.conversation_id]
    assert len(stored.messages) == 4  # 2 turns x (user + assistant)
    # history_window=1 -> only the single most recent prior message is sent as history.
    non_system = [m for m in llm.received if m.role != Role.SYSTEM]
    assert len(non_system) == 2  # 1 history message + the new question
    assert non_system[-1].content == "second question"


async def test_answer_question_rejects_wrong_tenant_conversation() -> None:
    embeddings = FakeEmbeddingProvider()
    vectors = InMemoryVectorRepository()
    llm = FakeLLMProvider()
    conversations = InMemoryConversationRepository()
    use_case = AnswerQuestionUseCase(embeddings, vectors, llm, conversations, ChatSettings())

    first = await use_case.execute(
        AnswerQuestionInput(tenant_id="tenant-a", question="hello")
    )

    with pytest.raises(EntityNotFoundError):
        await use_case.execute(
            AnswerQuestionInput(
                tenant_id="tenant-b",
                question="trying to read tenant-a's conversation",
                conversation_id=first.conversation_id,
            )
        )
