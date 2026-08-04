"""Data access layer for User and RefreshToken entities."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.models.user import User


class UserRepository:
    """Repository encapsulating all database access for users."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str, full_name: str | None) -> User:
        user = User(email=email, hashed_password=hashed_password, full_name=full_name)
        self._session.add(user)
        await self._session.flush()
        return user


class RefreshTokenRepository:
    """Repository encapsulating all database access for refresh tokens."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: UUID, token: str, expires_at: datetime) -> RefreshToken:
        record = RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_by_token(self, token: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        return result.scalar_one_or_none()

    async def revoke(self, token_record: RefreshToken) -> None:
        token_record.revoked = True
        await self._session.flush()
