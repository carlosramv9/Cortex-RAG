"""Typed knowledge metadata.

Replaces the generic ``dict`` metadata with a validated, strongly-typed model
that still serializes losslessly to/from JSON (``model_dump(mode="json")`` /
``model_validate``). Enables future structured queries such as "documents in
Spanish", "documents from the HR department" or "confidential documents".
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator

# ISO 639-1 language codes accepted for the ``language`` field. Curated subset;
# extend as needed.
ALLOWED_LANGUAGES: frozenset[str] = frozenset(
    {
        "es",
        "en",
        "pt",
        "fr",
        "de",
        "it",
        "nl",
        "ca",
        "gl",
        "eu",
        "ru",
        "zh",
        "ja",
        "ko",
        "ar",
        "hi",
        "tr",
        "pl",
        "sv",
        "no",
        "da",
        "fi",
        "cs",
        "el",
        "he",
        "uk",
        "ro",
        "hu",
    }
)


class SecurityLevel(StrEnum):
    """Security classification of a document."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SECRET = "secret"


class KnowledgeMetadata(BaseModel):
    """Enriched, typed document metadata."""

    model_config = ConfigDict(extra="forbid")

    language: str | None = None
    author: str | None = None
    organization: str | None = None
    department: str | None = None
    category: str | None = None
    tags: list[str] = []
    keywords: list[str] = []
    security_level: SecurityLevel | None = None
    retention_policy: str | None = None
    created_by_application: str | None = None
    document_created_at: datetime | None = None
    document_modified_at: datetime | None = None
    custom_properties: dict[str, str] = {}

    @field_validator("language", mode="before")
    @classmethod
    def _validate_language(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("language must be a string ISO 639-1 code.")
        code = value.strip().lower()
        if code not in ALLOWED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{value}'. Use an ISO 639-1 code (e.g. 'es', 'en')."
            )
        return code

    @field_validator("tags")
    @classmethod
    def _validate_tags(cls, tags: list[str]) -> list[str]:
        cleaned = [t.strip() for t in tags if t.strip()]
        lowered = [t.lower() for t in cleaned]
        if len(set(lowered)) != len(lowered):
            raise ValueError("Duplicate tags are not allowed.")
        return cleaned

    @field_validator("keywords")
    @classmethod
    def _validate_keywords(cls, keywords: list[str]) -> list[str]:
        if any(not k.strip() for k in keywords):
            raise ValueError("Empty keywords are not allowed.")
        return [k.strip() for k in keywords]
