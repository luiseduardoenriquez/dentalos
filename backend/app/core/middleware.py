import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

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
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        # Only send HSTS when the connection was served over HTTPS
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
    import json

    try:
        # JWT format: header.payload.signature — decode payload
        parts = token.split(".")
        if len(parts) != 3:
            return ("", "")
        # Add padding for base64
        payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return (data.get("tid", ""), data.get("sub", ""))
    except Exception:
        return ("", "")
