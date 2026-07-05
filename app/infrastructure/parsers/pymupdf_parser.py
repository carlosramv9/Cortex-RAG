"""Placeholder PyMuPDF ``ParserProvider``."""

from __future__ import annotations

from app.domain.parsers.entities import ParsedDocument
from app.domain.parsers.providers import ParserProvider


class PyMuPDFParserProvider(ParserProvider):
    """Extracts text/metadata from PDFs via PyMuPDF (placeholder)."""

    async def parse(self, content: bytes, *, content_type: str) -> ParsedDocument:
        raise NotImplementedError
