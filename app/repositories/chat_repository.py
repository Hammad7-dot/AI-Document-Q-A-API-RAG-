"""Data access layer for Chat and Message entities."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import Chat, Message, MessageRole


class ChatRepository:
    """Repository encapsulating all database access for chats and messages."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_chat(self, owner_id: UUID, document_id: UUID, title: str) -> Chat:
        chat = Chat(owner_id=owner_id, document_id=document_id, title=title)
        self._session.add(chat)
        await self._session.flush()
        return chat

    async def get_by_id(self, chat_id: UUID, owner_id: UUID) -> Chat | None:
        result = await self._session.execute(
            select(Chat)
            .options(selectinload(Chat.messages))
            .where(Chat.id == chat_id, Chat.owner_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def list_for_owner(self, owner_id: UUID, page: int, page_size: int) -> tuple[list[Chat], int]:
        count_result = await self._session.execute(
            select(func.count()).select_from(Chat).where(Chat.owner_id == owner_id)
        )
        total = count_result.scalar_one()

        result = await self._session.execute(
            select(Chat)
            .where(Chat.owner_id == owner_id)
            .order_by(Chat.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def add_message(self, chat_id: UUID, role: MessageRole, content: str) -> Message:
        message = Message(chat_id=chat_id, role=role, content=content)
        self._session.add(message)
        await self._session.flush()
        return message
