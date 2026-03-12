import json
import logging
import time
import uuid
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.metrics import (
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
    normalize_path,
)

logger = logging.getLogger("dentalos.http")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        # Skip CSP on API responses — the frontend's Next.js config handles CSP for
        # the browser.  Backend CSP on JSON responses is redundant and causes conflicts
        # (duplicate headers) when proxied through Next.js rewrites.
        is_api = request.url.path.startswith("/api/")
        if not is_api:
            if settings.debug:
                connect_src = "connect-src 'self' https: http://localhost:*"
            else:
                connect_src = "connect-src 'self'"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "font-src 'self'; "
                f"{connect_src}; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        # Skip HSTS in debug mode to avoid protocol confusion through proxies (ngrok)
        if not settings.debug:
            if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains; preload"
                )
        if "server" in response.headers:
            del response.headers["server"]
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect Prometheus HTTP metrics for every request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method
        http_requests_in_progress.labels(method=method).inc()
        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            # Count 500s on unhandled exceptions
            endpoint = normalize_path(request.url.path)
            http_requests_total.labels(method=method, endpoint=endpoint, status_code="500").inc()
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
                time.monotonic() - start
            )
            raise
        finally:
            http_requests_in_progress.labels(method=method).dec()

        endpoint = normalize_path(request.url.path)
        http_requests_total.labels(
            method=method, endpoint=endpoint, status_code=str(response.status_code)
        ).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
            time.monotonic() - start
        )
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log requests with timing and inject X-Request-ID header."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Extract tenant_id and user_id from JWT for logging (decode header only, no verification)
        tenant_id = ""
        user_id = ""
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            tenant_id, user_id = _extract_jwt_claims(auth_header[7:])

        response = await call_next(request)

        duration_ms = round((time.time() - start_time) * 1000)

        logger.info(
            "HTTP %s %s → %d (%dms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "request_id": request_id,
                "method": request.method,
                "endpoint": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "tenant_id": tenant_id,
                "user_id": user_id,
            },
        )

        response.headers["X-Request-ID"] = request_id
        return response


def _extract_jwt_claims(token: str) -> tuple[str, str]:
    """Extract tenant_id and user_id from a JWT without verification.

    Only used for logging enrichment — never for auth decisions.
    Returns ("", "") on any parsing failure.
    """
    import base64
    import json as _json

    try:
        # JWT format: header.payload.signature — decode payload
        parts = token.split(".")
        if len(parts) != 3:
            return ("", "")
        # Add padding for base64
        payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
        data = _json.loads(base64.urlsafe_b64decode(payload))
        return (data.get("tid", ""), data.get("sub", ""))
    except Exception:
        return ("", "")


class ApiMetricsMiddleware(BaseHTTPMiddleware):
    """Write API usage counters to Redis for the admin API metrics dashboard.

    Populates the keys that ``admin_service.get_api_usage_metrics()`` reads:
    - ``dentalos:api:hourly:{YYYYMMDDHH}`` — request count per hour (TTL 25h)
    - ``dentalos:api:errors:24h`` — error count rolling window (TTL 25h)
    - ``dentalos:api:endpoint:{method}:{path}:count`` — per-endpoint count (TTL 25h)
    - ``dentalos:api:endpoint:{method}:{path}:errors`` — per-endpoint errors (TTL 25h)
    - ``dentalos:api:endpoint:{method}:{path}:latency_sum`` — cumulative ms (TTL 25h)
    - ``dentalos:api:tenant:{tid}:count`` — per-tenant count (TTL 25h)
    - ``dentalos:api:latency:samples`` — sorted set of recent latencies (TTL 25h)

    All writes are fire-and-forget so they never block the request.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.monotonic()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.monotonic() - start) * 1000, 1)
            endpoint = normalize_path(request.url.path)
            method = request.method

            # Extract tenant_id for per-tenant metrics
            tenant_id = ""
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                tenant_id, _ = _extract_jwt_claims(auth_header[7:])

            # Fire-and-forget Redis writes
            try:
                from app.core.redis import redis_client

                now = datetime.now(UTC)
                hour_key = f"dentalos:api:hourly:{now.strftime('%Y%m%d%H')}"
                ttl = 90000  # 25 hours

                pipe = redis_client.pipeline(transaction=False)

                # Hourly bucket
                pipe.incr(hour_key)
                pipe.expire(hour_key, ttl)

                # Per-endpoint counters
                ep_key = f"dentalos:api:endpoint:{method}:{endpoint}"
                pipe.incr(f"{ep_key}:count")
                pipe.expire(f"{ep_key}:count", ttl)
                pipe.incrbyfloat(f"{ep_key}:latency_sum", duration_ms)
                pipe.expire(f"{ep_key}:latency_sum", ttl)

                # Errors
                if status_code >= 400:
                    pipe.incr("dentalos:api:errors:24h")
                    pipe.expire("dentalos:api:errors:24h", ttl)
                    pipe.incr(f"{ep_key}:errors")
                    pipe.expire(f"{ep_key}:errors", ttl)

                # Per-tenant
                if tenant_id:
                    t_key = f"dentalos:api:tenant:{tenant_id}:count"
                    pipe.incr(t_key)
                    pipe.expire(t_key, ttl)

                # Latency samples (sorted set — score = latency, member = timestamp)
                sample_key = "dentalos:api:latency:samples"
                pipe.zadd(sample_key, {f"{now.timestamp()}": duration_ms})
                pipe.expire(sample_key, ttl)
                # Trim to last 10000 samples
                pipe.zremrangebyrank(sample_key, 0, -10001)

                await pipe.execute()
            except Exception:
                # Never let metrics break a request
                pass


class MaintenanceMiddleware(BaseHTTPMiddleware):
    """Enforce maintenance mode by returning 503 on non-admin API routes.

    Checks the Redis key ``dentalos:global:maintenance``. When set, its value
    is a JSON object with ``message`` and optional ``ends_at`` ISO timestamp.
    Admin routes (``/api/v1/admin/``) are always allowed through so superadmins
    can manage maintenance mode. Health check endpoints (``/api/v1/health``)
    are also exempt.
    """

    # Prefixes that bypass maintenance mode
    _EXEMPT_PREFIXES = ("/api/v1/admin/", "/api/v1/health", "/docs", "/redoc", "/openapi.json")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Only gate API requests
        if not path.startswith("/api/"):
            return await call_next(request)

        # Exempt admin and health routes
        for prefix in self._EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Check maintenance flag in Redis
        try:
            from app.core.redis import redis_client

            raw = await redis_client.get("dentalos:global:maintenance")
            if raw:
                data = json.loads(raw) if isinstance(raw, str) else {}
                message = data.get("message", "El sistema se encuentra en mantenimiento programado.")

                # Check if maintenance has expired
                ends_at = data.get("ends_at")
                if ends_at:
                    end_dt = datetime.fromisoformat(ends_at)
                    if datetime.now(UTC) >= end_dt:
                        # Maintenance period has ended — auto-clear the key
                        await redis_client.delete("dentalos:global:maintenance")
                        return await call_next(request)

                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "SYSTEM_maintenance_mode",
                        "message": message,
                        "details": {"ends_at": ends_at},
                    },
                    headers={"Retry-After": "300"},
                )
        except Exception:
            # If Redis is down, don't block requests
            pass

        return await call_next(request)
