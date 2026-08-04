"""Password hashing and JWT token utilities."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: UUID, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: UUID) -> str:
    """Create a short-lived JWT access token."""
    return _create_token(
        user_id, "access", timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(user_id: UUID) -> str:
    """Create a long-lived JWT refresh token."""
    return _create_token(
        user_id, "refresh", timedelta(days=settings.refresh_token_expire_days)
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Raises JWTError if invalid/expired."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


class InvalidTokenError(Exception):
    """Raised when a token fails validation."""


def get_subject_from_token(token: str, expected_type: TokenType) -> UUID:
    """Extract and validate the subject (user id) from a token."""
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise InvalidTokenError("Invalid or expired token") from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"Expected {expected_type} token")

    subject = payload.get("sub")
    if subject is None:
        raise InvalidTokenError("Token missing subject")

    return UUID(subject)
