"""Authentication endpoints: register, login, refresh, logout."""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.rate_limit import RATE_LIMIT, limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    LogoutRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserLogin,
    UserRead,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(RATE_LIMIT)
async def register(request: Request, payload: UserCreate, db: AsyncSession = Depends(get_db)) -> UserRead:
    """Register a new user account."""
    service = AuthService(db)
    user = await service.register(payload)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPair)
@limiter.limit(RATE_LIMIT)
async def login(request: Request, payload: UserLogin, db: AsyncSession = Depends(get_db)) -> TokenPair:
    """Authenticate a user and issue an access/refresh token pair."""
    service = AuthService(db)
    return await service.login(payload)


@router.post("/refresh", response_model=TokenPair)
@limiter.limit(RATE_LIMIT)
async def refresh(request: Request, payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    """Exchange a valid refresh token for a new token pair."""
    service = AuthService(db)
    return await service.refresh(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(RATE_LIMIT)
async def logout(request: Request, payload: LogoutRequest, db: AsyncSession = Depends(get_db)) -> None:
    """Revoke a refresh token, effectively logging the user out."""
    service = AuthService(db)
    await service.logout(payload.refresh_token)


users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("/me", response_model=UserRead)
@limiter.limit(RATE_LIMIT)
async def get_me(request: Request, current_user: User = Depends(get_current_user)) -> UserRead:
    """Return the currently authenticated user's profile."""
    return UserRead.model_validate(current_user)
