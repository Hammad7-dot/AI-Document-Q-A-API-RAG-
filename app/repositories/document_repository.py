"""Data access layer for Document and DocumentChunk entities."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk, DocumentStatus


class DocumentRepository:
    """Repository encapsulating all database access for documents."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, owner_id: UUID, filename: str, storage_path: str, content_type: str, size_bytes: int
    ) -> Document:
        document = Document(
            owner_id=owner_id,
            filename=filename,
            storage_path=storage_path,
            content_type=content_type,
            size_bytes=size_bytes,
            status=DocumentStatus.UPLOADED,
        )
        self._session.add(document)
        await self._session.flush()
        return document

    async def get_by_id(self, document_id: UUID, owner_id: UUID) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.id == document_id, Document.owner_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def list_for_owner(
        self, owner_id: UUID, page: int, page_size: int
    ) -> tuple[list[Document], int]:
        count_result = await self._session.execute(
            select(func.count()).select_from(Document).where(Document.owner_id == owner_id)
        )
        total = count_result.scalar_one()

        result = await self._session.execute(
            select(Document)
            .where(Document.owner_id == owner_id)
            .order_by(Document.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def update_status(
        self, document: Document, status: DocumentStatus, error_message: str | None = None
    ) -> Document:
        document.status = status
        document.error_message = error_message
        await self._session.flush()
        return document

    async def delete(self, document: Document) -> None:
        await self._session.delete(document)
        await self._session.flush()

    async def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        self._session.add_all(chunks)
        await self._session.flush()

    async def search_similar_chunks(
        self, document_id: UUID, query_embedding: list[float], top_k: int
    ) -> list[tuple[DocumentChunk, float]]:
        """Return top_k chunks ordered by cosine distance to the query embedding."""
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        result = await self._session.execute(
            select(DocumentChunk, distance.label("distance"))
            .where(DocumentChunk.document_id == document_id)
            .order_by(distance)
            .limit(top_k)
        )
        rows = result.all()
        # similarity = 1 - cosine_distance
        return [(chunk, 1 - dist) for chunk, dist in rows]
