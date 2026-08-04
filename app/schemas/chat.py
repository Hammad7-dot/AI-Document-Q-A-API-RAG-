"""Pydantic schemas for chat and messages."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.chat import MessageRole


class SourceChunk(BaseModel):
    chunk_id: UUID
    document_id: UUID
    content: str
    similarity: float


class ChatRequest(BaseModel):
    document_id: UUID
    question: str = Field(min_length=1, max_length=4000)
    chat_id: UUID | None = None
    stream: bool = False


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: MessageRole
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    chat_id: UUID
    answer: str
    sources: list[SourceChunk]


class ChatHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatHistoryResponse(BaseModel):
    items: list[ChatHistoryItem]
    total: int
    page: int
    page_size: int


class ChatMessagesResponse(BaseModel):
    chat_id: UUID
    messages: list[MessageRead]
