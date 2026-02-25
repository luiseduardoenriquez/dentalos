# ADR-008: RabbitMQ over Celery+Redis for Async Task Processing

**Status:** Accepted
**Date:** 2026-02-24
**Authors:** DentalOS Architecture Team

---

## Context

DentalOS requires asynchronous task processing for operations that cannot or should not execute synchronously within an API request lifecycle. These tasks span multiple domains and have varying reliability, latency, and priority requirements.

### Task Inventory

| Task | Domain | Criticality | Latency Tolerance | Volume |
|------|--------|-------------|-------------------|--------|
| Email delivery (transactional) | Notifications | High | < 30 seconds | ~500/day per active tenant |
| WhatsApp appointment reminders | Notifications | High | < 5 minutes before scheduled send | ~200/day per active tenant |
| SMS notifications | Notifications | High | < 30 seconds | ~100/day per active tenant |
| RIPS file generation | Compliance (CO) | Critical | < 1 hour (batch, end of billing period) | Monthly per Colombian tenant |
| CFDI invoice submission | Compliance (MX) | Critical | < 5 minutes after invoice creation | Per invoice, real-time |
| DTE invoice submission | Compliance (CL) | Critical | < 5 minutes after invoice creation | Per invoice, real-time |
| Treatment plan PDF generation | Clinical | Medium | < 2 minutes | On demand, ~20/day per tenant |
| Consent form PDF generation | Clinical | Medium | < 2 minutes | On demand, ~10/day per tenant |
| Prescription PDF generation | Clinical | Medium | < 1 minute | On demand, ~15/day per tenant |
| Audit log writes | Compliance | Critical | < 10 seconds | Every state-changing API request |
| Patient CSV import | Data | Low | < 10 minutes | Rare, during onboarding |
| Tenant schema migration | Infra | Critical | < 5 minutes | During deployments |
| Analytics aggregation | Analytics | Low | < 1 hour | Nightly batch |

### Reliability Requirements

In a healthcare SaaS application, message loss has direct consequences:

- **Lost audit log write** = Non-compliance with healthcare record-keeping regulations (Colombia Resolucion 1995, Mexico NOM-024).
- **Lost RIPS generation job** = Missed regulatory reporting deadline, potential fines.
- **Lost invoice submission** = Tax compliance violation.
- **Lost appointment reminder** = Patient no-show, lost revenue for the clinic.

The message broker must guarantee **at-least-once delivery** for all tasks. Lost messages are not an acceptable trade-off for simplicity or performance.

### Evaluation Criteria

1. **Message durability:** Are messages persisted to disk before acknowledgment?
2. **Priority queues:** Can urgent tasks (notifications) preempt batch tasks (analytics)?
3. **Dead letter handling:** Where do failed messages go after retry exhaustion?
4. **Routing flexibility:** Can messages be routed by domain, priority, or tenant?
5. **Operational visibility:** Can we inspect queue depths, message contents, and consumer health?
6. **Python async compatibility:** Does it work with `asyncio` and our FastAPI async architecture?
7. **Self-hosted viability:** Can it run on Hetzner VPS without managed service dependency?

---

## Decision

We will use **RabbitMQ** as the message broker with **aio-pika** as the async Python client library. Redis remains in the stack exclusively for caching (see `infra/caching-strategy.md`) and rate limiting (see `infra/rate-limiting.md`). Redis will not be used as a message broker.

### Queue Topology

```
dentalos.direct (Direct Exchange, durable)
  |
  +-- routing_key: "notifications" --> [notifications] queue (priority: 0-10)
  |                                      Workers: 2
  |
  +-- routing_key: "clinical"      --> [clinical] queue (priority: 0-10)
  |                                      Workers: 2
  |
  +-- routing_key: "import"        --> [import] queue (priority: 0-10)
  |                                      Workers: 1
  |
  +-- routing_key: "maintenance"   --> [maintenance] queue (priority: 0-10)
                                         Workers: 1

dentalos.dlx (Direct Exchange, durable)
  |
  +-- routing_key: "dead_letter"   --> [dead_letter] queue (durable, no TTL)
```

**Queue configuration details:**

| Queue | Max Priority | Max Length | DLX | Consumer Prefetch |
|-------|-------------|------------|-----|-------------------|
| `notifications` | 10 | 10,000 | `dentalos.dlx` | 10 |
| `clinical` | 10 | 5,000 | `dentalos.dlx` | 10 |
| `import` | 10 | 100 | `dentalos.dlx` | 1 |
| `maintenance` | 10 | 1,000 | `dentalos.dlx` | 5 |
| `dead_letter` | N/A | Unlimited | None | N/A (manual processing) |

### Message Priority Levels

| Priority | Range | Examples |
|----------|-------|---------|
| Critical | 8-10 | Tenant schema migrations, emergency system maintenance |
| High | 5-7 | Transactional emails, WhatsApp/SMS sends, audit log writes, RIPS/CFDI generation |
| Medium | 3-4 | PDF generation (treatment plans, consent forms), bulk email campaigns |
| Low | 1-2 | Analytics aggregation, data archival, audit log archiving, tenant cleanup |

### Dead Letter Queue (DLQ) Configuration

Messages are routed to the DLQ after exhausting all retry attempts. The DLQ provides:

1. **Durability:** Dead-lettered messages are persisted indefinitely until manually processed.
2. **Enrichment:** Each dead-lettered message includes the original payload, failure reason, total attempt count, origin queue, and failure timestamp.
3. **Alerting:** Any message arriving in the DLQ triggers a monitoring alert (Slack/PagerDuty). Critical job types (`audit.write`, `tenant.schema_migrate`, `rips.generate`) trigger immediate escalation.
4. **Manual replay:** The superadmin dashboard provides a UI to inspect dead-lettered messages and replay them to their origin queue.

### Acknowledgment-Based Delivery

RabbitMQ uses explicit consumer acknowledgments. A message is removed from the queue only after the consumer sends an `ack`. If the consumer crashes or the connection drops before `ack`, the message is automatically requeued and delivered to another consumer. This guarantees at-least-once delivery.

```python
async def _process_message(self, message: IncomingMessage) -> None:
    async with message.process(requeue=False):
        # Message is auto-acked when this context manager exits successfully.
        # If an exception propagates, the message is nacked (not requeued)
        # and retry/DLQ logic handles it.
        body = json.loads(message.body.decode())
        handler = self.registry.get_handler(body["job_type"])
        async with get_tenant_session(body["tenant_id"]) as session:
            await handler(session, body["payload"], body)
```

### aio-pika Consumer Code Pattern

```python
"""
Example consumer using aio-pika with DentalOS conventions.
Each worker is a standalone process consuming from one queue.
"""
import asyncio
import aio_pika

from app.core.config import settings
from app.workers.base import BaseWorker
from app.jobs.registry import JobRegistry


async def main():
    worker = BaseWorker(
        queue_name="notifications",
        prefetch_count=10,
    )
    # Register handlers for this queue's job types
    worker.registry.register("email.send", handle_email_send)
    worker.registry.register("whatsapp.send", handle_whatsapp_send)
    worker.registry.register("sms.send", handle_sms_send)
    worker.registry.register("email.bulk", handle_bulk_email)
    worker.registry.register(
        "whatsapp.appointment_reminder",
        handle_appointment_reminder,
    )

    await worker.start()

    # Run until interrupted
    try:
        await asyncio.Future()  # Block forever
    finally:
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
```

### Retry Policies (Exponential Backoff)

Failed messages are retried with exponential backoff using TTL-based delay queues. Each retry creates a temporary delay queue with a message TTL; when the TTL expires, the message is dead-lettered back to the original queue for reprocessing.

```
Attempt 1: Immediate processing
Attempt 2: 30-second delay (via dentalos.notifications.delay.30s queue)
Attempt 3: 120-second delay (2 minutes)
Attempt 4: 480-second delay (8 minutes)
Attempt 5: Dead letter queue (no further automatic retries)
```

Formula: `delay = base_delay * (2 ^ retry_count)` where `base_delay` varies per job type.

**Per-queue retry overrides:**

| Job Type | Max Retries | Backoff Base | Rationale |
|----------|-------------|--------------|-----------|
| `email.send` | 5 | 60s | SMTP servers may be temporarily unavailable |
| `whatsapp.send` | 3 | 30s | Meta API has its own retry semantics |
| `rips.generate` | 2 | 60s | Deterministic: if source data is invalid, retrying will not help |
| `pdf.*` | 3 | 30s | Resource contention (CPU/memory) is the usual failure cause |
| `audit.write` | 5 | 15s | Audit logs must not be lost; retry aggressively |
| `tenant.schema_migrate` | 1 | 0s | Migrations are idempotent but require manual review on failure |

### Idempotency with processed_jobs Table

All job handlers are idempotent. The `message_id` field in the message envelope serves as the idempotency key. Before processing, the handler checks a `public.processed_jobs` table:

```sql
CREATE TABLE public.processed_jobs (
    message_id  UUID PRIMARY KEY,
    job_type    VARCHAR(100) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tenant_id   VARCHAR(30) NOT NULL
);

-- Auto-cleanup: entries older than 7 days are purged by maintenance worker
CREATE INDEX idx_processed_jobs_processed_at ON public.processed_jobs (processed_at);
```

This prevents duplicate processing when a message is redelivered (e.g., consumer crash after processing but before ack, or manual DLQ replay).

### RabbitMQ Management UI

RabbitMQ ships with a management plugin that provides a web-based UI for monitoring:

- **Queue metrics:** Message count, publish rate, delivery rate, acknowledgment rate per queue.
- **Connection/channel health:** Active consumers, channel count, heartbeat status.
- **Message inspection:** Peek at messages in any queue without consuming them.
- **Shovel/Federation:** Move messages between queues (useful for DLQ replay).

The management UI is exposed on port 15672 and protected by HTTP basic auth. In production, it is accessible only via VPN or SSH tunnel.

---

## Alternatives Considered

### Alternative 1: Celery + Redis

Use Celery (the de facto Python task queue) with Redis as both the message broker and result backend.

**Why rejected:**

| Criterion | Celery + Redis | RabbitMQ + aio-pika |
|-----------|---------------|---------------------|
| **Message durability** | Redis persistence (RDB/AOF) is eventual. Messages in memory can be lost during Redis crash before the next RDB snapshot or AOF fsync. Celery's `acks_late` mitigates but does not eliminate this risk. | RabbitMQ persists durable messages to disk before acknowledging the publisher. Messages survive broker restarts. |
| **Priority queues** | Celery supports priorities via separate queues (one queue per priority level) or Redis sorted sets, but the implementation is fragile and not well-documented. | RabbitMQ has native priority queue support (x-max-priority argument). Messages are dequeued in priority order within a single queue. |
| **Dead letter handling** | Celery has no built-in DLQ concept. Failed tasks go to a configurable error handler, but there is no durable "dead letter queue" for inspection and replay. Requires custom implementation. | RabbitMQ has native Dead Letter Exchanges (DLX). Failed messages are automatically routed to a DLQ with full metadata (reason, retry count, original queue). |
| **Routing flexibility** | Celery routes tasks by queue name. Dynamic routing (e.g., by tenant, by country) requires custom routers. | RabbitMQ exchanges support direct, topic, fanout, and headers routing. Messages can be routed by any combination of routing key, headers, and exchange bindings. |
| **Operational visibility** | Celery Flower provides a web dashboard, but it monitors workers, not the broker. Redis has no built-in queue monitoring UI. | RabbitMQ Management UI provides full visibility into queues, messages, connections, channels, and consumer health. |
| **Python async** | Celery's async support is incomplete. `celery.contrib.asyncio` exists but is not production-ready. Running Celery workers in an asyncio event loop requires workarounds. | aio-pika is a native asyncio AMQP client. Full async/await support, compatible with FastAPI's async architecture. |
| **Abstraction level** | Celery provides a high-level `@task` decorator API that hides broker details. Convenient for simple use cases. | aio-pika is a lower-level AMQP client. We manage queue topology, message serialization, and consumer logic ourselves. More code, but more control. |
| **Resource separation** | Using Redis as both cache AND broker means cache eviction pressure can affect message storage. A spike in cached data could trigger Redis memory eviction policies, potentially evicting queued messages. | RabbitMQ is a dedicated broker with its own memory management. Redis serves only caching and rate limiting, with no risk of cross-concern interference. |

**Summary:** Celery + Redis is the simpler, more conventional choice for Python projects. However, for a healthcare application where message loss has regulatory consequences, RabbitMQ's durability guarantees, native priority queues, DLX support, and management UI provide essential capabilities that Redis-as-broker does not reliably offer.

### Alternative 2: AWS SQS

Use Amazon SQS (Simple Queue Service) as a managed message broker.

**Why rejected:**

- DentalOS is hosted on Hetzner Cloud (ADR-004). Using AWS SQS introduces a cross-cloud dependency, adding network latency (Hetzner to AWS round-trip) and a hard dependency on AWS infrastructure.
- SQS pricing is per-request. At DentalOS's projected message volume (10,000-100,000 messages/day across all tenants), costs are manageable but represent an ongoing variable expense versus RabbitMQ's fixed cost on Hetzner.
- SQS does not support message priority queues. Priority must be simulated with multiple queues and consumer-side polling logic.
- SQS FIFO queues have a 300 messages/second throughput limit. Standard queues do not guarantee ordering.
- Vendor lock-in to AWS for a critical infrastructure component contradicts DentalOS's cloud-portable architecture principle.

**Trade-offs:** Fully managed (no operational burden). Highly available. But the cross-cloud latency, lack of priority queues, and vendor lock-in make it a poor fit for Hetzner-hosted DentalOS.

### Alternative 3: Custom PostgreSQL-based Queue

Use PostgreSQL's `SKIP LOCKED` feature to implement a custom job queue table. Workers poll the table for pending jobs.

```sql
-- Simplified PostgreSQL queue pattern
SELECT * FROM public.job_queue
WHERE status = 'pending' AND scheduled_at <= NOW()
ORDER BY priority DESC, created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;
```

**Why rejected:**

- Polling-based consumption wastes database connections and CPU. Each worker polls every N seconds regardless of queue depth, consuming connection pool slots that are needed for API requests.
- PostgreSQL is not designed as a message broker. Under high message throughput, the job queue table accumulates dead tuples rapidly, requiring aggressive VACUUM settings. This interferes with clinical query performance.
- No built-in features for dead letter handling, priority dequeuing, TTL-based message expiry, or consumer heartbeats. All of these would need to be implemented in application code.
- DentalOS already uses pgbouncer for connection pooling (ADR-001). Adding long-polling worker connections to the pool increases pressure on a resource that is sized for API request traffic.

**Trade-offs:** Zero additional infrastructure (PostgreSQL is already deployed). Simple to implement for low-volume use cases. But the operational overhead (polling waste, VACUUM pressure, no DLQ, no management UI) makes it unsuitable for DentalOS's volume and reliability requirements.

---

## Consequences

### Positive

- **Message durability guarantees.** RabbitMQ persists durable messages to disk before acknowledging the publisher. Combined with consumer acknowledgments, this provides at-least-once delivery with no message loss during broker or consumer restarts.
- **Native priority queues.** Urgent notifications (e.g., a patient's appointment in 1 hour) are dequeued before batch analytics aggregation, all from the same queue. No need to maintain separate queues per priority level.
- **Dead Letter Exchanges.** Failed messages are automatically routed to a DLQ with full context (failure reason, retry count, origin queue). This is critical for healthcare compliance: lost audit logs or RIPS generation failures must be visible and recoverable.
- **Exchange-based routing.** The direct exchange routes messages by domain (notifications, clinical, import, maintenance). Future expansion can add topic exchanges for tenant-specific or country-specific routing without changing publishers.
- **Operational visibility.** The RabbitMQ Management UI provides real-time visibility into queue depths, consumer health, and message flow. This is essential for diagnosing production issues (e.g., "Why are notifications delayed?" -- check queue depth and consumer count).
- **Clean resource separation.** Redis handles caching and rate limiting. RabbitMQ handles messaging. Neither system is overloaded with dual responsibilities. Redis eviction policies cannot affect message delivery.
- **Async-native.** aio-pika integrates naturally with FastAPI's asyncio event loop. Publishers and consumers use `async/await` without thread pool hacks.

### Negative

- **Operational overhead.** RabbitMQ is a separate service to deploy, configure, monitor, and upgrade on Hetzner. Unlike Redis (which DentalOS needs anyway for caching), RabbitMQ is an additional infrastructure component. Mitigated by Docker Compose for development and systemd for production.
- **No high-level task API.** Unlike Celery's `@task` decorator, aio-pika requires explicit message publishing, queue declaration, and consumer registration. More boilerplate code. Mitigated by DentalOS's `BaseWorker` class and `JobPublisher` utility (see `infra/background-processing.md`).
- **Learning curve.** AMQP concepts (exchanges, bindings, routing keys, acknowledgments, prefetch) are more complex than Celery's task/queue abstraction. New team members need to understand RabbitMQ's messaging model.
- **Single point of failure (initial deployment).** In the MVP phase, RabbitMQ runs as a single node. If it crashes, async processing stops until it restarts. Mitigated by RabbitMQ's durable queues (messages survive restart) and the plan to add HA clustering at Phase 3 (500+ tenants).

### Neutral

- **Resource requirements.** RabbitMQ requires approximately 256-512 MB RAM for DentalOS's workload. On the Hetzner CX31 VPS (32 GB RAM shared with API servers), this is a modest allocation.
- **Erlang dependency.** RabbitMQ runs on the Erlang VM. This is an opaque dependency -- the team does not need Erlang expertise for normal operations, but debugging RabbitMQ internals requires Erlang familiarity. Mitigated by RabbitMQ's mature documentation and community.
- **Redis remains in the stack.** Choosing RabbitMQ does not remove Redis. Redis continues to serve caching (db 0), sessions (db 1), rate limiting (db 2), as defined in `infra/caching-strategy.md`. The two systems have distinct, non-overlapping responsibilities.
- **Future migration path.** If DentalOS outgrows a single RabbitMQ node, the migration path is well-defined: RabbitMQ clustering with quorum queues. If the team later decides Celery's convenience outweighs the trade-offs, Celery can use RabbitMQ as its broker (Celery supports AMQP natively) -- the queue topology would remain unchanged.

---

## References

- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)
- [aio-pika (PyPI)](https://pypi.org/project/aio-pika/) -- Async Python AMQP client
- [RabbitMQ Priority Queue Support](https://www.rabbitmq.com/priority.html)
- [RabbitMQ Dead Letter Exchanges](https://www.rabbitmq.com/dlx.html)
- [RabbitMQ Management Plugin](https://www.rabbitmq.com/management.html)
- [Celery Documentation](https://docs.celeryq.dev/) -- The alternative we considered
- DentalOS `infra/background-processing.md` -- Full queue topology, worker implementation, and monitoring spec
- DentalOS `infra/caching-strategy.md` -- Redis usage (caching and rate limiting only)
- DentalOS `infra/adr/004-hetzner-over-aws.md` -- Why AWS SQS is not viable (Hetzner hosting)
- DentalOS `ADR-LOG.md` -- ADR-008 summary
