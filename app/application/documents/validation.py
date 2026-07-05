"""Reusable upload validation against the configured policy."""

from __future__ import annotations

from app.config.settings import UploadSettings
from app.domain.shared.exceptions import ValidationError


def validate_upload(
    settings: UploadSettings,
    *,
    original_filename: str,
    content: bytes,
    content_type: str,
) -> str:
    """Validate an uploaded file; return the normalized extension.

    Shared by the upload-document and add-version use cases so the policy is
    enforced identically everywhere.
    """
    if not content:
        raise ValidationError("Uploaded file is empty.")

    if len(content) > settings.max_size_bytes:
        raise ValidationError(f"File exceeds max size of {settings.max_size_mb} MB.")

    if "." not in original_filename:
        raise ValidationError("Filename has no extension.")
    extension = original_filename.rsplit(".", 1)[-1].lower()

    if extension not in settings.allowed_extensions:
        raise ValidationError(
            f"Extension '.{extension}' is not allowed. Allowed: {settings.allowed_extensions}."
        )

    if content_type not in settings.allowed_mime_types:
        raise ValidationError(
            f"MIME type '{content_type}' is not allowed. Allowed: {settings.allowed_mime_types}."
        )
    return extension
