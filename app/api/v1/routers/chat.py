"""Chat router — RAG question answering."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import AnswerQuestionUseCaseDep, TenantIdDep
from app.api.v1.schemas.chat import ChatRequest, ChatResponse, ChatSource
from app.application.chat.dtos import AnswerQuestionInput

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    use_case: AnswerQuestionUseCaseDep,
    tenant_id: TenantIdDep,
) -> ChatResponse:
    """Answer a question grounded only on retrieved knowledge (RAG)."""
    output = await use_case.execute(
        AnswerQuestionInput(
            tenant_id=tenant_id,
            question=payload.question,
            conversation_id=payload.conversation_id,
            top_k=payload.top_k,
        )
    )
    return ChatResponse(
        answer=output.answer,
        conversation_id=output.conversation_id,
        sources=[ChatSource(chunk_id=s.chunk_id, score=s.score) for s in output.sources],
    )
