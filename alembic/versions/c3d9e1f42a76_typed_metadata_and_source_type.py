"""typed metadata and generalized source_type

Revision ID: c3d9e1f42a76
Revises: b7f2c9a4d1e8
Create Date: 2026-07-05

Data-only migration (no schema change, fully backward compatible):

* Remaps ``knowledge_documents.source_type`` from the legacy ``'file_upload'``
  to a ``SourceType`` value derived from the active version's extension.
* Reshapes the generic ``metadata`` JSON into the typed ``KnowledgeMetadata``
  structure, preserving any previous free-form values under
  ``custom_properties``.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d9e1f42a76"
down_revision: str | None = "b7f2c9a4d1e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Generalize source_type from the active version's extension.
    op.execute(
        """
        UPDATE knowledge_documents d
        SET source_type = CASE lower(v.extension)
            WHEN 'pdf' THEN 'pdf'
            WHEN 'doc' THEN 'word'
            WHEN 'docx' THEN 'word'
            WHEN 'rtf' THEN 'word'
            WHEN 'xls' THEN 'excel'
            WHEN 'xlsx' THEN 'excel'
            WHEN 'csv' THEN 'excel'
            WHEN 'ppt' THEN 'powerpoint'
            WHEN 'pptx' THEN 'powerpoint'
            WHEN 'md' THEN 'markdown'
            WHEN 'markdown' THEN 'markdown'
            WHEN 'txt' THEN 'text'
            WHEN 'html' THEN 'html'
            WHEN 'htm' THEN 'html'
            WHEN 'png' THEN 'image'
            WHEN 'jpg' THEN 'image'
            WHEN 'jpeg' THEN 'image'
            WHEN 'gif' THEN 'image'
            WHEN 'webp' THEN 'image'
            WHEN 'tiff' THEN 'image'
            WHEN 'eml' THEN 'email'
            WHEN 'msg' THEN 'email'
            ELSE 'text'
        END
        FROM knowledge_document_versions v
        WHERE v.id = d.current_version_id
        """
    )
    # Any document without an active version (shouldn't happen) -> default.
    op.execute(
        "UPDATE knowledge_documents SET source_type = 'text' "
        "WHERE source_type = 'file_upload'"
    )

    # 2. Reshape metadata into the typed KnowledgeMetadata skeleton, keeping the
    #    old free-form dict under custom_properties.
    op.execute(
        """
        UPDATE knowledge_documents
        SET metadata = (
            jsonb_build_object(
                'language', NULL,
                'author', NULL,
                'organization', NULL,
                'department', NULL,
                'category', NULL,
                'tags', '[]'::jsonb,
                'keywords', '[]'::jsonb,
                'security_level', NULL,
                'retention_policy', NULL,
                'created_by_application', NULL,
                'document_created_at', NULL,
                'document_modified_at', NULL,
                'custom_properties', COALESCE(metadata::jsonb, '{}'::jsonb)
            )
        )::json
        """
    )


def downgrade() -> None:
    # Restore the legacy free-form metadata (unwrap custom_properties).
    op.execute(
        """
        UPDATE knowledge_documents
        SET metadata = COALESCE(
            (metadata::jsonb -> 'custom_properties')::json, '{}'::json
        )
        """
    )
    op.execute("UPDATE knowledge_documents SET source_type = 'file_upload'")
