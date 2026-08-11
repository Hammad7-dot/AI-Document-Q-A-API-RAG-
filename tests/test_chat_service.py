"""Unit tests for ChatService using mocked repositories and AI providers."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ValidationAppError
from app.models.document import DocumentStatus
from app.services.chat_service import ChatService

pytestmark = pytest.mark.asyncio


def _make_chunk(content: str):
    chunk = MagicMock()
    chunk.id = uuid.uuid4()
    chunk.document_id = uuid.uuid4()
    chunk.content = content
    return chunk


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


async def test_ask_raises_when_document_not_ready(mock_session):
    service = ChatService(mock_session, embedding_provider=AsyncMock(), llm_provider=AsyncMock())

    document = MagicMock()
    document.status = DocumentStatus.PROCESSING
    service._documents.get_by_id = AsyncMock(return_value=document)

    with pytest.raises(ValidationAppError):
        await service.ask(uuid.uuid4(), uuid.uuid4(), "What is this about?", None)


async def test_ask_raises_when_document_missing(mock_session):
    service = ChatService(mock_session, embedding_provider=AsyncMock(), llm_provider=AsyncMock())
    service._documents.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(ValidationAppError):
        await service.ask(uuid.uuid4(), uuid.uuid4(), "What is this about?", None)


async def test_ask_returns_answer_with_sources(mock_session):
    embedding_provider = AsyncMock()
    embedding_provider.embed_query.return_value = [0.1, 0.2, 0.3]

    llm_provider = AsyncMock()
    llm_provider.generate.return_value = "The document is about testing."

    service = ChatService(mock_session, embedding_provider=embedding_provider, llm_provider=llm_provider)

    document = MagicMock()
    document.status = DocumentStatus.READY
    service._documents.get_by_id = AsyncMock(return_value=document)

    chunk = _make_chunk("Some relevant text about testing.")
    service._documents.search_similar_chunks = AsyncMock(return_value=[(chunk, 0.87)])

    chat = MagicMock()
    chat.id = uuid.uuid4()
    service._chats.create_chat = AsyncMock(return_value=chat)
    service._chats.add_message = AsyncMock()

    result = await service.ask(uuid.uuid4(), uuid.uuid4(), "What is this document about?", None)

    assert result.answer == "The document is about testing."
    assert len(result.sources) == 1
    assert result.sources[0].similarity == 0.87
    assert result.chat_id == chat.id
    embedding_provider.embed_query.assert_awaited_once()
    llm_provider.generate.assert_awaited_once()
