# Background Processing Spec

> **Spec ID:** I-06
> **Status:** Draft
> **Last Updated:** 2026-02-24

---

## Overview

**Feature:** RabbitMQ-based asynchronous task processing for DentalOS. Handles all background work including notification dispatch, clinical document generation, data import/export, and system maintenance tasks.

**Domain:** infra

**Priority:** Critical

**Dependencies:** I-01 (multi-tenancy), I-04 (database-architecture)

---

## Architecture

### Why RabbitMQ

See `infra/adr/008-rabbitmq-over-celery-redis.md` for the full decision record. Summary: RabbitMQ provides native priority queues, dead letter exchanges, durable message persistence, and better backpressure handling than Celery+Redis for healthcare workloads where message loss is unacceptable.

### Connection Architecture

```
FastAPI API Server(s)
       |
       | (publish messages via aio-pika)
       v
   RabbitMQ Broker
   ├── Exchange: dentalos.direct (direct exchange)
   │   ├── Queue: notifications  (routing key: notifications)
   │   ├── Queue: clinical       (routing key: clinical)
   │   ├── Queue: import         (routing key: import)
   │   └── Queue: maintenance    (routing key: maintenance)
   │
   └── Exchange: dentalos.dlx (dead letter exchange)
       └── Queue: dead_letter    (all failed messages after max retries)

Worker Pool (separate processes)
   ├── notification-worker (x2)
   ├── clinical-worker     (x2)
   ├── import-worker       (x1)
   └── maintenance-worker  (x1)
```

Each worker connects to tenant schemas dynamically using the `tenant_id` from the message payload. Workers use the same SQLAlchemy engine/session factory as the API server, resolving the tenant schema via `search_path` per connection.

---

## Queue Topology

### 1. `notifications` Queue

**Purpose:** Dispatch all outbound communications.

**Job types:**

| Job Type | Description | Priority |
|----------|-------------|----------|
| `email.send` | Transactional email via SMTP/SendGrid | 5 (high) |
| `whatsapp.send` | WhatsApp message via Meta Business API | 5 (high) |
| `sms.send` | SMS via Twilio or local provider | 5 (high) |
| `email.bulk` | Marketing/batch email (appointment reminders) | 3 (medium) |
| `whatsapp.appointment_reminder` | 24h/1h appointment reminders | 4 (medium-high) |
| `notification.in_app` | In-app notification persistence | 2 (low) |

**Workers:** 2 concurrent workers. Each worker processes one message at a time with prefetch count of 10.

**Concurrency rationale:** Notification delivery is I/O-bound (waiting on external APIs). Two workers provide redundancy and parallelism without overwhelming external rate limits.

### 2. `clinical` Queue

**Purpose:** Generate clinical documents and compliance reports.

**Job types:**

| Job Type | Description | Priority |
|----------|-------------|----------|
| `rips.generate` | Generate RIPS compliance files (Colombia Resolucion 3374) | 5 (high) |
| `pdf.treatment_plan` | Generate treatment plan PDF for patient signature | 4 (medium-high) |
| `pdf.consent_form` | Generate consent form PDF | 4 (medium-high) |
| `pdf.invoice` | Generate invoice/billing PDF | 3 (medium) |
| `pdf.prescription` | Generate prescription PDF | 4 (medium-high) |
| `pdf.clinical_summary` | Generate full clinical summary for referral/export | 2 (low) |
| `odontogram.snapshot_render` | Render odontogram snapshot to PNG/SVG | 2 (low) |

**Workers:** 2 concurrent workers. PDF generation is CPU-bound; workers are isolated to prevent resource contention with API processes.

**Concurrency rationale:** Clinical document generation involves PDF rendering (WeasyPrint/ReportLab) which is CPU-intensive. Two workers prevent a single long PDF job from blocking other clinical tasks.

### 3. `import` Queue

**Purpose:** Handle bulk data operations.

**Job types:**

| Job Type | Description | Priority |
|----------|-------------|----------|
| `patient.csv_import` | Parse and import patients from CSV/Excel upload | 3 (medium) |
| `patient.data_migration` | Migrate patient data from external system | 2 (low) |
| `patient.bulk_export` | Generate CSV/Excel export of patient list | 2 (low) |
| `data.tenant_seed` | Seed initial data for new tenant (catalogs, templates) | 5 (high) |

**Workers:** 1 worker. Import jobs are long-running (minutes) and should not compete for resources. Single worker prevents concurrent imports from overwhelming the database.

**Concurrency rationale:** Imports perform many sequential database writes. A single worker with proper batch sizes (100 rows per commit) prevents database connection exhaustion. Users receive progress updates via WebSocket or polling.

### 4. `maintenance` Queue

**Purpose:** System housekeeping and analytics.

**Job types:**

| Job Type | Description | Priority |
|----------|-------------|----------|
| `audit.archive` | Archive audit logs older than configurable threshold to cold storage | 2 (low) |
| `audit.write` | Write audit log entry (async from API request) | 4 (medium-high) |
| `tenant.cleanup` | Clean up expired sessions, temp files, orphaned records | 1 (lowest) |
| `analytics.aggregate` | Aggregate daily/weekly/monthly analytics per tenant | 2 (low) |
| `analytics.usage_snapshot` | Capture tenant usage metrics for plan enforcement | 3 (medium) |
| `tenant.schema_migrate` | Run Alembic migrations on tenant schema | 5 (high) |

**Workers:** 1 worker. Maintenance tasks are low-priority, scheduled, and must not interfere with clinical operations.

**Concurrency rationale:** Maintenance tasks run during off-peak hours (scheduled via cron publisher). A single worker prevents resource contention with production traffic.

---

## Message Format

All messages follow a standardized envelope format.

```json
{
  "message_id": "uuid-v4",
  "tenant_id": "tn_abc123",
  "job_type": "email.send",
  "payload": {
    "to": "patient@example.com",
    "template": "appointment_reminder",
    "variables": {
      "patient_name": "Carlos Rodriguez",
      "appointment_date": "2026-03-01T10:00:00-05:00",
      "doctor_name": "Dra. Maria Garcia"
    }
  },
  "priority": 5,
  "retry_count": 0,
  "max_retries": 3,
  "created_at": "2026-02-24T15:30:00Z",
  "correlation_id": "req_xyz789",
  "initiated_by": "usr_def456"
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message_id` | UUID v4 | Yes | Unique message identifier for idempotency |
| `tenant_id` | string | Yes | Tenant identifier. Worker uses this to resolve the correct PostgreSQL schema |
| `job_type` | string | Yes | Dot-notation job type matching queue handler registry |
| `payload` | object | Yes | Job-specific data. Schema varies by `job_type` |
| `priority` | integer (1-10) | Yes | RabbitMQ priority. 10 = highest, 1 = lowest |
| `retry_count` | integer | Yes | Current retry attempt. Starts at 0 |
| `max_retries` | integer | Yes | Maximum retry attempts before dead-lettering |
| `created_at` | ISO 8601 | Yes | Timestamp of original publish |
| `correlation_id` | string | No | Request ID from the originating API call for tracing |
| `initiated_by` | string | No | User ID who triggered the job |

### Priority Scale

| Priority | Value | Use Case |
|----------|-------|----------|
| Critical | 8-10 | Tenant provisioning, schema migrations |
| High | 5-7 | Clinical notifications, consent forms, prescriptions |
| Medium | 3-4 | Billing PDFs, bulk email, analytics |
| Low | 1-2 | Archival, cleanup, cold exports |

Global priority ordering across all queues: clinical notifications > clinical documents > billing > analytics > maintenance.

---

## Retry Policies

### Exponential Backoff

Failed messages are retried with exponential backoff using the `x-death` header mechanism.

```
Attempt 1: Immediate processing
Attempt 2: 30 seconds delay
Attempt 3: 120 seconds delay (2 minutes)
Attempt 4: Dead letter queue (no further retries)
```

Formula: `delay = base_delay * (2 ^ retry_count)` where `base_delay = 30 seconds`.

### Per-Job-Type Retry Overrides

| Job Type | Max Retries | Backoff Base | Rationale |
|----------|-------------|--------------|-----------|
| `email.send` | 5 | 60s | External SMTP may be temporarily unavailable |
| `whatsapp.send` | 3 | 30s | Meta API has its own retry logic |
| `sms.send` | 3 | 30s | Similar to WhatsApp |
| `rips.generate` | 2 | 60s | Deterministic -- if data is bad, retrying won't help |
| `pdf.*` | 3 | 30s | Usually succeeds on retry if resource contention |
| `patient.csv_import` | 1 | 0s | User should re-upload if import fails |
| `audit.write` | 5 | 15s | Audit logs must not be lost |
| `tenant.schema_migrate` | 1 | 0s | Migrations are idempotent but need manual review on failure |

### Dead Letter Queue

Messages that exhaust all retries are routed to `dentalos.dlx` exchange and land in the `dead_letter` queue.

**Dead letter message enrichment:**
```json
{
  "original_message": { "...original envelope..." },
  "failure_reason": "ConnectionRefusedError: SMTP server unreachable",
  "failed_at": "2026-02-24T15:35:00Z",
  "total_attempts": 4,
  "queue_origin": "notifications"
}
```

**Dead letter handling:**
1. Messages are persisted in the `dead_letter` queue indefinitely (durable)
2. Monitoring alert fires when dead letter queue depth exceeds 10 messages
3. Superadmin dashboard shows dead letter queue contents with retry/discard actions
4. Manual retry re-publishes the original message to its origin queue with `retry_count` reset
5. Critical job types (`audit.write`, `tenant.schema_migrate`) trigger immediate PagerDuty/Slack alerts

---

## Worker Implementation

### Worker Process Architecture

Each worker is a standalone Python process managed by systemd (production) or Docker Compose (development). Workers share the same codebase as the API server but run a different entrypoint.

```
dentalos/
├── app/
│   ├── api/          # FastAPI routes
│   ├── workers/
│   │   ├── base.py           # Base worker class
│   │   ├── notification.py   # Notification worker handlers
│   │   ├── clinical.py       # Clinical document worker handlers
│   │   ├── import_worker.py  # Import worker handlers
│   │   └── maintenance.py    # Maintenance worker handlers
│   ├── jobs/
│   │   ├── registry.py       # Job type -> handler mapping
│   │   ├── publisher.py      # Message publishing utilities
│   │   └── schemas.py        # Pydantic models for job payloads
│   └── core/
│       ├── database.py       # Shared DB session factory
│       └── tenant.py         # Tenant schema resolution
```

### Base Worker (Python)

```python
"""
Base worker class for DentalOS background processing.
All workers inherit from this to get tenant-aware database access,
structured logging, and retry handling.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Callable, Dict

import aio_pika
from aio_pika import IncomingMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_tenant_session
from app.jobs.registry import JobRegistry

logger = logging.getLogger("dentalos.worker")


class BaseWorker:
    def __init__(self, queue_name: str, prefetch_count: int = 10):
        self.queue_name = queue_name
        self.prefetch_count = prefetch_count
        self.registry = JobRegistry()
        self._connection = None
        self._channel = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(
            settings.RABBITMQ_URL,
            heartbeat=60,
            blocked_connection_timeout=300,
        )
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=self.prefetch_count)

    async def start(self) -> None:
        await self.connect()
        queue = await self._channel.declare_queue(
            self.queue_name,
            durable=True,
            arguments={
                "x-max-priority": 10,
                "x-dead-letter-exchange": "dentalos.dlx",
                "x-dead-letter-routing-key": "dead_letter",
            },
        )
        await queue.consume(self._process_message)
        logger.info(
            "Worker started",
            extra={"queue": self.queue_name, "prefetch": self.prefetch_count},
        )

    async def _process_message(self, message: IncomingMessage) -> None:
        async with message.process(requeue=False):
            body = json.loads(message.body.decode())
            tenant_id = body["tenant_id"]
            job_type = body["job_type"]
            message_id = body["message_id"]

            logger.info(
                "Processing job",
                extra={
                    "message_id": message_id,
                    "tenant_id": tenant_id,
                    "job_type": job_type,
                    "retry_count": body.get("retry_count", 0),
                },
            )

            handler = self.registry.get_handler(job_type)
            if handler is None:
                logger.error(
                    "No handler registered for job type",
                    extra={"job_type": job_type, "message_id": message_id},
                )
                return  # Message is acked and discarded

            try:
                async with get_tenant_session(tenant_id) as session:
                    await handler(session, body["payload"], body)
                logger.info(
                    "Job completed",
                    extra={
                        "message_id": message_id,
                        "tenant_id": tenant_id,
                        "job_type": job_type,
                    },
                )
            except Exception as exc:
                await self._handle_failure(body, exc)

    async def _handle_failure(self, body: dict, exc: Exception) -> None:
        retry_count = body.get("retry_count", 0)
        max_retries = body.get("max_retries", 3)
        message_id = body["message_id"]

        logger.error(
            "Job failed",
            extra={
                "message_id": message_id,
                "tenant_id": body["tenant_id"],
                "job_type": body["job_type"],
                "retry_count": retry_count,
                "error": str(exc),
            },
            exc_info=True,
        )

        if retry_count < max_retries:
            delay_seconds = 30 * (2 ** retry_count)
            body["retry_count"] = retry_count + 1
            await self._publish_with_delay(body, delay_seconds)
        else:
            await self._publish_to_dead_letter(body, exc)

    async def _publish_with_delay(self, body: dict, delay_seconds: int) -> None:
        """Republish message with TTL-based delay for retry."""
        delay_queue_name = f"{self.queue_name}.delay.{delay_seconds}s"
        delay_queue = await self._channel.declare_queue(
            delay_queue_name,
            durable=True,
            arguments={
                "x-message-ttl": delay_seconds * 1000,
                "x-dead-letter-exchange": "dentalos.direct",
                "x-dead-letter-routing-key": self.queue_name,
            },
        )
        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(body).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=delay_queue_name,
        )

    async def _publish_to_dead_letter(self, body: dict, exc: Exception) -> None:
        """Send exhausted message to dead letter queue."""
        dlx_message = {
            "original_message": body,
            "failure_reason": str(exc),
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "total_attempts": body.get("retry_count", 0) + 1,
            "queue_origin": self.queue_name,
        }
        exchange = await self._channel.get_exchange("dentalos.dlx")
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(dlx_message).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key="dead_letter",
        )

    async def shutdown(self) -> None:
        if self._channel:
            await self._channel.close()
        if self._connection:
            await self._connection.close()
        logger.info("Worker shut down", extra={"queue": self.queue_name})
```

### Job Publisher (FastAPI side)

```python
"""
Publisher utility for dispatching jobs from FastAPI request handlers.
Used as a FastAPI dependency.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aio_pika
from aio_pika.pool import Pool

from app.core.config import settings


class JobPublisher:
    def __init__(self, channel_pool: Pool):
        self._channel_pool = channel_pool

    async def publish(
        self,
        queue: str,
        job_type: str,
        tenant_id: str,
        payload: Dict[str, Any],
        priority: int = 5,
        max_retries: int = 3,
        correlation_id: Optional[str] = None,
        initiated_by: Optional[str] = None,
    ) -> str:
        message_id = str(uuid.uuid4())
        body = {
            "message_id": message_id,
            "tenant_id": tenant_id,
            "job_type": job_type,
            "payload": payload,
            "priority": priority,
            "retry_count": 0,
            "max_retries": max_retries,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id,
            "initiated_by": initiated_by,
        }

        async with self._channel_pool.acquire() as channel:
            exchange = await channel.get_exchange("dentalos.direct")
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps(body).encode(),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    priority=priority,
                    message_id=message_id,
                ),
                routing_key=queue,
            )

        return message_id


# FastAPI dependency
async def get_publisher() -> JobPublisher:
    """Dependency injection for job publisher. Channel pool is app-scoped."""
    from app.core.rabbitmq import channel_pool  # initialized at app startup
    return JobPublisher(channel_pool)
```

### Usage in FastAPI Route

```python
from fastapi import APIRouter, Depends
from app.jobs.publisher import JobPublisher, get_publisher
from app.core.auth import get_current_user, CurrentUser
from app.core.tenant import get_tenant_id

router = APIRouter()


@router.post("/patients/{patient_id}/treatment-plans/{plan_id}/pdf")
async def generate_treatment_plan_pdf(
    patient_id: str,
    plan_id: str,
    user: CurrentUser = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    publisher: JobPublisher = Depends(get_publisher),
):
    """Trigger async PDF generation for a treatment plan."""
    message_id = await publisher.publish(
        queue="clinical",
        job_type="pdf.treatment_plan",
        tenant_id=tenant_id,
        payload={
            "patient_id": patient_id,
            "plan_id": plan_id,
        },
        priority=4,
        initiated_by=user.id,
    )
    return {
        "status": "processing",
        "job_id": message_id,
        "message": "PDF generation started. You will be notified when it is ready.",
    }
```

### Job Handler Registration

```python
"""
Job registry maps job_type strings to async handler functions.
Each handler receives (session, payload, envelope) arguments.
"""
from typing import Any, Callable, Coroutine, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

HandlerFunc = Callable[
    [AsyncSession, Dict[str, Any], Dict[str, Any]],
    Coroutine[Any, Any, None],
]


class JobRegistry:
    def __init__(self):
        self._handlers: Dict[str, HandlerFunc] = {}

    def register(self, job_type: str, handler: HandlerFunc) -> None:
        self._handlers[job_type] = handler

    def get_handler(self, job_type: str) -> Optional[HandlerFunc]:
        return self._handlers.get(job_type)


# Example registration in clinical worker:
# registry.register("pdf.treatment_plan", handle_treatment_plan_pdf)
# registry.register("pdf.consent_form", handle_consent_form_pdf)
# registry.register("rips.generate", handle_rips_generation)
```

---

## Tenant Schema Resolution in Workers

Workers resolve the tenant PostgreSQL schema dynamically per message. This is identical to how the API server resolves tenants, but driven by the message `tenant_id` instead of a JWT claim.

```python
"""
Tenant-aware database session for workers.
Sets PostgreSQL search_path to the tenant schema before yielding the session.
"""
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import async_engine


@asynccontextmanager
async def get_tenant_session(tenant_id: str):
    """Create a database session scoped to a specific tenant schema."""
    schema_name = f"tenant_{tenant_id}"
    async with async_sessionmaker(async_engine, class_=AsyncSession)() as session:
        await session.execute(text(f"SET search_path TO {schema_name}, public"))
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

---

## Monitoring

### Metrics to Track

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Queue depth (per queue) | RabbitMQ Management API | > 100 messages sustained for 5 min |
| Processing rate (msg/sec) | Worker structured logs | < 1 msg/sec when queue depth > 0 |
| Failure rate (per queue) | Worker structured logs | > 5% of processed messages |
| Dead letter queue depth | RabbitMQ Management API | > 0 (any dead letter is an alert) |
| Worker process count | systemd / Docker health | < expected count |
| Consumer lag | RabbitMQ consumer utilization | < 50% utilization sustained |
| Message age (oldest unprocessed) | RabbitMQ per-queue | > 5 minutes for notifications, > 30 minutes for others |

### Health Check Endpoint

Workers expose a health check via a lightweight HTTP server on a separate port (configurable, default 8081-8084).

```python
# GET /health on port 8081
{
  "status": "healthy",
  "worker": "notification-worker",
  "queue": "notifications",
  "connected": true,
  "messages_processed": 1542,
  "last_message_at": "2026-02-24T15:30:00Z",
  "uptime_seconds": 86400
}
```

### Structured Logging

All worker logs are JSON-formatted for log aggregation.

```json
{
  "timestamp": "2026-02-24T15:30:00Z",
  "level": "INFO",
  "logger": "dentalos.worker.clinical",
  "message": "Job completed",
  "message_id": "uuid",
  "tenant_id": "tn_abc123",
  "job_type": "pdf.treatment_plan",
  "duration_ms": 1250,
  "worker": "clinical-worker-1"
}
```

---

## RabbitMQ Configuration

### Exchange and Queue Setup (Terraform/Ansible or startup script)

```python
"""
RabbitMQ topology setup. Run once during infrastructure provisioning
or at application startup (idempotent).
"""
import aio_pika


async def setup_topology(connection: aio_pika.Connection) -> None:
    channel = await connection.channel()

    # Declare main direct exchange
    main_exchange = await channel.declare_exchange(
        "dentalos.direct",
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    # Declare dead letter exchange
    dlx_exchange = await channel.declare_exchange(
        "dentalos.dlx",
        aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    # Declare queues with priority support and dead lettering
    queues_config = {
        "notifications": {"x-max-priority": 10, "x-max-length": 10000},
        "clinical": {"x-max-priority": 10, "x-max-length": 5000},
        "import": {"x-max-priority": 10, "x-max-length": 100},
        "maintenance": {"x-max-priority": 10, "x-max-length": 1000},
    }

    for queue_name, args in queues_config.items():
        queue = await channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                **args,
                "x-dead-letter-exchange": "dentalos.dlx",
                "x-dead-letter-routing-key": "dead_letter",
            },
        )
        await queue.bind(main_exchange, routing_key=queue_name)

    # Dead letter queue
    dl_queue = await channel.declare_queue("dead_letter", durable=True)
    await dl_queue.bind(dlx_exchange, routing_key="dead_letter")
```

### Production Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `vm_memory_high_watermark` | 0.6 | Conservative for shared Hetzner VPS |
| `disk_free_limit` | 2GB | Prevent disk exhaustion |
| `heartbeat` | 60s | Detect dead connections |
| `channel_max` | 128 | Prevent resource exhaustion |
| `consumer_timeout` | 1800000 (30 min) | Allow long-running import jobs |
| Persistence | All queues durable, messages persistent | Healthcare data: message loss is unacceptable |
| Cluster | Single node (initial), mirrored pair (scale) | Start simple, add HA when needed |

---

## Scaling Strategy

### Phase 1: Single Server (0-50 tenants)

- RabbitMQ on same server as API
- 2 notification workers, 2 clinical workers, 1 import worker, 1 maintenance worker
- Total: 6 worker processes

### Phase 2: Dedicated Queue Server (50-500 tenants)

- RabbitMQ on dedicated Hetzner VPS (CX31: 8 vCPU, 32GB RAM)
- Scale notification workers to 4, clinical workers to 4
- Total: 10 worker processes across 2 servers

### Phase 3: HA Cluster (500+ tenants)

- RabbitMQ 3-node cluster with quorum queues
- Workers deployed as Docker containers with auto-scaling
- Separate worker pools per tenant tier (Enterprise tenants get dedicated workers)

---

## Idempotency

All job handlers MUST be idempotent. The `message_id` field in the envelope is used as an idempotency key.

**Pattern:** Before processing, check if `message_id` exists in a `processed_jobs` table. If it does, skip processing and acknowledge the message.

```python
async def ensure_idempotent(session: AsyncSession, message_id: str) -> bool:
    """Returns True if message was already processed."""
    result = await session.execute(
        text("SELECT 1 FROM public.processed_jobs WHERE message_id = :mid"),
        {"mid": message_id},
    )
    if result.scalar():
        return True  # Already processed
    await session.execute(
        text("INSERT INTO public.processed_jobs (message_id, processed_at) VALUES (:mid, NOW())"),
        {"mid": message_id},
    )
    return False
```

The `processed_jobs` table lives in the `public` schema (shared) and is periodically cleaned by the maintenance worker (entries older than 7 days).

---

## Out of Scope

This spec explicitly does NOT cover:

- Specific notification template rendering (see `notifications/` spec domain)
- PDF template design and content layout (see `treatment-plans/`, `consents/`, `billing/` specs)
- RIPS file format details (see `compliance/rips-generate.md`)
- RabbitMQ cluster setup and Hetzner provisioning (see `infra/deployment-architecture.md`)
- WebSocket push for real-time job status updates (future enhancement)
- Scheduled/cron job triggering mechanism (managed outside RabbitMQ, e.g., APScheduler or systemd timers)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec: queue topology, message format, retry policies, worker architecture, monitoring |
