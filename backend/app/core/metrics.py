"""Prometheus metrics registry for DentalOS.

Centralizes all application metrics. Exposed via GET /api/v1/metrics.
"""

import re

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

# Use a custom registry to avoid default process/platform collectors
# that may leak host information in multi-tenant environments.
REGISTRY = CollectorRegistry()

# ─── HTTP Metrics ──────────────────────────────────────
http_requests_total = Counter(
    "dentalos_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY,
)

http_request_duration_seconds = Histogram(
    "dentalos_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

http_requests_in_progress = Gauge(
    "dentalos_http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method"],
    registry=REGISTRY,
)

# ─── Database Pool Metrics ──────────────────────────────
db_pool_size = Gauge(
    "dentalos_db_pool_size",
    "Database connection pool size by state",
    ["state"],
    registry=REGISTRY,
)

# ─── Cache Metrics ──────────────────────────────────────
cache_operations_total = Counter(
    "dentalos_cache_operations_total",
    "Total cache operations",
    ["operation", "domain"],
    registry=REGISTRY,
)

# ─── Queue Metrics ──────────────────────────────────────
queue_depth = Gauge(
    "dentalos_queue_depth",
    "RabbitMQ queue depth",
    ["queue_name"],
    registry=REGISTRY,
)

# ─── Business Metrics ──────────────────────────────────
active_tenants = Gauge(
    "dentalos_active_tenants",
    "Number of active tenants",
    registry=REGISTRY,
)

appointments_today = Gauge(
    "dentalos_appointments_today",
    "Number of appointments scheduled for today",
    registry=REGISTRY,
)


# ─── Path Normalization ────────────────────────────────
# Collapse dynamic segments to avoid label cardinality explosion.
# UUIDs (with or without dashes) and integer IDs are normalized.
_UUID_RE = re.compile(
    r"/[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}",
    re.IGNORECASE,
)
_INT_ID_RE = re.compile(r"/\d+(?=/|$)")


def normalize_path(path: str) -> str:
    """Normalize a URL path by replacing dynamic segments with {id}.

    Examples:
        /api/v1/patients/550e8400-e29b-41d4-a716-446655440000 → /api/v1/patients/{id}
        /api/v1/patients/123/records/456 → /api/v1/patients/{id}/records/{id}
    """
    path = _UUID_RE.sub("/{id}", path)
    path = _INT_ID_RE.sub("/{id}", path)
    return path


# ─── Helper Functions ──────────────────────────────────
def record_cache_hit(domain: str) -> None:
    """Record a cache hit for the given domain."""
    cache_operations_total.labels(operation="hit", domain=domain).inc()


def record_cache_miss(domain: str) -> None:
    """Record a cache miss for the given domain."""
    cache_operations_total.labels(operation="miss", domain=domain).inc()


def record_cache_set(domain: str) -> None:
    """Record a cache set for the given domain."""
    cache_operations_total.labels(operation="set", domain=domain).inc()


def record_cache_delete(domain: str) -> None:
    """Record a cache delete for the given domain."""
    cache_operations_total.labels(operation="delete", domain=domain).inc()


def update_db_pool_stats(checked_in: int, checked_out: int, overflow: int) -> None:
    """Update database pool gauges."""
    db_pool_size.labels(state="idle").set(checked_in)
    db_pool_size.labels(state="active").set(checked_out)
    db_pool_size.labels(state="overflow").set(overflow)


def update_queue_depth(queue_name: str, depth: int) -> None:
    """Update the queue depth gauge for a given queue."""
    queue_depth.labels(queue_name=queue_name).set(depth)
