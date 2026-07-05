"""Port: ParserProvider.

Extracts text and metadata from raw document bytes (e.g. PDF via PyMuPDF).
Implemented by the infrastructure layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.parsers.entities import ParsedDocument


class ParserProvider(ABC):
    """Abstract document parser."""

    @abstractmethod
    async def parse(self, content: bytes, *, content_type: str) -> ParsedDocument:
        """Parse raw bytes into a ``ParsedDocument``."""
        raise NotImplementedError
