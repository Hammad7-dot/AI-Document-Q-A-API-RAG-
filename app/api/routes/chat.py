"""Chat endpoints: ask a question (JSON or SSE streaming) and view history."""
import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessagesResponse,
    ChatRequest,
    ChatResponse,
    MessageRead,
)
from app.services.chat_service import ChatService

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=None)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ask a question about a document. Returns JSON, or SSE if stream=true."""
    service = ChatService(db)

    if payload.stream:
        return StreamingResponse(
            _sse_stream(service, current_user.id, payload),
            media_type="text/event-stream",
        )

    result: ChatResponse = await service.ask(
        current_user.id, payload.document_id, payload.question, payload.chat_id
    )
    return result


async def _sse_stream(service: ChatService, owner_id, payload: ChatRequest):
    async for token in service.ask_stream(
        owner_id, payload.document_id, payload.question, payload.chat_id
    ):
        yield f"data: {json.dumps({'token': token})}\n\n"
    yield "event: done\ndata: {}\n\n"


@router.get("/chat/history", response_model=ChatHistoryResponse)
async def chat_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatHistoryResponse:
    """List the current user's chat conversations, paginated."""
    service = ChatService(db)
    items, total = await service.list_history(current_user.id, page, page_size)
    return ChatHistoryResponse(
        items=items, total=total, page=page, page_size=page_size
    )


@router.get("/chat/{chat_id}/messages", response_model=ChatMessagesResponse)
async def chat_messages(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatMessagesResponse:
    """Return the full message history for a single chat conversation."""
    service = ChatService(db)
    chat_record = await service.get_messages(current_user.id, chat_id)
    return ChatMessagesResponse(
        chat_id=chat_record.id,
        messages=[MessageRead.model_validate(m) for m in chat_record.messages],
    )
