"""Documents router — fully functional ingestion foundation.

POST   /documents        upload + store + register (status UPLOADED)
GET    /documents        list (paged, tenant-scoped)
GET    /documents/{id}    fetch one
DELETE /documents/{id}    soft delete (bytes preserved)
PATCH  /documents/{id}    update metadata / mutable fields
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.api.dependencies import (
    DeleteDocumentUseCaseDep,
    GetDocumentUseCaseDep,
    ListDocumentsUseCaseDep,
    TenantIdDep,
    UpdateDocumentMetadataUseCaseDep,
    UploadDocumentUseCaseDep,
    UploadedByDep,
)
from app.api.v1.schemas.document import UpdateDocumentRequest
from app.application.documents.dtos import (
    DocumentView,
    GetDocumentInput,
    ListDocumentsInput,
    ListDocumentsOutput,
    UpdateDocumentMetadataInput,
    UploadDocumentInput,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentView, status_code=status.HTTP_201_CREATED)
async def upload_document(
    use_case: UploadDocumentUseCaseDep,
    tenant_id: TenantIdDep,
    uploaded_by: UploadedByDep,
    file: UploadFile = File(...),
    knowledge_space_id: UUID | None = Form(default=None),
) -> DocumentView:
    """Upload a knowledge document (PDF today; more sources later)."""
    content = await file.read()
    return await use_case.execute(
        UploadDocumentInput(
            tenant_id=tenant_id,
            original_filename=file.filename or "unknown",
            content=content,
            content_type=file.content_type or "application/octet-stream",
            uploaded_by=uploaded_by,
            knowledge_space_id=knowledge_space_id,
        )
    )


@router.get("", response_model=ListDocumentsOutput)
async def list_documents(
    use_case: ListDocumentsUseCaseDep,
    tenant_id: TenantIdDep,
    knowledge_space_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, gt=0, le=200),
    offset: int = Query(default=0, ge=0),
) -> ListDocumentsOutput:
    """List a tenant's documents."""
    return await use_case.execute(
        ListDocumentsInput(
            tenant_id=tenant_id,
            knowledge_space_id=knowledge_space_id,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/{document_id}", response_model=DocumentView)
async def get_document(
    document_id: UUID,
    use_case: GetDocumentUseCaseDep,
    tenant_id: TenantIdDep,
) -> DocumentView:
    """Fetch a single document."""
    return await use_case.execute(GetDocumentInput(tenant_id=tenant_id, document_id=document_id))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    use_case: DeleteDocumentUseCaseDep,
    tenant_id: TenantIdDep,
) -> None:
    """Soft-delete a document (original bytes are preserved)."""
    await use_case.execute(GetDocumentInput(tenant_id=tenant_id, document_id=document_id))


@router.patch("/{document_id}", response_model=DocumentView)
async def update_document(
    document_id: UUID,
    payload: UpdateDocumentRequest,
    use_case: UpdateDocumentMetadataUseCaseDep,
    tenant_id: TenantIdDep,
) -> DocumentView:
    """Update metadata / mutable fields of a document."""
    return await use_case.execute(
        UpdateDocumentMetadataInput(
            tenant_id=tenant_id,
            document_id=document_id,
            metadata=payload.metadata,
            title=payload.title,
            knowledge_space_id=payload.knowledge_space_id,
        )
    )
