"""Gemini ``LLMProvider``.

Uses the classic ``generate_content`` call (not the newer stateful
Interactions API): this service already persists conversation history in
Postgres (``ConversationRepository``), so the LLM is kept stateless from our
side — we pass the full turn window ourselves on every call instead of
tracking a second, Gemini-side session id.
"""

from __future__ import annotations

from collections.abc import Sequence

from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.domain.llm.entities import LLMCompletion, LLMMessage, Role
from app.domain.llm.providers import LLMProvider
from app.domain.shared.exceptions import ServiceUnavailableError

_ROLE_MAP = {Role.USER: "user", Role.ASSISTANT: "model"}


class GeminiLLMProvider(LLMProvider):
    """Generates completions via the Gemini API."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def complete(self, messages: Sequence[LLMMessage]) -> LLMCompletion:
        system_parts = [m.content for m in messages if m.role == Role.SYSTEM]
        contents = [
            types.Content(role=_ROLE_MAP[m.role], parts=[types.Part.from_text(text=m.content)])
            for m in messages
            if m.role in _ROLE_MAP
        ]

        config = (
            types.GenerateContentConfig(system_instruction="\n".join(system_parts))
            if system_parts
            else None
        )
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model, contents=contents, config=config
            )
        except APIError as exc:
            if exc.code == 429:
                raise ServiceUnavailableError(
                    "Gemini rate limit exceeded. Please try again in a moment."
                ) from exc
            raise
        return LLMCompletion(content=response.text or "", model=self._model)
