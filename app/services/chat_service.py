"""RAG chat orchestration: retrieve, build prompt, generate, persist."""
from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ValidationAppError
from app.core.logging import get_logger
from app.models.chat import MessageRole
from app.models.document import DocumentStatus
from app.repositories.chat_repository import ChatRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.chat import ChatResponse, SourceChunk
from app.services.ai.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.ai.llm import LLMProvider, get_llm_provider

logger = get_logger(__name__)


class ChatService:
    """Coordinates semantic retrieval and LLM answer generation."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._chats = ChatRepository(session)
        self._embeddings = embedding_provider or get_embedding_provider()
        self._llm = llm_provider or get_llm_provider()

    async def _retrieve(
        self, document_id: UUID, owner_id: UUID, question: str
    ) -> tuple[list[SourceChunk], str]:
        document = await self._documents.get_by_id(document_id, owner_id)
        if document is None:
            raise ValidationAppError("Document not found")
        if document.status != DocumentStatus.READY:
            raise ValidationAppError("Document is not ready for search yet")

        query_embedding = await self._embeddings.embed_query(question)
        results = await self._documents.search_similar_chunks(
            document_id, query_embedding, settings.top_k
        )

        sources = [
            SourceChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                similarity=round(similarity, 4),
            )
            for chunk, similarity in results
        ]
        context = "\n\n---\n\n".join(
            f"[Source {i + 1}] {s.content}" for i, s in enumerate(sources)
        )
        return sources, context

    async def ask(self, owner_id: UUID, document_id: UUID, question: str, chat_id: UUID | None) -> ChatResponse:
        sources, context = await self._retrieve(document_id, owner_id, question)

        chat = None
        if chat_id is not None:
            chat = await self._chats.get_by_id(chat_id, owner_id)
        if chat is None:
            title = question[:50]
            chat = await self._chats.create_chat(owner_id, document_id, title)

        await self._chats.add_message(chat.id, MessageRole.USER, question)
        answer = await self._llm.generate(question, context)
        await self._chats.add_message(chat.id, MessageRole.ASSISTANT, answer)
        await self._session.commit()

        return ChatResponse(chat_id=chat.id, answer=answer, sources=sources)

    async def ask_stream(
        self, owner_id: UUID, document_id: UUID, question: str, chat_id: UUID | None
    ) -> AsyncIterator[str]:
        sources, context = await self._retrieve(document_id, owner_id, question)

        chat = None
        if chat_id is not None:
            chat = await self._chats.get_by_id(chat_id, owner_id)
        if chat is None:
            title = question[:50]
            chat = await self._chats.create_chat(owner_id, document_id, title)

        await self._chats.add_message(chat.id, MessageRole.USER, question)
        await self._session.commit()

        full_answer = []
        async for token in self._llm.stream(question, context):
            full_answer.append(token)
            yield token

        await self._chats.add_message(chat.id, MessageRole.ASSISTANT, "".join(full_answer))
        await self._session.commit()

    async def list_history(self, owner_id: UUID, page: int, page_size: int):
        return await self._chats.list_for_owner(owner_id, page, page_size)

    async def get_messages(self, owner_id: UUID, chat_id: UUID):
        chat = await self._chats.get_by_id(chat_id, owner_id)
        if chat is None:
            raise ValidationAppError("Chat not found")
        return chat
