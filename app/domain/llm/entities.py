"""Value objects for the LLM context."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    """Role of a message in an LLM conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class LLMMessage:
    """A single message passed to the LLM."""

    role: Role
    content: str


@dataclass(frozen=True, slots=True)
class LLMCompletion:
    """The LLM's generated answer."""

    content: str
    model: str
