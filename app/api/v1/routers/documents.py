"""Documents router.

Endpoints are scaffolding: they return 501 until the use cases are implemented.
The use cases are already wired in ``app.api.dependencies`` and will be injected
here (e.g. ``use_case: UploadDocumentUseCaseDep``) once logic is added.
"""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile, status

from app.api.v1.schemas.document import (
    ProcessDocumentRequest,
    ProcessDocumentResponse,
    UploadDocumentResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=UploadDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(file: UploadFile = File(...)) -> UploadDocumentResponse:
    """Upload a document for later processing."""
    raise NotImplementedError


@router.post("/process", response_model=ProcessDocumentResponse)
async def process_document(payload: ProcessDocumentRequest) -> ProcessDocumentResponse:
    """Parse, chunk, embed and index a previously uploaded document."""
    raise NotImplementedError
