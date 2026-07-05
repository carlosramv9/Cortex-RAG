"""processing job pipeline: expand processing_jobs

Revision ID: d4e8f1a29b30
Revises: c3d9e1f42a76
Create Date: 2026-07-05

Expands ``processing_jobs`` for the async pipeline: adds version_id, priority,
retry_count, progress, worker_name, error_message, started_at, finished_at;
migrates ``attempts`` -> ``retry_count`` and ``error`` -> ``error_message``;
drops the legacy ``attempts``, ``error`` and ``payload`` columns.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e8f1a29b30"
down_revision: str | None = "c3d9e1f42a76"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "processing_jobs", sa.Column("version_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "processing_jobs",
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "processing_jobs",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "processing_jobs",
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "processing_jobs", sa.Column("worker_name", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "processing_jobs", sa.Column("error_message", sa.Text(), nullable=True)
    )
    op.add_column(
        "processing_jobs",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "processing_jobs",
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Migrate legacy values.
    op.execute("UPDATE processing_jobs SET retry_count = attempts")
    op.execute("UPDATE processing_jobs SET error_message = error")

    # Drop legacy columns.
    op.drop_column("processing_jobs", "attempts")
    op.drop_column("processing_jobs", "error")
    op.drop_column("processing_jobs", "payload")

    # Indexes.
    op.create_index(
        op.f("ix_processing_jobs_job_type"),
        "processing_jobs",
        ["job_type"],
        unique=False,
    )
    op.create_index(
        "ix_jobs_document_type", "processing_jobs", ["document_id", "job_type"]
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_document_type", table_name="processing_jobs")
    op.drop_index(op.f("ix_processing_jobs_job_type"), table_name="processing_jobs")

    op.add_column(
        "processing_jobs",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("processing_jobs", sa.Column("error", sa.Text(), nullable=True))
    op.add_column(
        "processing_jobs",
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
    )

    op.execute("UPDATE processing_jobs SET attempts = retry_count")
    op.execute("UPDATE processing_jobs SET error = error_message")

    op.drop_column("processing_jobs", "finished_at")
    op.drop_column("processing_jobs", "started_at")
    op.drop_column("processing_jobs", "error_message")
    op.drop_column("processing_jobs", "worker_name")
    op.drop_column("processing_jobs", "progress")
    op.drop_column("processing_jobs", "retry_count")
    op.drop_column("processing_jobs", "priority")
    op.drop_column("processing_jobs", "version_id")
