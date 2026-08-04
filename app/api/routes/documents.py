"""Document upload, listing, retrieval, and deletion endpoints."""
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.document import DocumentListResponse, DocumentRead
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentRead:
    """Upload a PDF document; it is parsed, chunked, embedded, and indexed."""
    service = DocumentService(db)
    document = await service.upload_and_process(current_user.id, file)
    return DocumentRead.model_validate(document)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """List the current user's documents, paginated."""
    service = DocumentService(db)
    items, total = await service.list_documents(current_user.id, page, page_size)
    return DocumentListResponse(
        items=[DocumentRead.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentRead:
    """Fetch metadata for a single document owned by the current user."""
    service = DocumentService(db)
    document = await service.get_document(document_id, current_user.id)
    return DocumentRead.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a document and all associated chunks/embeddings."""
    service = DocumentService(db)
    await service.delete_document(document_id, current_user.id)
