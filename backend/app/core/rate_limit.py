"""Rate limiting via Redis sliding window."""
import logging
import time

from app.core.exceptions import RateLimitError
from app.core.redis import redis_client

logger = logging.getLogger("dentalos.rate_limit")


async def check_rate_limit(key: str, limit: int, window_seconds: int) -> None:
    """Check rate limit using Redis sliding window.

    Raises RateLimitError if the limit is exceeded.
    If Redis is down, allows the request (graceful degradation).
    """
    try:
        redis = redis_client
        now = time.time()
        window_start = now - window_seconds

        pipe = redis.pipeline()
        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)
        # Count entries in the current window
        pipe.zcard(key)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Set expiry on the key
        pipe.expire(key, window_seconds)
        results = await pipe.execute()

        count = results[1]
        if count >= limit:
            raise RateLimitError(retry_after=window_seconds)
    except RateLimitError:
        raise
    except Exception:
        # Redis down — allow the request (graceful degradation)
        logger.warning("Rate limit check failed (Redis unavailable), allowing request")


async def check_rate_limit_tenant(
    tenant_id: str,
    resource: str,
    limit: int,
    window_seconds: int,
) -> None:
    """Check rate limit scoped to a specific tenant and resource.

    Uses key pattern: dentalos:{tenant_id_short}:rl:{resource}
    Raises RateLimitError if the limit is exceeded.
    If Redis is down, allows the request (graceful degradation).
    """
    # tenant_id_short: strip the "tn_" prefix if present, keep the rest
    tenant_id_short = tenant_id.removeprefix("tn_")
    key = f"dentalos:{tenant_id_short}:rl:{resource}"
    await check_rate_limit(key, limit, window_seconds)
