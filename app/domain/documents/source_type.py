"""SourceType: the kind of knowledge source a document comes from.

No magic strings anywhere in the codebase — always use this enum.
"""

from __future__ import annotations

from enum import StrEnum


class SourceType(StrEnum):
    """Supported knowledge source types."""

    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"
    MARKDOWN = "markdown"
    TEXT = "text"
    HTML = "html"
    IMAGE = "image"
    EMAIL = "email"
    NOTION = "notion"
    CONFLUENCE = "confluence"
    GITHUB = "github"
    DATABASE = "database"
    API = "api"
    WEB = "web"

    @classmethod
    def from_extension(cls, extension: str) -> SourceType:
        """Map a file extension to a source type (defaults to ``TEXT``)."""
        return _EXTENSION_MAP.get(extension.lstrip(".").lower(), cls.TEXT)


_EXTENSION_MAP: dict[str, SourceType] = {
    "pdf": SourceType.PDF,
    "doc": SourceType.WORD,
    "docx": SourceType.WORD,
    "rtf": SourceType.WORD,
    "xls": SourceType.EXCEL,
    "xlsx": SourceType.EXCEL,
    "csv": SourceType.EXCEL,
    "ppt": SourceType.POWERPOINT,
    "pptx": SourceType.POWERPOINT,
    "md": SourceType.MARKDOWN,
    "markdown": SourceType.MARKDOWN,
    "txt": SourceType.TEXT,
    "html": SourceType.HTML,
    "htm": SourceType.HTML,
    "png": SourceType.IMAGE,
    "jpg": SourceType.IMAGE,
    "jpeg": SourceType.IMAGE,
    "gif": SourceType.IMAGE,
    "webp": SourceType.IMAGE,
    "tiff": SourceType.IMAGE,
    "eml": SourceType.EMAIL,
    "msg": SourceType.EMAIL,
}
