"""Rate limiting via Redis sliding window."""
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

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


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Global rate limit: 200 requests per minute per IP."""

    def __init__(self, app: object, requests_per_minute: int = 200) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute

    async def dispatch(self, request: Request, call_next: object) -> Response:
        # Get client IP; check X-Forwarded-For for requests behind a proxy
        ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
            request.client.host if request.client else "unknown"
        )
        key = f"dentalos:global:rl:{ip}"

        try:
            current = await redis_client.incr(key)
            if current == 1:
                await redis_client.expire(key, 60)
            if current > self.requests_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "SYSTEM_rate_limit",
                        "message": "Too many requests. Please try again later.",
                        "details": {},
                    },
                    headers={"Retry-After": "60"},
                )
        except Exception:
            # Graceful degradation: if Redis is down, allow the request
            pass

        return await call_next(request)


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
