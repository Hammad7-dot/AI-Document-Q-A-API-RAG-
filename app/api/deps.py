"""Shared FastAPI dependencies: DB session, current user, rate limiting."""
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import InvalidTokenError, get_subject_from_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import AuthService


async def get_current_user(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the current authenticated user from the Authorization header."""
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        user_id = get_subject_from_token(token, "access")
    except InvalidTokenError as exc:
        raise UnauthorizedError(str(exc)) from exc

    auth_service = AuthService(db)
    return await auth_service.get_current_user(user_id)
