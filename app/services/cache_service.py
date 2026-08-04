"""Redis-backed cache service for embeddings, metadata, and sessions."""
import json
from typing import Any

from redis.asyncio import Redis, from_url

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: Redis | None = None


def get_redis() -> Redis:
    """Return a singleton Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = from_url(settings.redis_url, decode_responses=True)
    return _redis_client


class CacheService:
    """Thin wrapper around Redis providing JSON get/set with a default TTL."""

    def __init__(self, redis: Redis | None = None) -> None:
        self._redis = redis or get_redis()
        self._ttl = settings.redis_ttl_seconds

    async def get_json(self, key: str) -> Any | None:
        try:
            raw = await self._redis.get(key)
            return json.loads(raw) if raw else None
        except Exception:  # pragma: no cover - cache is best-effort
            logger.warning("cache_get_failed", key=key)
            return None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        try:
            await self._redis.set(key, json.dumps(value), ex=ttl or self._ttl)
        except Exception:  # pragma: no cover - cache is best-effort
            logger.warning("cache_set_failed", key=key)

    async def delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except Exception:  # pragma: no cover
            logger.warning("cache_delete_failed", key=key)

    def embedding_key(self, text_hash: str) -> str:
        return f"embedding:{text_hash}"

    def document_meta_key(self, document_id: str) -> str:
        return f"document:meta:{document_id}"
