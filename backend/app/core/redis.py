from typing import Any

import redis.asyncio as redis

from app.core.config import settings

pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=50,
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5,
    retry_on_timeout=True,
)

redis_client = redis.Redis(connection_pool=pool)


def _extract_domain(key: str) -> str:
    """Extract the domain segment from a cache key.

    Key pattern: dentalos:{tid}:{domain}:{resource}:{id}
    Falls back to "unknown" if the key doesn't match the expected pattern.
    """
    parts = key.split(":")
    if len(parts) >= 3:
        return parts[2]
    return "unknown"


async def cache_get(key: str) -> Any | None:
    """Get a value from cache, recording hit/miss metrics."""
    from app.core.metrics import record_cache_hit, record_cache_miss

    value = await redis_client.get(key)
    domain = _extract_domain(key)
    if value is not None:
        record_cache_hit(domain)
    else:
        record_cache_miss(domain)
    return value


async def cache_set(key: str, value: Any, ex: int | None = None) -> None:
    """Set a value in cache, recording set metrics."""
    from app.core.metrics import record_cache_set

    await redis_client.set(key, value, ex=ex)
    record_cache_set(_extract_domain(key))


async def cache_delete(key: str) -> None:
    """Delete a value from cache, recording delete metrics."""
    from app.core.metrics import record_cache_delete

    await redis_client.delete(key)
    record_cache_delete(_extract_domain(key))
