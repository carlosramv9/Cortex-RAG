"""Aggregate router wiring all v1 feature routers together."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers import chat, documents, search

api_router = APIRouter()
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(search.router)
