"""Value objects for the parsers context."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """The text content and metadata extracted from a raw document."""

    text: str
    page_count: int
    metadata: dict[str, str] = field(default_factory=dict)
