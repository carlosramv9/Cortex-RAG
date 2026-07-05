"""Chat router (scaffolding — returns 501)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    """Answer a question grounded only on retrieved knowledge (RAG)."""
    raise NotImplementedError
