"""Unit tests for DocumentService validation logic using mocks."""
import uuid
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.exceptions import ValidationAppError
from app.services.document_service import DocumentService

pytestmark = pytest.mark.asyncio


def _make_upload_file(filename: str, content_type: str, content: bytes = b"%PDF-1.4 fake") -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )


@pytest.fixture
def mock_session():
    return AsyncMock()


async def test_rejects_non_pdf_content_type(mock_session):
    service = DocumentService(mock_session, embedding_provider=AsyncMock(), cache=AsyncMock())
    upload = _make_upload_file("notes.txt", "text/plain")

    with pytest.raises(ValidationAppError):
        await service.upload_and_process(uuid.uuid4(), upload)


async def test_rejects_wrong_extension(mock_session):
    service = DocumentService(mock_session, embedding_provider=AsyncMock(), cache=AsyncMock())
    upload = _make_upload_file("document.docx", "application/pdf")

    with pytest.raises(ValidationAppError):
        await service.upload_and_process(uuid.uuid4(), upload)


async def test_get_document_not_found_raises(mock_session):
    service = DocumentService(mock_session, embedding_provider=AsyncMock(), cache=AsyncMock())
    service._repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(Exception):
        await service.get_document(uuid.uuid4(), uuid.uuid4())


async def test_get_document_returns_owned_document(mock_session):
    service = DocumentService(mock_session, embedding_provider=AsyncMock(), cache=AsyncMock())
    document = MagicMock()
    service._repo.get_by_id = AsyncMock(return_value=document)

    result = await service.get_document(uuid.uuid4(), uuid.uuid4())

    assert result is document
