import json
import logging
from typing import Any

from app.core.redis import redis_client

logger = logging.getLogger("dentalos.cache")


async def get_cached(key: str) -> Any | None:
    """Get a value from cache. Returns None on miss or error."""
    try:
        raw = await redis_client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        logger.warning("cache_get_failed", extra={"key_prefix": _safe_key_prefix(key)})
        return None


async def set_cached(key: str, value: Any, ttl_seconds: int) -> None:
    """Set a value in cache with TTL. Silently fails on error."""
    try:
        await redis_client.setex(key, ttl_seconds, json.dumps(value, default=str))
    except Exception:
        logger.warning("cache_set_failed", extra={"key_prefix": _safe_key_prefix(key)})


async def cache_delete(key: str) -> None:
    """Delete a single cache key. Silently fails on error."""
    try:
        await redis_client.delete(key)
    except Exception:
        logger.warning("cache_delete_failed", extra={"key_prefix": _safe_key_prefix(key)})


async def cache_delete_pattern(pattern: str) -> None:
    """Delete keys matching glob pattern. Uses SCAN, never KEYS."""
    try:
        cursor: int = 0
        while True:
            cursor, keys = await redis_client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        logger.warning("cache_pattern_delete_failed", extra={"pattern": pattern})


def _safe_key_prefix(key: str) -> str:
    """Extract a safe prefix from a cache key for logging (no PHI)."""
    parts = key.split(":")
    return ":".join(parts[:3]) if len(parts) >= 3 else key
