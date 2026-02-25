# Rate Limiting Spec

> **Spec ID:** I-07
> **Status:** Draft
> **Last Updated:** 2026-02-24

---

## Overview

**Feature:** Redis-based rate limiting for all DentalOS API endpoints. Uses a sliding window algorithm to enforce per-user, per-IP, and per-tenant request limits. Configurable per subscription plan with endpoint-specific overrides.

**Domain:** infra

**Priority:** Critical

**Dependencies:** I-01 (multi-tenancy), I-05 (caching-strategy)

---

## Algorithm: Sliding Window Counter

DentalOS uses the **sliding window counter** algorithm implemented on Redis. This approach combines the memory efficiency of fixed windows with the accuracy of sliding logs.

### How It Works

1. Divide time into fixed windows (e.g., 1-minute buckets)
2. Track request counts in the current window and the previous window
3. Calculate a weighted count: `weighted = previous_count * overlap_percentage + current_count`
4. If `weighted >= limit`, reject the request with 429

### Why Sliding Window (Not Token Bucket or Leaky Bucket)

- **Token bucket:** More complex state, harder to implement atomically in Redis
- **Leaky bucket:** Smooths traffic but adds latency; inappropriate for bursty clinical workflows (e.g., doctor recording multiple conditions rapidly)
- **Fixed window:** Allows burst at window boundaries (2x limit in worst case)
- **Sliding window counter:** Best balance of accuracy, simplicity, and Redis performance

---

## Rate Limit Tiers

### Global Defaults

| Context | Limit | Window | Key Pattern |
|---------|-------|--------|-------------|
| Authenticated user | 100 requests | 1 minute | `rl:user:{tenant_id}:{user_id}:{endpoint_group}` |
| Unauthenticated IP | 20 requests | 1 minute | `rl:ip:{ip_address}` |
| Per-tenant global | 1000 requests | 1 minute | `rl:tenant:{tenant_id}` |

### Per-Plan Limits

Subscription plan overrides the global defaults. Plan limits are cached in Redis from the tenant settings (see `infra/caching-strategy.md`).

| Plan | Auth User Limit | Tenant Global Limit | Notes |
|------|-----------------|---------------------|-------|
| **Free** | 60 req/min | 300 req/min | Strict limits to prevent abuse on free tier |
| **Pro** | 100 req/min | 1000 req/min | Standard limits |
| **Enterprise** | 300 req/min | 5000 req/min | Relaxed for high-volume clinics |

Enterprise tenants may request custom limits via support. Custom limits are stored in the tenant configuration and loaded into Redis at tenant startup.

---

## Endpoint-Specific Overrides

These overrides take precedence over plan-level defaults. They protect sensitive or expensive endpoints.

### Authentication Endpoints (Unauthenticated)

| Endpoint | Limit | Window | Key | Rationale |
|----------|-------|--------|-----|-----------|
| `POST /api/v1/auth/login` | 5 | 15 min | `rl:login:{ip}` | Brute force prevention |
| `POST /api/v1/auth/register` | 3 | 1 hour | `rl:register:{ip}` | Spam account prevention |
| `POST /api/v1/auth/forgot-password` | 3 | 1 hour | `rl:forgot:{ip}` | Email bombing prevention |
| `POST /api/v1/auth/reset-password` | 5 | 1 hour | `rl:reset:{ip}` | Token brute force prevention |
| `POST /api/v1/auth/verify-email` | 5 | 1 hour | `rl:verify:{ip}` | Token brute force prevention |

### Clinical Endpoints (Authenticated)

| Endpoint | Limit | Window | Key | Rationale |
|----------|-------|--------|-----|-----------|
| `GET /api/v1/patients/search` | 30 | 1 min | `rl:search:{tenant_id}:{user_id}` | Database-heavy full-text search |
| `POST /api/v1/patients/{id}/odontogram/conditions` | 60 | 1 min | `rl:odon:{tenant_id}:{user_id}` | Allow rapid clinical entry but prevent abuse |
| `POST /api/v1/patients/import` | 3 | 1 hour | `rl:import:{tenant_id}` | CPU-heavy async job; per-tenant to prevent queue flooding |
| `GET /api/v1/patients/export` | 5 | 1 hour | `rl:export:{tenant_id}:{user_id}` | Resource-heavy streaming response |

### Compliance Endpoints (Authenticated, Per-Tenant)

| Endpoint | Limit | Window | Key | Rationale |
|----------|-------|--------|-----|-----------|
| `POST /api/v1/compliance/rips/generate` | 5 | 1 hour | `rl:rips:{tenant_id}` | RIPS generation is CPU-intensive; per-tenant |
| `GET /api/v1/compliance/rips/export` | 10 | 1 hour | `rl:rips_export:{tenant_id}` | Large file exports |

### Public API Endpoints

| Endpoint | Limit | Window | Key | Rationale |
|----------|-------|--------|-----|-----------|
| `GET /api/v1/public/*` | 30 | 1 min | `rl:public:{ip}` | Public booking pages, widget embeds |
| `POST /api/v1/public/appointments/book` | 5 | 15 min | `rl:book:{ip}` | Prevent appointment spam |

---

## Response Headers

All API responses include rate limit information in standard headers.

### Headers

| Header | Description | Example |
|--------|-------------|---------|
| `X-RateLimit-Limit` | Maximum requests allowed in the window | `100` |
| `X-RateLimit-Remaining` | Requests remaining in the current window | `87` |
| `X-RateLimit-Reset` | Unix timestamp when the window resets | `1740412800` |
| `Retry-After` | Seconds until the client can retry (only on 429) | `23` |

### 429 Response Format

When a request is rate-limited, the API returns:

**Status:** `429 Too Many Requests`

```json
{
  "error": "rate_limit_exceeded",
  "message": "Has excedido el limite de solicitudes. Intenta de nuevo en 23 segundos.",
  "message_en": "Rate limit exceeded. Try again in 23 seconds.",
  "details": {
    "limit": 100,
    "window_seconds": 60,
    "retry_after_seconds": 23,
    "retry_after": "2026-02-24T15:30:23Z"
  }
}
```

**Notes:**
- Error messages are bilingual (Spanish primary, English secondary) for LATAM users
- `retry_after_seconds` provides the exact wait time
- The response is intentionally lightweight to not waste bandwidth on rejected requests

---

## Redis Key Design

### Key Pattern

```
rl:{scope}:{identifier}:{window_timestamp}
```

- `scope`: `user`, `ip`, `tenant`, or endpoint-specific like `login`, `search`
- `identifier`: user ID, IP address, or tenant ID
- `window_timestamp`: Unix timestamp floored to the window start

### Example Keys

```
rl:user:tn_abc123:usr_def456:1740412740    # User limit, minute window
rl:user:tn_abc123:usr_def456:1740412800    # Next minute window
rl:ip:192.168.1.1:1740412740               # IP limit
rl:login:203.0.113.50:1740411900           # Login attempt, 15-min window
rl:tenant:tn_abc123:1740412740             # Tenant global limit
rl:rips:tn_abc123:1740409200               # RIPS generation, hourly window
```

### TTL Strategy

Each key has a TTL of `2 * window_size` to ensure automatic cleanup. The previous window key is needed for the sliding window calculation, so both current and previous must be alive.

| Window Size | Key TTL |
|-------------|---------|
| 1 minute | 120 seconds |
| 15 minutes | 1800 seconds |
| 1 hour | 7200 seconds |

---

## FastAPI Middleware Implementation

### Rate Limit Middleware

```python
"""
Redis-based sliding window rate limiting middleware for FastAPI.
Applies global limits and endpoint-specific overrides.
"""
import time
import math
from typing import Optional, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from redis.asyncio import Redis

from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis: Redis):
        super().__init__(app)
        self.redis = redis
        self.endpoint_overrides = ENDPOINT_OVERRIDES

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks and internal endpoints
        if request.url.path in ("/health", "/ready", "/metrics"):
            return await call_next(request)

        # Determine rate limit parameters
        limit_config = self._resolve_limit_config(request)
        if limit_config is None:
            return await call_next(request)

        key, limit, window = limit_config

        # Check rate limit using sliding window
        allowed, current_count, reset_at = await self._check_rate_limit(
            key, limit, window
        )

        if not allowed:
            retry_after = max(1, reset_at - int(time.time()))
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": (
                        f"Has excedido el limite de solicitudes. "
                        f"Intenta de nuevo en {retry_after} segundos."
                    ),
                    "message_en": (
                        f"Rate limit exceeded. "
                        f"Try again in {retry_after} seconds."
                    ),
                    "details": {
                        "limit": limit,
                        "window_seconds": window,
                        "retry_after_seconds": retry_after,
                    },
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                    "Retry-After": str(retry_after),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to successful responses
        remaining = max(0, limit - current_count)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at)

        return response

    def _resolve_limit_config(
        self, request: Request
    ) -> Optional[Tuple[str, int, int]]:
        """
        Determine the rate limit key, limit, and window for this request.
        Returns (key, limit, window_seconds) or None to skip.
        """
        path = request.url.path
        method = request.method
        endpoint_key = f"{method} {path}"

        # Check endpoint-specific overrides first
        for pattern, config in self.endpoint_overrides.items():
            if self._match_endpoint(endpoint_key, pattern):
                key = self._build_key(config, request)
                return (key, config["limit"], config["window"])

        # Fall back to global limits
        user = getattr(request.state, "user", None)
        if user:
            tenant_id = getattr(request.state, "tenant_id", "unknown")
            plan_limits = self._get_plan_limits(request)
            key = f"rl:user:{tenant_id}:{user.id}:{self._current_window(60)}"
            return (key, plan_limits["user_limit"], 60)
        else:
            ip = self._get_client_ip(request)
            key = f"rl:ip:{ip}:{self._current_window(60)}"
            return (key, 20, 60)

    async def _check_rate_limit(
        self, key: str, limit: int, window: int
    ) -> Tuple[bool, int, int]:
        """
        Sliding window counter check.
        Returns (allowed, current_count, reset_timestamp).
        """
        now = time.time()
        current_window = int(now // window) * window
        previous_window = current_window - window

        current_key = f"{key}:{current_window}"
        previous_key = f"{key}:{previous_window}"

        pipe = self.redis.pipeline()
        pipe.get(previous_key)
        pipe.incr(current_key)
        pipe.expire(current_key, window * 2)
        results = await pipe.execute()

        previous_count = int(results[0] or 0)
        current_count = int(results[1])

        # Calculate weighted count using sliding window
        elapsed_in_window = now - current_window
        overlap = 1 - (elapsed_in_window / window)
        weighted_count = math.floor(previous_count * overlap) + current_count

        reset_at = current_window + window
        allowed = weighted_count <= limit

        if not allowed:
            # Decrement since we incremented optimistically
            await self.redis.decr(current_key)

        return (allowed, weighted_count, reset_at)

    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP, respecting X-Forwarded-For behind load balancer."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _current_window(self, window: int) -> int:
        return int(time.time() // window) * window

    def _match_endpoint(self, endpoint: str, pattern: str) -> bool:
        """Simple pattern matching supporting trailing wildcards."""
        if pattern.endswith("*"):
            return endpoint.startswith(pattern[:-1])
        return endpoint == pattern

    def _build_key(self, config: dict, request: Request) -> str:
        """Build the Redis key based on the rate limit scope."""
        scope = config["scope"]
        if scope == "ip":
            ip = self._get_client_ip(request)
            return f"rl:{config['name']}:{ip}"
        elif scope == "user":
            user = getattr(request.state, "user", None)
            tenant_id = getattr(request.state, "tenant_id", "unknown")
            user_id = user.id if user else "anon"
            return f"rl:{config['name']}:{tenant_id}:{user_id}"
        elif scope == "tenant":
            tenant_id = getattr(request.state, "tenant_id", "unknown")
            return f"rl:{config['name']}:{tenant_id}"
        return f"rl:{config['name']}:global"

    def _get_plan_limits(self, request: Request) -> dict:
        """Retrieve plan-based limits from request state (set by auth middleware)."""
        plan = getattr(request.state, "plan", "free")
        return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


# --------------------------------------------------------------------------
# Configuration Tables
# --------------------------------------------------------------------------

PLAN_LIMITS = {
    "free": {"user_limit": 60, "tenant_limit": 300},
    "pro": {"user_limit": 100, "tenant_limit": 1000},
    "enterprise": {"user_limit": 300, "tenant_limit": 5000},
}

ENDPOINT_OVERRIDES = {
    # Authentication (unauthenticated, IP-scoped)
    "POST /api/v1/auth/login": {
        "name": "login",
        "scope": "ip",
        "limit": 5,
        "window": 900,  # 15 minutes
    },
    "POST /api/v1/auth/register": {
        "name": "register",
        "scope": "ip",
        "limit": 3,
        "window": 3600,  # 1 hour
    },
    "POST /api/v1/auth/forgot-password": {
        "name": "forgot",
        "scope": "ip",
        "limit": 3,
        "window": 3600,
    },
    "POST /api/v1/auth/reset-password": {
        "name": "reset",
        "scope": "ip",
        "limit": 5,
        "window": 3600,
    },
    # Clinical (authenticated, user-scoped)
    "GET /api/v1/patients/search": {
        "name": "search",
        "scope": "user",
        "limit": 30,
        "window": 60,
    },
    "POST /api/v1/patients/*/odontogram/conditions": {
        "name": "odon",
        "scope": "user",
        "limit": 60,
        "window": 60,
    },
    "POST /api/v1/patients/import": {
        "name": "import",
        "scope": "tenant",
        "limit": 3,
        "window": 3600,
    },
    "GET /api/v1/patients/export": {
        "name": "export",
        "scope": "user",
        "limit": 5,
        "window": 3600,
    },
    # Compliance (authenticated, tenant-scoped)
    "POST /api/v1/compliance/rips/generate": {
        "name": "rips",
        "scope": "tenant",
        "limit": 5,
        "window": 3600,
    },
    "GET /api/v1/compliance/rips/export": {
        "name": "rips_export",
        "scope": "tenant",
        "limit": 10,
        "window": 3600,
    },
    # Public endpoints (unauthenticated, IP-scoped)
    "GET /api/v1/public/*": {
        "name": "public",
        "scope": "ip",
        "limit": 30,
        "window": 60,
    },
    "POST /api/v1/public/appointments/book": {
        "name": "book",
        "scope": "ip",
        "limit": 5,
        "window": 900,
    },
}
```

### Middleware Registration

```python
"""
Application startup: register rate limiting middleware.
"""
from fastapi import FastAPI
from redis.asyncio import Redis

from app.middleware.rate_limit import RateLimitMiddleware
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="DentalOS API", version="1.0.0")

    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)

    # Rate limiting must be applied BEFORE authentication middleware
    # so that unauthenticated endpoints are also protected.
    app.add_middleware(RateLimitMiddleware, redis=redis)

    return app
```

### Rate Limit Decorator (Alternative to Middleware)

For endpoints that need custom limits not covered by the middleware pattern matching, use a dependency-based approach.

```python
"""
Dependency-based rate limiting for individual endpoints.
Use when the middleware pattern matching is insufficient.
"""
from functools import wraps
from fastapi import Depends, HTTPException, Request
from redis.asyncio import Redis

from app.core.redis import get_redis


class RateLimitDep:
    """FastAPI dependency for per-endpoint rate limiting."""

    def __init__(self, key_prefix: str, limit: int, window: int, scope: str = "user"):
        self.key_prefix = key_prefix
        self.limit = limit
        self.window = window
        self.scope = scope

    async def __call__(
        self,
        request: Request,
        redis: Redis = Depends(get_redis),
    ) -> None:
        # Build key based on scope
        if self.scope == "ip":
            identifier = self._get_client_ip(request)
        elif self.scope == "tenant":
            identifier = getattr(request.state, "tenant_id", "unknown")
        else:
            user = getattr(request.state, "user", None)
            tenant_id = getattr(request.state, "tenant_id", "unknown")
            identifier = f"{tenant_id}:{user.id}" if user else "anon"

        import time, math
        now = time.time()
        current_window = int(now // self.window) * self.window
        key = f"rl:{self.key_prefix}:{identifier}:{current_window}"

        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, self.window * 2)

        if count > self.limit:
            reset_at = current_window + self.window
            retry_after = max(1, reset_at - int(time.time()))
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Limite excedido. Intenta en {retry_after}s.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


# Usage in a route:
# @router.post("/custom-endpoint")
# async def my_endpoint(
#     _rate_limit: None = Depends(RateLimitDep("custom", limit=10, window=60)),
# ):
#     ...
```

---

## Bypass Rules

The following requests bypass rate limiting entirely:

| Condition | Rationale |
|-----------|-----------|
| Health check endpoints (`/health`, `/ready`, `/metrics`) | Infrastructure monitoring must never be blocked |
| Superadmin requests (role = `superadmin`) | Platform operators need unrestricted access |
| Internal service-to-service calls (verified by shared secret header) | Background workers calling internal APIs |

Bypass is implemented as an early return in `_resolve_limit_config`. Superadmin bypass is checked after authentication middleware has set `request.state.user`.

---

## Monitoring and Alerting

### Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `rate_limit.rejected_total` | Total 429 responses by endpoint | > 50/min sustained |
| `rate_limit.rejected_by_ip` | 429 responses grouped by IP | > 20/min from single IP (possible attack) |
| `rate_limit.auth_failures` | Login rate limit hits | > 10/min (brute force attempt) |
| `redis.rate_limit_keys` | Total rate limit keys in Redis | > 100k (memory pressure) |

### Redis Memory

Rate limit keys are lightweight (< 100 bytes each). With 500 concurrent users, expected memory usage for rate limiting is under 10MB. TTL-based expiration ensures automatic cleanup.

---

## Testing Strategy

### Unit Tests

- Sliding window algorithm correctness (boundary conditions, window transitions)
- Key generation for each scope type
- Plan limit resolution
- Endpoint pattern matching

### Integration Tests

- Middleware rejects requests at exact limit boundary
- Rate limit headers are present on all responses
- 429 response format matches spec
- TTL expiration resets limits after window
- Bypass rules work for superadmin and health checks

### Load Tests

- Verify rate limiting under concurrent requests (k6 or locust)
- Confirm Redis performance does not degrade under rate limit traffic
- Test sliding window accuracy at window boundaries

---

## Out of Scope

This spec explicitly does NOT cover:

- DDoS protection at the network/infrastructure level (handled by Hetzner firewall or Cloudflare if added later)
- API key-based rate limiting for external integrations (future: see `integrations/` specs)
- WebSocket connection rate limiting (future enhancement)
- Geographic/country-based rate limiting
- Rate limit configuration UI in the admin dashboard (see `admin/` specs)
- Billing-based usage metering (see `billing/` specs; rate limiting is about protection, not billing)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec: sliding window algorithm, tier definitions, endpoint overrides, FastAPI middleware, Redis key design |
