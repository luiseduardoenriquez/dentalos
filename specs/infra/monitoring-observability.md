# Monitoring and Observability Spec

> **Spec ID:** I-15
> **Status:** Draft
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Comprehensive monitoring and observability stack for DentalOS. Structured JSON logging to Grafana Loki, distributed tracing via OpenTelemetry → Grafana Tempo, metrics via Prometheus → Grafana dashboards, and alerting via Telegram/PagerDuty for P1 incidents. The health check endpoint provides a quick system status overview.

**Domain:** infra

**Priority:** Critical

**Dependencies:** I-14 (deployment-architecture), I-11 (audit-logging)

---

## 1. Observability Stack Overview

```
App Servers + Worker Server
    │
    ├── Structured JSON logs → Promtail agent → Grafana Loki
    │
    ├── OpenTelemetry SDK → OTLP exporter → Grafana Tempo (traces)
    │
    ├── Prometheus metrics endpoint (/metrics)
    │        └── Prometheus scraper → Grafana
    │
    └── Health check endpoint (/api/v1/health)
              └── Uptime monitoring (Better Uptime / Hetzner LB)

Grafana (dashboards, alerting)
├── Data sources: Loki, Tempo, Prometheus
└── Alert rules → Telegram bot / PagerDuty
```

### Hosting

Grafana stack (Loki, Tempo, Prometheus, Grafana) hosted on the Worker Server (CPX31, 8GB RAM). For initial launch, these can share the worker server. When metrics volume grows, move to a dedicated monitoring server or Grafana Cloud.

---

## 2. Structured Logging

### Log Format

All application logs are structured JSON. Each log entry includes mandatory fields:

```python
import logging
import json
import time
import uuid
from typing import Optional


class StructuredJSONFormatter(logging.Formatter):
    """
    Formats log records as structured JSON for Loki ingestion.
    Mandatory fields: timestamp, level, service, tenant_id, user_id,
                     request_id, endpoint, duration_ms, message.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "dentalos-api",
            # Context (injected via contextvars or extra={}):
            "tenant_id": getattr(record, "tenant_id", None),
            "user_id": getattr(record, "user_id", None),
            "request_id": getattr(record, "request_id", None),
            "endpoint": getattr(record, "endpoint", None),
            "method": getattr(record, "method", None),
            "status_code": getattr(record, "status_code", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "trace_id": getattr(record, "trace_id", None),
            "span_id": getattr(record, "span_id", None),
        }

        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "id", "levelname", "levelno", "lineno", "module",
                "msecs", "message", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "thread", "threadName",
            ) and not key.startswith("_"):
                if key not in log_entry:
                    log_entry[key] = value

        # Remove None values for cleaner logs
        log_entry = {k: v for k, v in log_entry.items() if v is not None}

        # Exception handling
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False, default=str)
```

### Request Logging Middleware

```python
import time
import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

# Context variables for log enrichment
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)

        start_time = time.time()

        # Add request ID to response headers
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000)

        # Log request summary
        logger.info(
            "HTTP request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "endpoint": str(request.url.path),
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "tenant_id": tenant_id_var.get(""),
                "user_id": user_id_var.get(""),
            }
        )

        response.headers["X-Request-ID"] = request_id
        return response
```

### PHI-Safe Logging Rules

```python
# NEVER log these values — log their IDs/hashes only
PHI_FIELDS = {
    "patient_name", "patient_email", "patient_phone",
    "document_number", "address", "birth_date",
    "diagnosis", "prescription", "clinical_notes",
    "card_number", "bank_account",
}


def safe_log_context(data: dict) -> dict:
    """Strip PHI fields from log context before logging."""
    return {
        k: ("[REDACTED]" if k in PHI_FIELDS else v)
        for k, v in data.items()
    }
```

---

## 3. Log Aggregation — Grafana Loki

### Promtail Configuration

Promtail runs on each app server and worker server, tailing application log files:

```yaml
# /etc/promtail/config.yml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /var/lib/promtail/positions.yaml

clients:
  - url: http://10.0.0.10:3100/loki/api/v1/push  # Loki on worker server

scrape_configs:
  - job_name: dentalos-api
    static_configs:
      - targets: [localhost]
        labels:
          job: dentalos-api
          host: app-server-1
          __path__: /var/log/dentalos/gunicorn-access.log

  - job_name: dentalos-workers
    static_configs:
      - targets: [localhost]
        labels:
          job: dentalos-workers
          host: worker-1
          __path__: /var/log/dentalos/workers/*.log

  - job_name: nginx
    static_configs:
      - targets: [localhost]
        labels:
          job: nginx
          __path__: /var/log/nginx/access.log
```

### Useful Loki Queries

```logql
# All errors for a specific tenant
{job="dentalos-api"} | json | level="ERROR" | tenant_id="abc123"

# Slow requests (> 2 seconds)
{job="dentalos-api"} | json | duration_ms > 2000

# Failed DIAN submissions
{job="dentalos-workers"} | json | logger="app.integrations.matias" | level="ERROR"

# All requests for a specific endpoint
{job="dentalos-api"} | json | endpoint=~"/api/v1/appointments.*" | status_code >= 400
```

---

## 4. Distributed Tracing — OpenTelemetry + Grafana Tempo

### OpenTelemetry Setup

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor


def setup_tracing(app) -> None:
    """Initialize OpenTelemetry tracing for DentalOS."""
    provider = TracerProvider()

    otlp_exporter = OTLPSpanExporter(
        endpoint="http://10.0.0.10:4317",  # Grafana Tempo on worker server
        insecure=True,
    )
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Auto-instrument SQLAlchemy (DB queries)
    SQLAlchemyInstrumentor().instrument()

    # Auto-instrument Redis
    RedisInstrumentor().instrument()

    # Auto-instrument RabbitMQ
    AioPikaInstrumentor().instrument()
```

### Trace Context in Logs

```python
from opentelemetry import trace as otel_trace


class OpenTelemetryLogFilter(logging.Filter):
    """Inject trace_id and span_id into log records from active OTel span."""

    def filter(self, record: logging.LogRecord) -> bool:
        current_span = otel_trace.get_current_span()
        ctx = current_span.get_span_context()
        if ctx.is_valid:
            record.trace_id = format(ctx.trace_id, "032x")
            record.span_id = format(ctx.span_id, "016x")
        return True
```

This allows correlating a Loki log entry directly to a Tempo trace using the `trace_id` field.

---

## 5. Metrics — Prometheus

### Prometheus Metrics Endpoint

```python
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, generate_latest, CONTENT_TYPE_LATEST
)
from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()

# Define metrics
REQUEST_COUNT = Counter(
    "dentalos_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "dentalos_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

ACTIVE_TENANTS = Gauge(
    "dentalos_active_tenants_total",
    "Number of active tenants",
)

APPOINTMENTS_CREATED = Counter(
    "dentalos_appointments_created_total",
    "Total appointments created",
    ["tenant_country"],
)

QUEUE_DEPTH = Gauge(
    "dentalos_queue_depth",
    "RabbitMQ queue depth",
    ["queue_name"],
)

CACHE_HITS = Counter(
    "dentalos_cache_hits_total",
    "Redis cache hits",
    ["cache_key_pattern"],
)

CACHE_MISSES = Counter(
    "dentalos_cache_misses_total",
    "Redis cache misses",
    ["cache_key_pattern"],
)

DB_CONNECTIONS = Gauge(
    "dentalos_db_connections_active",
    "Active database connections",
)


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
```

### Metrics Recording Middleware

```python
import time

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        # Normalize endpoint for cardinality control
        endpoint = normalize_endpoint(str(request.url.path))

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)

        return response


def normalize_endpoint(path: str) -> str:
    """
    Replace UUIDs and numeric IDs with placeholders to prevent high cardinality.
    /api/v1/patients/f47ac10b-... → /api/v1/patients/{id}
    /api/v1/appointments/123 → /api/v1/appointments/{id}
    """
    import re
    path = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "{id}", path)
    path = re.sub(r"/[0-9]+", "/{id}", path)
    return path
```

### Prometheus Scrape Config

```yaml
# /etc/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: dentalos-api
    static_configs:
      - targets:
          - 10.0.0.1:8000   # App Server 1
          - 10.0.0.2:8000   # App Server 2
    metrics_path: /metrics
    scheme: http

  - job_name: dentalos-workers
    static_configs:
      - targets: [10.0.0.10:9090]
    metrics_path: /metrics

  - job_name: postgresql
    static_configs:
      - targets: [10.0.0.20:9187]  # postgres_exporter

  - job_name: redis
    static_configs:
      - targets: [10.0.0.30:9121]  # redis_exporter

  - job_name: rabbitmq
    static_configs:
      - targets: [10.0.0.10:15692]  # RabbitMQ Prometheus plugin
```

---

## 6. Grafana Dashboards

### Dashboard: System Overview

**Panels:**
- Request rate (req/s) — by endpoint and method
- Error rate (%) — 4xx and 5xx
- Request latency p50/p95/p99 (histogram)
- Active DB connections
- Cache hit rate (%)
- Queue depth per queue
- Active tenant count

### Dashboard: Business Metrics

**Panels:**
- Appointments created / day / week
- Invoices issued (by country)
- Active WhatsApp conversations
- SMS delivery rate
- Patient registrations per day
- New tenant signups per week

### Dashboard: Infrastructure Health

**Panels:**
- CPU usage per server
- Memory usage per server
- Disk I/O
- Network throughput
- PostgreSQL: slow queries, connections, replication lag
- Redis: memory usage, hit rate, evictions
- RabbitMQ: messages/s, consumer count, queue depth

### Dashboard: Error Tracking

**Panels:**
- Top error endpoints (last 1h)
- Error log stream (Loki)
- Failed background jobs per queue
- DIAN/MATIAS submission failures
- WhatsApp/SMS delivery failures

---

## 7. Alerting

### Alert Severity Levels

| Level | Description | Response Time | Notification Channel |
|-------|-------------|--------------|---------------------|
| P1 — Critical | System down, data loss risk | Immediate (24/7) | Telegram + PagerDuty |
| P2 — High | Significant degradation | < 30 minutes | Telegram |
| P3 — Medium | Partial degradation | < 4 hours (business hours) | Telegram |
| P4 — Low | Warning, no user impact | Next business day | Email |

### Alert Rules

```yaml
# Grafana alert rules (Prometheus alerting rules format)

groups:
  - name: p1-critical
    rules:
      - alert: APIDown
        expr: up{job="dentalos-api"} == 0
        for: 2m
        labels:
          severity: p1
        annotations:
          summary: "DentalOS API server down"
          description: "API server {{ $labels.instance }} has been down for 2+ minutes"

      - alert: DatabaseConnectionLost
        expr: pg_up == 0
        for: 1m
        labels:
          severity: p1
        annotations:
          summary: "PostgreSQL connection lost"

      - alert: HighErrorRate
        expr: |
          rate(dentalos_http_requests_total{status_code=~"5.."}[5m])
          / rate(dentalos_http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: p1
        annotations:
          summary: "Error rate > 5% for 5 minutes"
          description: "Current error rate: {{ $value | humanizePercentage }}"

  - name: p2-high
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.95, dentalos_http_request_duration_seconds_bucket) > 2
        for: 5m
        labels:
          severity: p2
        annotations:
          summary: "p95 latency > 2 seconds"

      - alert: QueueDepthHigh
        expr: dentalos_queue_depth > 1000
        for: 10m
        labels:
          severity: p2
        annotations:
          summary: "RabbitMQ queue {{ $labels.queue_name }} depth > 1000"

      - alert: RedisMemoryHigh
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.85
        for: 15m
        labels:
          severity: p2
        annotations:
          summary: "Redis memory usage > 85%"

      - alert: CertificateExpiringSoon
        expr: ssl_certificate_expiry_seconds < 30 * 86400
        for: 1h
        labels:
          severity: p2
        annotations:
          summary: "SSL certificate expires in < 30 days"

  - name: p3-medium
    rules:
      - alert: LowCacheHitRate
        expr: |
          rate(dentalos_cache_hits_total[1h])
          / (rate(dentalos_cache_hits_total[1h]) + rate(dentalos_cache_misses_total[1h])) < 0.5
        for: 30m
        labels:
          severity: p3
        annotations:
          summary: "Cache hit rate < 50%"

      - alert: DIANSubmissionFailures
        expr: increase(dentalos_dian_failures_total[1h]) > 10
        for: 0m
        labels:
          severity: p3
        annotations:
          summary: "10+ DIAN submission failures in the last hour"
```

### Telegram Alert Bot

```python
import httpx
from app.core.config import settings


async def send_telegram_alert(
    severity: str,
    summary: str,
    description: str,
) -> None:
    """Send alert to Telegram channel."""
    emoji_map = {"p1": "🚨", "p2": "⚠️", "p3": "📋", "p4": "ℹ️"}
    emoji = emoji_map.get(severity.lower(), "📢")

    message = (
        f"{emoji} *DentalOS Alert — {severity.upper()}*\n\n"
        f"*{summary}*\n\n"
        f"{description}\n\n"
        f"_Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}_"
    )

    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": settings.TELEGRAM_ALERT_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
            },
        )
```

---

## 8. Health Check Endpoint

```python
@router.get("/api/v1/health")
async def health_check():
    """
    System health check for load balancer and uptime monitoring.
    Returns overall status and per-component status.
    """
    start = time.time()
    checks = {}

    # Database check
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy"}
    except Exception as e:
        checks["database"] = {"status": "degraded", "error": "connection_failed"}

    # Redis check
    try:
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = {"status": "healthy"}
    except Exception:
        checks["redis"] = {"status": "degraded"}

    # RabbitMQ check (non-blocking)
    try:
        conn = await aio_pika.connect_robust(settings.RABBITMQ_URL, timeout=3)
        await conn.close()
        checks["rabbitmq"] = {"status": "healthy"}
    except Exception:
        checks["rabbitmq"] = {"status": "degraded"}

    # S3/Object Storage check (non-blocking)
    try:
        storage = StorageService()
        storage.client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        checks["storage"] = {"status": "healthy"}
    except Exception:
        checks["storage"] = {"status": "degraded"}

    duration_ms = round((time.time() - start) * 1000)
    is_healthy = checks["database"]["status"] == "healthy"

    return JSONResponse(
        content={
            "status": "healthy" if is_healthy else "degraded",
            "version": settings.APP_VERSION,
            "uptime_seconds": get_uptime_seconds(),
            "checks": checks,
            "duration_ms": duration_ms,
        },
        status_code=200 if is_healthy else 503,
    )
```

---

## 9. Error Tracking — Sentry

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration


def setup_sentry() -> None:
    """Initialize Sentry error tracking."""
    if not settings.SENTRY_DSN:
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
        traces_sample_rate=0.1,   # 10% of transactions traced in Sentry
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
        # PHI protection: scrub sensitive data before sending to Sentry
        before_send=scrub_phi_from_sentry_event,
        ignore_errors=[
            # Don't send 4xx errors to Sentry (client errors)
            HTTPException,
        ],
    )


def scrub_phi_from_sentry_event(event: dict, hint: dict) -> dict:
    """Remove PHI from Sentry events before transmission."""
    if "request" in event:
        # Scrub request body
        if "data" in event["request"]:
            event["request"]["data"] = "[REDACTED]"
        # Scrub authorization headers
        if "headers" in event["request"]:
            event["request"]["headers"].pop("authorization", None)

    # Scrub extra context
    for key in PHI_FIELDS:
        event.get("extra", {}).pop(key, None)

    return event
```

---

## 10. Uptime Monitoring

External uptime monitoring using **Better Uptime** (or equivalent):

| Check | URL | Frequency | Alert if down for |
|-------|-----|-----------|-------------------|
| API health | `https://api.dentalos.app/api/v1/health` | 1 minute | 2 minutes |
| Frontend | `https://app.dentalos.app` | 1 minute | 2 minutes |
| Patient portal | `https://portal.dentalos.app` | 5 minutes | 5 minutes |

---

## Out of Scope

- Application Performance Management (APM) beyond OpenTelemetry
- Log-based billing analytics (use dedicated analytics service)
- Real user monitoring (RUM) for frontend
- Synthetic transaction monitoring
- SIEM (Security Information and Event Management) — future

---

## Acceptance Criteria

**This spec is complete when:**

- [ ] All app logs formatted as structured JSON with tenant_id, request_id
- [ ] Promtail shipping logs to Loki
- [ ] Grafana dashboard shows request rate, error rate, latency p95
- [ ] Prometheus scraping all app servers every 15 seconds
- [ ] P1 alert fires within 2 minutes of API going down
- [ ] Telegram bot receives P1 alert within 3 minutes of incident
- [ ] Sentry capturing exceptions (with PHI scrubbed)
- [ ] Health check endpoint responds within 500ms
- [ ] Trace IDs appear in Loki logs and correlate to Tempo traces

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
