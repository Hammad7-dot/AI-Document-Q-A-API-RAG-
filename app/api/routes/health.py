"""Health check endpoint."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.rate_limit import RATE_LIMIT, limiter
from app.db.session import get_db
from app.services.cache_service import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
@limiter.limit(RATE_LIMIT)
async def health_check(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Report liveness of the API and its core dependencies."""
    db_ok = True
    redis_ok = True

    try:
        await db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False

    try:
        redis = get_redis()
        await redis.ping()
    except Exception:  # noqa: BLE001
        redis_ok = False

    status_str = "ok" if db_ok and redis_ok else "degraded"
    return {
        "status": status_str,
        "database": "ok" if db_ok else "unavailable",
        "redis": "ok" if redis_ok else "unavailable",
    }
