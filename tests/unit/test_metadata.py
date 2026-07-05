"""Tests for KnowledgeMetadata and SourceType."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.domain.documents.metadata import KnowledgeMetadata, SecurityLevel
from app.domain.documents.source_type import SourceType


class TestSourceType:
    def test_from_extension_known(self) -> None:
        assert SourceType.from_extension("pdf") == SourceType.PDF
        assert SourceType.from_extension(".DOCX") == SourceType.WORD
        assert SourceType.from_extension("xlsx") == SourceType.EXCEL
        assert SourceType.from_extension("png") == SourceType.IMAGE

    def test_from_extension_unknown_defaults_to_text(self) -> None:
        assert SourceType.from_extension("xyz") == SourceType.TEXT

    def test_covers_required_sources(self) -> None:
        required = {
            "PDF",
            "WORD",
            "EXCEL",
            "POWERPOINT",
            "MARKDOWN",
            "TEXT",
            "HTML",
            "IMAGE",
            "EMAIL",
            "NOTION",
            "CONFLUENCE",
            "GITHUB",
            "DATABASE",
            "API",
            "WEB",
        }
        assert required <= set(SourceType.__members__)


class TestKnowledgeMetadataValidation:
    def test_language_normalized(self) -> None:
        assert KnowledgeMetadata(language="ES").language == "es"

    def test_invalid_language_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            KnowledgeMetadata(language="klingon")

    def test_duplicate_tags_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            KnowledgeMetadata(tags=["iso9001", "ISO9001"])

    def test_empty_keyword_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            KnowledgeMetadata(keywords=["ok", "  "])

    def test_unknown_field_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            KnowledgeMetadata(lang="es")  # type: ignore[call-arg]

    def test_security_level_enum(self) -> None:
        md = KnowledgeMetadata(security_level=SecurityLevel.CONFIDENTIAL)
        assert md.security_level == SecurityLevel.CONFIDENTIAL

    def test_tags_trimmed_and_empty_dropped(self) -> None:
        assert KnowledgeMetadata(tags=[" a ", "", "b"]).tags == ["a", "b"]


class TestKnowledgeMetadataSerialization:
    def test_json_roundtrip_preserves_types(self) -> None:
        now = datetime(2026, 7, 5, 12, 0, tzinfo=UTC)
        original = KnowledgeMetadata(
            language="es",
            department="RH",
            security_level=SecurityLevel.CONFIDENTIAL,
            tags=["ISO9001"],
            keywords=["auditoria"],
            document_created_at=now,
            custom_properties={"cost_center": "1234"},
        )

        dumped = original.model_dump(mode="json")
        # JSON-safe primitives.
        assert dumped["security_level"] == "confidential"
        assert isinstance(dumped["document_created_at"], str)

        restored = KnowledgeMetadata.model_validate(dumped)
        assert restored == original
        assert restored.security_level is SecurityLevel.CONFIDENTIAL
        assert restored.document_created_at == now

    def test_empty_metadata_roundtrip(self) -> None:
        md = KnowledgeMetadata()
        assert KnowledgeMetadata.model_validate(md.model_dump(mode="json")) == md
