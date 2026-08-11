"""Unit tests for DocumentService validation logic using mocks."""
import uuid
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.exceptions import ValidationAppError
from app.models.document import DocumentStatus
from app.services.document_service import DocumentService, process_document_background

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
        await service.upload_and_process(uuid.uuid4(), upload, MagicMock())


async def test_rejects_wrong_extension(mock_session):
    service = DocumentService(mock_session, embedding_provider=AsyncMock(), cache=AsyncMock())
    upload = _make_upload_file("document.docx", "application/pdf")

    with pytest.raises(ValidationAppError):
        await service.upload_and_process(uuid.uuid4(), upload, MagicMock())


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


async def test_rejects_oversized_file(mock_session, tmp_path):
    service = DocumentService(mock_session, embedding_provider=AsyncMock(), cache=AsyncMock())
    with patch("app.services.document_service.settings") as mock_settings:
        mock_settings.upload_dir = str(tmp_path)
        mock_settings.max_upload_size_mb = 0  # any content exceeds 0MB
        upload = _make_upload_file("document.pdf", "application/pdf", content=b"some pdf bytes")

        with pytest.raises(ValidationAppError, match="exceeds maximum size"):
            await service.upload_and_process(uuid.uuid4(), upload, MagicMock())


async def test_upload_and_process_saves_file_and_schedules_background_task(mock_session, tmp_path):
    service = DocumentService(mock_session, embedding_provider=AsyncMock(), cache=AsyncMock())
    created_document = MagicMock(id=uuid.uuid4())
    service._repo.create = AsyncMock(return_value=created_document)
    background_tasks = MagicMock()

    with patch("app.services.document_service.settings") as mock_settings:
        mock_settings.upload_dir = str(tmp_path)
        mock_settings.max_upload_size_mb = 25
        upload = _make_upload_file("document.pdf", "application/pdf", content=b"%PDF-1.4 real enough")
        owner_id = uuid.uuid4()

        result = await service.upload_and_process(owner_id, upload, background_tasks)

    assert result is created_document
    mock_session.commit.assert_awaited()
    background_tasks.add_task.assert_called_once()
    args = background_tasks.add_task.call_args.args
    assert args[0] is process_document_background
    assert args[1] == created_document.id
    assert args[2] == owner_id


async def test_process_document_raises_when_no_chunks_extracted(mock_session):
    embedding_provider = AsyncMock()
    service = DocumentService(mock_session, embedding_provider=embedding_provider, cache=AsyncMock())
    service._repo.update_status = AsyncMock()
    document = MagicMock(storage_path="/tmp/does-not-matter.pdf")

    with (
        patch("app.services.document_service.extract_text_from_pdf", return_value=""),
        patch("app.services.document_service.chunk_text", return_value=[]),
    ):
        with pytest.raises(ValidationAppError, match="no chunks"):
            await service._process_document(document)

    service._repo.update_status.assert_awaited_with(document, DocumentStatus.PROCESSING)
    embedding_provider.embed_documents.assert_not_awaited()


async def test_process_document_success_embeds_chunks_and_marks_ready(mock_session):
    embedding_provider = AsyncMock()
    embedding_provider.embed_documents = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4]])
    cache = AsyncMock()
    cache.document_meta_key = MagicMock(return_value="doc:meta:123")
    service = DocumentService(mock_session, embedding_provider=embedding_provider, cache=cache)
    service._repo.update_status = AsyncMock()
    service._repo.add_chunks = AsyncMock()
    document = MagicMock(storage_path="/tmp/does-not-matter.pdf", id=uuid.uuid4())

    with (
        patch("app.services.document_service.extract_text_from_pdf", return_value="some extracted text"),
        patch("app.services.document_service.chunk_text", return_value=["chunk one", "chunk two"]),
    ):
        await service._process_document(document)

    embedding_provider.embed_documents.assert_awaited_once_with(["chunk one", "chunk two"])
    service._repo.add_chunks.assert_awaited_once()
    saved_chunks = service._repo.add_chunks.call_args.args[0]
    assert len(saved_chunks) == 2
    assert saved_chunks[0].content == "chunk one"
    assert saved_chunks[1].chunk_index == 1
    service._repo.update_status.assert_awaited_with(document, DocumentStatus.READY)
    cache.set_json.assert_awaited_once()


async def test_list_documents_delegates_to_repository(mock_session):
    service = DocumentService(mock_session, embedding_provider=AsyncMock(), cache=AsyncMock())
    expected = ([MagicMock(), MagicMock()], 2)
    service._repo.list_for_owner = AsyncMock(return_value=expected)
    owner_id = uuid.uuid4()

    result = await service.list_documents(owner_id, page=1, page_size=20)

    assert result == expected
    service._repo.list_for_owner.assert_awaited_once_with(owner_id, 1, 20)


async def test_delete_document_removes_record_cache_and_file(mock_session, tmp_path):
    service = DocumentService(mock_session, embedding_provider=AsyncMock(), cache=AsyncMock())
    stored_file = tmp_path / "doc.pdf"
    stored_file.write_bytes(b"content")
    document = MagicMock(storage_path=str(stored_file))
    service.get_document = AsyncMock(return_value=document)
    service._repo.delete = AsyncMock()
    service._cache.document_meta_key = MagicMock(return_value="doc:meta:123")

    document_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    await service.delete_document(document_id, owner_id)

    service._repo.delete.assert_awaited_once_with(document)
    mock_session.commit.assert_awaited()
    service._cache.delete.assert_awaited_once_with("doc:meta:123")
    assert not stored_file.exists()


async def test_delete_document_skips_missing_file_on_disk(mock_session, tmp_path):
    service = DocumentService(mock_session, embedding_provider=AsyncMock(), cache=AsyncMock())
    missing_path = str(tmp_path / "already-gone.pdf")
    document = MagicMock(storage_path=missing_path)
    service.get_document = AsyncMock(return_value=document)
    service._repo.delete = AsyncMock()

    # Should not raise even though the file doesn't exist on disk.
    await service.delete_document(uuid.uuid4(), uuid.uuid4())


async def test_process_document_background_logs_and_returns_when_document_missing():
    document_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    mock_session = AsyncMock()

    with patch("app.services.document_service.AsyncSessionLocal") as mock_session_local:
        mock_session_local.return_value.__aenter__.return_value = mock_session
        with patch(
            "app.repositories.document_repository.DocumentRepository.get_by_id",
            new=AsyncMock(return_value=None),
        ):
            # Should return cleanly without raising when no matching document exists.
            await process_document_background(document_id, owner_id)


async def test_process_document_background_marks_failed_on_processing_error():
    document_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    mock_session = AsyncMock()
    document = MagicMock(id=document_id)

    with patch("app.services.document_service.AsyncSessionLocal") as mock_session_local:
        mock_session_local.return_value.__aenter__.return_value = mock_session
        with patch(
            "app.repositories.document_repository.DocumentRepository.get_by_id",
            new=AsyncMock(return_value=document),
        ), patch.object(
            DocumentService, "_process_document", new=AsyncMock(side_effect=RuntimeError("boom"))
        ), patch(
            "app.repositories.document_repository.DocumentRepository.update_status",
            new=AsyncMock(),
        ) as mock_update_status:
            await process_document_background(document_id, owner_id)

    mock_session.rollback.assert_awaited_once()
    mock_update_status.assert_awaited_once_with(document, DocumentStatus.FAILED, "boom")
    assert mock_session.commit.await_count >= 1
