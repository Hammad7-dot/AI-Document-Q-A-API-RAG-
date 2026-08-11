"""Authentication business logic."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    get_subject_from_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import RefreshTokenRepository, UserRepository
from app.schemas.user import TokenPair, UserCreate, UserLogin


class AuthService:
    """Handles registration, login, token refresh, and logout."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)

    async def register(self, payload: UserCreate) -> User:
        existing = await self._users.get_by_email(payload.email)
        if existing is not None:
            raise ConflictError("A user with this email already exists")

        user = await self._users.create(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
        )
        await self._session.commit()
        return user

    async def login(self, payload: UserLogin) -> TokenPair:
        user = await self._users.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is disabled")

        return await self._issue_tokens(user.id)

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            user_id = get_subject_from_token(refresh_token, "refresh")
        except InvalidTokenError as exc:
            raise UnauthorizedError(str(exc)) from exc

        record = await self._refresh_tokens.get_by_token(refresh_token)
        if record is None or record.revoked:
            raise UnauthorizedError("Refresh token has been revoked")
        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise UnauthorizedError("Refresh token has expired")

        # rotate: revoke old, issue new
        await self._refresh_tokens.revoke(record)
        tokens = await self._issue_tokens(user_id)
        await self._session.commit()
        return tokens

    async def logout(self, refresh_token: str) -> None:
        record = await self._refresh_tokens.get_by_token(refresh_token)
        if record is not None and not record.revoked:
            await self._refresh_tokens.revoke(record)
            await self._session.commit()

    async def _issue_tokens(self, user_id: UUID) -> TokenPair:
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )
        await self._refresh_tokens.create(user_id, refresh_token, expires_at)
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def get_current_user(self, user_id: UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or inactive")
        return user
