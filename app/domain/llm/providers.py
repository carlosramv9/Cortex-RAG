"""Port: LLMProvider.

Abstraction over a local LLM (e.g. Ollama/vLLM). Implemented by the
infrastructure layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.llm.entities import LLMCompletion, LLMMessage


class LLMProvider(ABC):
    """Abstract LLM provider."""

    @abstractmethod
    async def complete(self, messages: Sequence[LLMMessage]) -> LLMCompletion:
        """Generate a completion from a sequence of messages."""
        raise NotImplementedError
