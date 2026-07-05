"""document versioning: split KnowledgeDocument into identity + versions

Revision ID: b7f2c9a4d1e8
Revises: 098482a100da
Create Date: 2026-07-05

Splits the physical file attributes out of ``knowledge_documents`` into a new
immutable ``knowledge_document_versions`` table. Existing rows are migrated: one
version (number 1) is created per document from its current physical columns,
and the document points at it via ``current_version_id``.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7f2c9a4d1e8"
down_revision: str | None = "098482a100da"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. New immutable versions table.
    op.create_table(
        "knowledge_document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=1024), nullable=False),
        sa.Column("filename", sa.String(length=1024), nullable=False),
        sa.Column("extension", sa.String(length=32), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_provider", sa.String(length=32), nullable=False),
        sa.Column("storage_path", sa.String(length=2048), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("uploaded_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_document_versions_document_id"),
        "knowledge_document_versions",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_document_versions_checksum_sha256"),
        "knowledge_document_versions",
        ["checksum_sha256"],
        unique=False,
    )
    op.create_index(
        "ix_versions_document_number",
        "knowledge_document_versions",
        ["document_id", "version_number"],
        unique=True,
    )

    # 2. New identity columns on knowledge_documents (nullable for now).
    op.add_column(
        "knowledge_documents",
        sa.Column("knowledge_space_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "knowledge_documents", sa.Column("title", sa.String(length=1024), nullable=True)
    )
    op.add_column(
        "knowledge_documents", sa.Column("source_type", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "knowledge_documents", sa.Column("current_version_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "knowledge_documents", sa.Column("created_by", sa.String(length=255), nullable=True)
    )

    # 3. Migrate existing data: one version per document, then wire identity.
    op.execute(
        """
        INSERT INTO knowledge_document_versions
            (id, document_id, version_number, original_filename, filename,
             extension, mime_type, size, checksum_sha256, storage_provider,
             storage_path, page_count, metadata, uploaded_by, created_at)
        SELECT gen_random_uuid(), id, 1, original_filename, filename,
               extension, mime_type, size, checksum_sha256, storage_provider,
               storage_path, page_count, metadata, uploaded_by, created_at
        FROM knowledge_documents
        """
    )
    op.execute(
        """
        UPDATE knowledge_documents d
        SET current_version_id = v.id,
            title = d.original_filename,
            source_type = 'file_upload',
            created_by = d.uploaded_by,
            knowledge_space_id = d.collection_id
        FROM knowledge_document_versions v
        WHERE v.document_id = d.id
        """
    )

    # 4. Enforce NOT NULL now that data is populated.
    op.alter_column("knowledge_documents", "title", nullable=False)
    op.alter_column("knowledge_documents", "source_type", nullable=False)
    op.create_index(
        op.f("ix_knowledge_documents_source_type"),
        "knowledge_documents",
        ["source_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_documents_knowledge_space_id"),
        "knowledge_documents",
        ["knowledge_space_id"],
        unique=False,
    )

    # 5. Drop the physical columns (now owned by versions) and their indexes.
    op.drop_index("ix_documents_tenant_checksum", table_name="knowledge_documents")
    op.drop_index(
        op.f("ix_knowledge_documents_checksum_sha256"), table_name="knowledge_documents"
    )
    op.drop_index(
        op.f("ix_knowledge_documents_collection_id"), table_name="knowledge_documents"
    )
    for column in (
        "original_filename",
        "filename",
        "extension",
        "mime_type",
        "size",
        "checksum_sha256",
        "storage_provider",
        "storage_path",
        "uploaded_by",
        "page_count",
        "collection_id",
    ):
        op.drop_column("knowledge_documents", column)


def downgrade() -> None:
    # Restore physical columns on knowledge_documents (nullable).
    op.add_column(
        "knowledge_documents", sa.Column("collection_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "knowledge_documents", sa.Column("page_count", sa.Integer(), nullable=True)
    )
    op.add_column(
        "knowledge_documents", sa.Column("uploaded_by", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "knowledge_documents", sa.Column("storage_path", sa.String(length=2048), nullable=True)
    )
    op.add_column(
        "knowledge_documents", sa.Column("storage_provider", sa.String(length=32), nullable=True)
    )
    op.add_column(
        "knowledge_documents", sa.Column("checksum_sha256", sa.String(length=64), nullable=True)
    )
    op.add_column("knowledge_documents", sa.Column("size", sa.BigInteger(), nullable=True))
    op.add_column(
        "knowledge_documents", sa.Column("mime_type", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "knowledge_documents", sa.Column("extension", sa.String(length=32), nullable=True)
    )
    op.add_column(
        "knowledge_documents", sa.Column("filename", sa.String(length=1024), nullable=True)
    )
    op.add_column(
        "knowledge_documents", sa.Column("original_filename", sa.String(length=1024), nullable=True)
    )

    # Copy the active version's physical attributes back onto the document.
    op.execute(
        """
        UPDATE knowledge_documents d
        SET original_filename = v.original_filename,
            filename = v.filename,
            extension = v.extension,
            mime_type = v.mime_type,
            size = v.size,
            checksum_sha256 = v.checksum_sha256,
            storage_provider = v.storage_provider,
            storage_path = v.storage_path,
            page_count = v.page_count,
            uploaded_by = v.uploaded_by,
            collection_id = d.knowledge_space_id
        FROM knowledge_document_versions v
        WHERE d.current_version_id = v.id
        """
    )

    op.create_index(
        op.f("ix_knowledge_documents_collection_id"),
        "knowledge_documents",
        ["collection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_documents_checksum_sha256"),
        "knowledge_documents",
        ["checksum_sha256"],
        unique=False,
    )
    op.create_index(
        "ix_documents_tenant_checksum",
        "knowledge_documents",
        ["tenant_id", "checksum_sha256"],
        unique=False,
    )

    # Drop identity columns / indexes added in upgrade.
    op.drop_index(
        op.f("ix_knowledge_documents_knowledge_space_id"),
        table_name="knowledge_documents",
    )
    op.drop_index(
        op.f("ix_knowledge_documents_source_type"), table_name="knowledge_documents"
    )
    op.drop_column("knowledge_documents", "created_by")
    op.drop_column("knowledge_documents", "current_version_id")
    op.drop_column("knowledge_documents", "source_type")
    op.drop_column("knowledge_documents", "title")
    op.drop_column("knowledge_documents", "knowledge_space_id")

    op.drop_index(
        "ix_versions_document_number", table_name="knowledge_document_versions"
    )
    op.drop_index(
        op.f("ix_knowledge_document_versions_checksum_sha256"),
        table_name="knowledge_document_versions",
    )
    op.drop_index(
        op.f("ix_knowledge_document_versions_document_id"),
        table_name="knowledge_document_versions",
    )
    op.drop_table("knowledge_document_versions")
