import json
import logging
from typing import Any

from app.core.redis import redis_client

logger = logging.getLogger("dentalos.cache")


def _extract_domain(key: str) -> str:
    """Extract the domain portion from a cache key.

    Key pattern: ``dentalos:{tid}:{domain}:{resource}:{id}``
    Returns the domain segment (e.g. "appointment", "clinical", "auth").
    Falls back to "unknown" for keys that do not match the expected structure.
    """
    parts = key.split(":")
    # parts[0] = "dentalos", parts[1] = tid/shared, parts[2] = domain
    if len(parts) >= 3:
        return parts[2]
    return "unknown"


async def get_cached(key: str) -> Any | None:
    """Get a value from cache. Returns None on miss or error.

    Fires fire-and-forget INCR counters for hit/miss metrics so the cache
    hit rate target (>90%) can be measured per domain. Counter failures
    never surface to callers.
    """
    try:
        raw = await redis_client.get(key)
        if raw:
            domain = _extract_domain(key)
            logger.debug("cache_hit", extra={"key_prefix": domain})
            try:
                await redis_client.incr(f"dentalos:metrics:cache:hits:{domain}")
            except Exception:
                pass
            return json.loads(raw)
        else:
            domain = _extract_domain(key)
            logger.debug("cache_miss", extra={"key_prefix": domain})
            try:
                await redis_client.incr(f"dentalos:metrics:cache:misses:{domain}")
            except Exception:
                pass
            return None
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
