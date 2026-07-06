"""PyMuPDF ``ParserProvider``.

Extracts plain text per page and joins them with a form-feed (``\\f``), the
conventional page-break marker, so downstream chunking can still locate page
boundaries by splitting on it if needed. PDF metadata fields are copied
verbatim (falsy/empty ones dropped) into ``ParsedDocument.metadata``.
"""

from __future__ import annotations

import asyncio

import fitz

from app.domain.parsers.entities import ParsedDocument
from app.domain.parsers.providers import ParserProvider


class PyMuPDFParserProvider(ParserProvider):
    """Extracts text/metadata from PDFs via PyMuPDF."""

    async def parse(self, content: bytes, *, content_type: str) -> ParsedDocument:
        return await asyncio.to_thread(self._parse_sync, content)

    def _parse_sync(self, content: bytes) -> ParsedDocument:
        with fitz.open(stream=content, filetype="pdf") as doc:
            pages = [page.get_text() for page in doc]
            metadata = {k: str(v) for k, v in (doc.metadata or {}).items() if v}
            return ParsedDocument(
                text="\f".join(pages),
                page_count=doc.page_count,
                metadata=metadata,
            )
