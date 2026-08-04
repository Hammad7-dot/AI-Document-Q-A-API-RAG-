"""Business logic for document upload, processing, listing, and deletion."""
import os
import uuid
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.repositories.document_repository import DocumentRepository
from app.services.ai.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.ai.text_processing import chunk_text, extract_text_from_pdf
from app.services.cache_service import CacheService

logger = get_logger(__name__)

ALLOWED_CONTENT_TYPES = {"application/pdf"}


class DocumentService:
    """Handles the full document upload -> parse -> chunk -> embed pipeline."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider | None = None,
        cache: CacheService | None = None,
    ) -> None:
        self._session = session
        self._repo = DocumentRepository(session)
        self._embeddings = embedding_provider or get_embedding_provider()
        self._cache = cache or CacheService()

    async def upload_and_process(self, owner_id: UUID, file: UploadFile) -> Document:
        self._validate_file(file)

        os.makedirs(settings.upload_dir, exist_ok=True)
        stored_name = f"{uuid.uuid4()}.pdf"
        storage_path = os.path.join(settings.upload_dir, stored_name)

        contents = await file.read()
        if len(contents) > settings.max_upload_size_mb * 1024 * 1024:
            raise ValidationAppError(
                f"File exceeds maximum size of {settings.max_upload_size_mb}MB"
            )

        with open(storage_path, "wb") as f:
            f.write(contents)

        document = await self._repo.create(
            owner_id=owner_id,
            filename=file.filename or stored_name,
            storage_path=storage_path,
            content_type=file.content_type or "application/pdf",
            size_bytes=len(contents),
        )
        await self._session.commit()

        document_id = document.id
        try:
            await self._process_document(document)
        except Exception as exc:  # noqa: BLE001
            logger.error("document_processing_failed", document_id=str(document_id), error=str(exc))
            await self._session.rollback()
            await self._repo.update_status(document, DocumentStatus.FAILED, str(exc))
            await self._session.commit()
            raise

        await self._session.refresh(document)
        return document

    async def _process_document(self, document: Document) -> None:
        await self._repo.update_status(document, DocumentStatus.PROCESSING)
        await self._session.commit()

        text = extract_text_from_pdf(document.storage_path)
        chunks = chunk_text(text)
        if not chunks:
            raise ValidationAppError("Document produced no chunks")

        embeddings = await self._embeddings.embed_documents(chunks)

        chunk_records = [
            DocumentChunk(document_id=document.id, chunk_index=i, content=content, embedding=embedding)
            for i, (content, embedding) in enumerate(zip(chunks, embeddings, strict=True))
        ]
        await self._repo.add_chunks(chunk_records)

        await self._repo.update_status(document, DocumentStatus.READY)
        await self._session.commit()

        await self._cache.set_json(
            self._cache.document_meta_key(str(document.id)),
            {"status": DocumentStatus.READY.value, "chunk_count": len(chunk_records)},
        )

    async def get_document(self, document_id: UUID, owner_id: UUID) -> Document:
        document = await self._repo.get_by_id(document_id, owner_id)
        if document is None:
            raise NotFoundError("Document not found")
        return document

    async def list_documents(
        self, owner_id: UUID, page: int, page_size: int
    ) -> tuple[list[Document], int]:
        return await self._repo.list_for_owner(owner_id, page, page_size)

    async def delete_document(self, document_id: UUID, owner_id: UUID) -> None:
        document = await self.get_document(document_id, owner_id)
        storage_path = document.storage_path
        await self._repo.delete(document)
        await self._session.commit()
        await self._cache.delete(self._cache.document_meta_key(str(document_id)))
        if os.path.exists(storage_path):
            os.remove(storage_path)

    @staticmethod
    def _validate_file(file: UploadFile) -> None:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationAppError("Only PDF files are supported")
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise ValidationAppError("File must have a .pdf extension")
