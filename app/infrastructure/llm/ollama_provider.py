"""Placeholder Ollama ``LLMProvider``."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.llm.entities import LLMCompletion, LLMMessage
from app.domain.llm.providers import LLMProvider


class OllamaLLMProvider(LLMProvider):
    """Generates completions via a local Ollama server (placeholder)."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url
        self._model = model

    async def complete(self, messages: Sequence[LLMMessage]) -> LLMCompletion:
        raise NotImplementedError
