# N-05 — Notification Dispatch Engine (Internal Service Spec)

---

## Overview

**Feature:** Internal notification dispatch engine. Accepts event type, recipient, and event data from any domain service via RabbitMQ. Routes the notification to the appropriate delivery channels (in-app, email, WhatsApp, SMS) based on the recipient's preferences. Handles template rendering, multi-channel fanout, async delivery, retry with exponential backoff, and dead-letter queue (DLQ) management for permanent failures. This is NOT an HTTP endpoint — it is an internal async service consumed via RabbitMQ.

**Domain:** notifications

**Priority:** Medium

**Dependencies:** N-01, N-02, N-03, N-04 (preferences matrix), infra/background-processing.md, infra/audit-logging.md, infra/caching-strategy.md

---

## Authentication

- **Level:** Internal service — no HTTP authentication. Messages arrive via RabbitMQ from trusted internal producers. The exchange is not publicly accessible.
- **Roles allowed:** Not applicable (internal service). The `recipient` in the message payload carries the `user_id` and `tenant_id` used to resolve preferences and routing.
- **Tenant context:** Carried in the message payload as `tenant_id`. The engine sets the PostgreSQL `search_path` to the tenant schema before inserting in-app notifications.
- **Special rules:** Message integrity is enforced by RabbitMQ exchange-level access control. No anonymous producers allowed. All producers must authenticate with RabbitMQ credentials.

---

## Service Interfaces

### Input Interface — RabbitMQ Message

**Exchange:** `notifications.fanout` (type: `topic`)

**Routing keys:**
- `notification.appointment.*` — appointment-related events
- `notification.billing.*` — billing and payment events
- `notification.clinical.*` — clinical record events
- `notification.inventory.*` — inventory alert events
- `notification.system.*` — system and platform events
- `notification.patient.*` — patient-related events

**Queue:** `notification.dispatch` (durable, persistent)

**Message format (JSON, UTF-8):**
```json
{
  "event_type": "string (required) — notification event type enum",
  "tenant_id": "string (required) — UUID of the tenant",
  "recipient": {
    "user_id": "string (required) — UUID of the receiving user",
    "role": "string (required) — user role for preference lookup",
    "email": "string | null — email address if known",
    "phone": "string | null — E.164 format phone number",
    "locale": "string — ISO 639-1, default 'es'"
  },
  "data": {
    "key": "value — arbitrary domain-specific template variables"
  },
  "idempotency_key": "string (required) — UUID for deduplication",
  "priority": "integer (optional) — 0-9, default 5",
  "scheduled_at": "string | null (optional) — ISO 8601 datetime for delayed delivery"
}
```

**Valid event types:**
- `appointment_reminder`
- `appointment_confirmed`
- `appointment_cancelled`
- `new_patient`
- `payment_received`
- `payment_overdue`
- `treatment_plan_approved`
- `consent_signed`
- `message_received`
- `inventory_alert`
- `system_update`

### Output Interfaces

The engine writes to multiple external systems per channel:

| Channel | Technology | Library/API | Output |
|---------|-----------|-------------|--------|
| in_app | PostgreSQL INSERT into tenant schema `notifications` table | SQLAlchemy async | Row in `notifications` |
| email | SendGrid / AWS SES (configurable per tenant) | `sendgrid` / `boto3` Python SDK | Email delivered to recipient's inbox |
| whatsapp | WhatsApp Business Cloud API (Meta) | HTTP REST via `httpx` | WhatsApp message delivered |
| sms | Twilio SMS API | `twilio` Python SDK | SMS delivered to phone |

---

## Queue Topology

### Exchanges

```
notifications.exchange (topic)
    ├── notification.dispatch (queue, durable)    ← main processing queue
    ├── notification.retry.1 (queue, TTL: 30s)   ← first retry delay
    ├── notification.retry.2 (queue, TTL: 300s)  ← second retry delay (5 min)
    ├── notification.retry.3 (queue, TTL: 1800s) ← third retry delay (30 min)
    └── notification.dlq (queue, durable)        ← dead-letter queue, permanent failures
```

### Dead Letter Configuration

Each retry queue is configured with:
- `x-dead-letter-exchange`: `notifications.exchange`
- `x-dead-letter-routing-key`: `notification.dispatch` (re-routes expired messages back to main queue with incremented retry count)
- `x-message-ttl`: Per retry level (30s / 300s / 1800s)

The DLQ (`notification.dlq`) is monitored by a separate alert consumer that notifies ops via Sentry and logs structured events for manual review.

---

## Processing Flow

### Main Dispatch Worker

**Concurrency:** 5 concurrent consumers per deployed worker instance. Horizontally scalable.

**Step-by-step processing:**

1. **Receive message** from `notification.dispatch` queue via `aio-pika` async consumer.
2. **Deserialize and validate** the message JSON against `NotificationMessage` Pydantic schema. If deserialization fails, ACK the message (malformed messages cannot be retried usefully) and emit Sentry alert.
3. **Idempotency check** — look up `idempotency_key` in Redis key `notification:idempotency:{idempotency_key}`. If found (TTL: 24h), ACK message and skip processing (already delivered). This prevents duplicate sends on RabbitMQ redelivery.
4. **Delayed delivery check** — if `scheduled_at` is in the future, re-publish message to `notification.retry.1` queue with remaining delay TTL. ACK original. (Note: for very long delays, a scheduled jobs approach via APScheduler is preferred over RabbitMQ TTL loops.)
5. **Resolve recipient preferences** — fetch from Redis cache `tenant:{tenant_id}:user:{user_id}:notification_preferences` (or DB if cache miss). Determine which channels are enabled for the given `event_type`.
6. **Check tenant channel capabilities** — load tenant settings to verify which external channels are provisioned (e.g., tenant may not have WhatsApp Business API configured). Suppress unconfigured channels silently with a log warning.
7. **Render templates** — for each enabled channel, render the notification template with the provided `data` variables (see Template Engine section below).
8. **Fanout to channels** — dispatch to each enabled channel concurrently using `asyncio.gather` with exception isolation. Channel failures are independent — a WhatsApp failure does not block email delivery.
9. **Insert in-app notification** — always executed (in_app is always enabled). Set tenant schema path, INSERT into `notifications` table with pre-rendered title+body, trigger cache invalidation for `unread_count`.
10. **Record idempotency key** in Redis: `SET notification:idempotency:{idempotency_key} 1 EX 86400`.
11. **ACK message** from RabbitMQ queue.
12. **Emit delivery log** — structured log entry per channel with delivery status.

### Per-Channel Delivery

**Email (SendGrid/SES):**
- Render HTML + plain-text email from Jinja2 templates.
- Send via SDK. On `4xx` (except 429), log and mark as permanent failure for this channel.
- On `5xx` or `429`, propagate as retryable error.
- Respect SendGrid's `asm_group_id` for unsubscribe compliance.

**WhatsApp (Meta Business Cloud API):**
- Use pre-approved message templates registered with Meta (HSM templates).
- Map `event_type` to WhatsApp template name and language code.
- Send via HTTP POST to `https://graph.facebook.com/v19.0/{phone_number_id}/messages`.
- On `400` (template rejected), log permanent failure. On `5xx`, retry.
- Include `recipient_type: individual` and `to: {E.164 phone}`.

**SMS (Twilio):**
- Render plain-text SMS body. Max 160 characters for single SMS; concatenation handled by Twilio for longer messages.
- Send via Twilio Python SDK `client.messages.create(...)`.
- On `21211` (invalid phone), mark permanent failure. On network errors, retry.

**In-App (PostgreSQL):**
- INSERT into tenant schema `notifications` table:
  ```sql
  INSERT INTO notifications (id, user_id, type, title, body, metadata, created_at)
  VALUES (gen_random_uuid(), :user_id, :type, :title, :body, :metadata::jsonb, NOW())
  ```
- DELETE Redis key `tenant:{tenant_id}:user:{user_id}:notifications:unread_count`.
- SCAN + DEL pattern `tenant:{tenant_id}:user:{user_id}:notifications:list:*`.

---

## Template Engine

**Technology:** Jinja2 with strict undefined (raises `UndefinedError` on missing variables).

**Template storage:** Templates stored in the application file system at `app/notification_templates/{channel}/{event_type}.{ext}`.

**Template naming convention:**
- `app/notification_templates/email/{event_type}.html`
- `app/notification_templates/email/{event_type}.txt`
- `app/notification_templates/whatsapp/{event_type}.json` (template params for Meta API)
- `app/notification_templates/sms/{event_type}.txt`
- `app/notification_templates/in_app/{event_type}.json` (title + body strings)

**Template variables** (always available in context):
```
{{ clinic_name }}      — from tenant settings
{{ recipient_name }}   — from data.recipient_name
{{ date }}             — formatted in tenant timezone
{{ time }}             — formatted in tenant timezone
{{ locale }}           — ISO 639-1
```

**Event-specific variables (examples):**

| Event Type | Additional Variables |
|------------|---------------------|
| appointment_reminder | `{{ doctor_name }}`, `{{ appointment_time }}`, `{{ appointment_date }}`, `{{ service_name }}` |
| payment_received | `{{ amount }}`, `{{ currency }}`, `{{ patient_name }}`, `{{ invoice_number }}` |
| payment_overdue | `{{ amount_due }}`, `{{ days_overdue }}`, `{{ patient_name }}` |
| inventory_alert | `{{ item_name }}`, `{{ item_category }}`, `{{ expiry_date }}`, `{{ alert_type }}` |
| new_patient | `{{ patient_name }}`, `{{ registration_date }}` |
| treatment_plan_approved | `{{ patient_name }}`, `{{ plan_name }}`, `{{ doctor_name }}` |

**Template rendering errors:** If a required template variable is missing from the `data` payload, the engine logs an error, marks the channel as failed, does NOT retry (permanent failure — the producer sent bad data), and sends an alert to Sentry with the full context.

---

## Retry Strategy

### Retry Policy

| Attempt | Delay | Queue |
|---------|-------|-------|
| 1st retry | 30 seconds | `notification.retry.1` |
| 2nd retry | 5 minutes | `notification.retry.2` |
| 3rd retry | 30 minutes | `notification.retry.3` |
| After 3rd retry | DLQ | `notification.dlq` |

### Retry Tracking

- Retry count stored in the RabbitMQ message header `x-retry-count` (incremented per re-queue).
- Per-channel retry state stored in Redis: `notification:retry:{idempotency_key}:{channel}` = `{attempt}`.
- A message is retried at the **message level** (all channels together) only if the in-app channel fails. Per-channel failures for external channels (email/WhatsApp/SMS) are retried independently via separate per-channel retry queues: `notification.retry.email`, `notification.retry.whatsapp`, `notification.retry.sms`.
- In-app delivery is the highest priority. If in-app INSERT fails, the entire message is retried.

### Permanent Failure Conditions (no retry)

- Invalid phone number (Twilio error 21211)
- Meta WhatsApp template rejected (`400` response)
- SendGrid invalid recipient (400 with code `550`)
- Template rendering error (missing variable — producer bug)
- Malformed message (JSON parse failure)
- Recipient user no longer exists in tenant schema

### DLQ Processing

- Messages in `notification.dlq` are monitored via a separate consumer that:
  1. Logs each message to the structured application log with `level: ERROR`.
  2. Emits a Sentry event with the full message payload (PHI redacted from title/body in Sentry).
  3. Persists the message to the `notification_dlq` table in the public schema for operational review.
  4. Does NOT automatically retry — requires manual intervention via admin tooling.

---

## Database Schema

### `notifications` table (tenant schema)

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    read_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}',
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_created ON notifications (user_id, created_at DESC, id DESC);
CREATE INDEX idx_notifications_user_read ON notifications (user_id, read_at);
CREATE INDEX idx_notifications_user_type ON notifications (user_id, type);
```

### `notification_delivery_log` table (tenant schema)

Tracks per-channel delivery status for observability and audit.

```sql
CREATE TABLE notification_delivery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key UUID NOT NULL,
    notification_id UUID REFERENCES notifications(id),
    event_type VARCHAR(64) NOT NULL,
    user_id UUID NOT NULL,
    channel VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL,  -- 'delivered', 'failed', 'skipped', 'pending'
    error_code VARCHAR(64),
    error_message TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 1,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `notification_dlq` table (public schema)

```sql
CREATE TABLE public.notification_dlq (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    idempotency_key UUID NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    raw_payload JSONB NOT NULL,
    failure_reason TEXT,
    retry_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by UUID
);
```

---

## Configuration

**Environment variables required:**

| Variable | Description | Example |
|----------|-------------|---------|
| `RABBITMQ_URL` | AMQP connection string | `amqp://user:pass@rabbitmq:5672/` |
| `SENDGRID_API_KEY` | SendGrid API key | `SG.xxxxxxxxxx` |
| `AWS_SES_REGION` | AWS region for SES fallback | `us-east-1` |
| `WHATSAPP_PHONE_NUMBER_ID` | Meta Business phone ID | `123456789` |
| `WHATSAPP_ACCESS_TOKEN` | Meta Graph API token | `EAAxxxxxxx` |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | `ACxxxxxxxx` |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | (secret) |
| `TWILIO_FROM_NUMBER` | Twilio source phone number | `+15550001234` |
| `NOTIFICATION_WORKER_CONCURRENCY` | Consumer concurrency | `5` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |

**Tenant-level settings** (stored in `public.tenants.settings` JSONB):
- `notification_channels.email_provider`: `sendgrid` or `ses`
- `notification_channels.whatsapp_enabled`: boolean
- `notification_channels.sms_enabled`: boolean
- `notification_channels.whatsapp_phone_number_id`: override per-tenant phone number

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `notifications`: INSERT on in-app delivery
- `notification_delivery_log`: INSERT per channel per attempt

**Public schema tables affected:**
- `notification_dlq`: INSERT on permanent failure after exhausting retries

### Cache Operations

**Cache keys affected:**
- `notification:idempotency:{idempotency_key}`: SET with 24h TTL (deduplication)
- `tenant:{tenant_id}:user:{user_id}:notifications:unread_count`: DELETE on in-app INSERT
- `tenant:{tenant_id}:user:{user_id}:notifications:list:*`: SCAN+DEL on in-app INSERT
- `tenant:{tenant_id}:user:{user_id}:notification_preferences`: READ (preferences lookup)

### Queue Jobs (RabbitMQ)

**Queues consumed:**
- `notification.dispatch` — main incoming queue

**Queues published to:**
- `notification.retry.1`, `.retry.2`, `.retry.3` — retry delays
- `notification.dlq` — permanent failures
- Per-channel retry queues: `notification.retry.email`, `notification.retry.whatsapp`, `notification.retry.sms`

### Audit Log

**Audit entry:** No — notification delivery is not a PHI-accessing action. Delivery log is maintained in `notification_delivery_log` for operational purposes.

### Notifications

**Notifications triggered:** This IS the notification engine — it does not trigger itself recursively.

---

## Performance

### Throughput Targets
- **Target:** Process 500 messages/minute per worker instance (average)
- **In-app INSERT latency:** < 20ms per notification
- **Email delivery:** < 2s round trip to SendGrid/SES API
- **WhatsApp delivery:** < 3s round trip to Meta API
- **SMS delivery:** < 2s round trip to Twilio API

### Caching Strategy
- **Preferences cache:** Redis `tenant:{tenant_id}:user:{user_id}:notification_preferences` — 300s TTL. Cache miss triggers DB read; no blocking.
- **Idempotency cache:** Redis `notification:idempotency:{key}` — 24h TTL. Critical for at-least-once delivery guarantee.
- **Tenant settings cache:** Redis `tenant:{tenant_id}:settings` — 600s TTL. Avoid loading tenant config per message.

### Scalability

- Workers are horizontally scalable. Add instances to increase throughput.
- RabbitMQ provides backpressure via queue depth. If queue depth exceeds 10,000 messages, alert ops.
- External API rate limits handled per-channel:
  - SendGrid: 600 emails/second on standard plan — pooled connection with rate limiter.
  - Twilio SMS: depends on plan (typically 1 SMS/sec per number) — queue separate per-number.
  - Meta WhatsApp: 250 conversations/24h per phone number on basic tier — rate limiter required.

---

## Security

### Message Security
- RabbitMQ exchange accessible only to internal services via private network (Hetzner private VLAN).
- RabbitMQ credentials rotated quarterly and stored in environment secrets, not code.
- Messages do not contain PHI beyond pre-rendered notification body strings. Raw patient data is not included in queue messages.

### PHI Handling in Templates
- Rendered notification bodies may contain patient names and appointment times — considered indirect PHI.
- Delivery logs store only `event_type`, `status`, and `channel` — NOT the rendered body.
- Sentry error reports redact the `body` field from notification payloads before transmission.

### External API Security
- All external API calls use HTTPS with TLS 1.2 minimum.
- API keys stored as environment secrets, never logged.
- WhatsApp and SMS use verified business phone numbers.

---

## Testing

### Test Cases

#### Happy Path
1. Full fanout — all channels enabled
   - **Given:** User has email + whatsapp + in_app enabled for `appointment_reminder`; tenant has all channels configured
   - **When:** Message published to `notification.dispatch` with event_type `appointment_reminder`
   - **Then:** In-app notification inserted in DB; email sent to SendGrid; WhatsApp message delivered; delivery log records 3 entries with status `delivered`; idempotency key set in Redis

2. Partial fanout — some channels disabled
   - **Given:** User has only in_app enabled for `inventory_alert`
   - **When:** `inventory_alert` message published
   - **Then:** Only in-app notification inserted; email/sms/whatsapp delivery log entries have status `skipped`

3. Idempotency — duplicate message
   - **Given:** Message with idempotency_key already processed and key in Redis
   - **When:** Same message re-published (RabbitMQ redelivery simulation)
   - **Then:** Message ACKed, no DB inserts, no external API calls, idempotency log entry

#### Edge Cases
1. External channel failure with retry
   - **Given:** SendGrid returns 500 on first attempt
   - **When:** Email delivery attempted
   - **Then:** Message re-queued to `notification.retry.1`; retried after 30s; succeeds on 2nd attempt; delivery log records `attempt_count: 2`

2. All retries exhausted — DLQ
   - **Given:** WhatsApp API returns 500 on all 3 retry attempts
   - **When:** Third retry fails
   - **Then:** Message moved to `notification.dlq`; entry in `notification_dlq` table; Sentry alert emitted; in-app delivery (if not failed) is not affected

3. Scheduled notification
   - **Given:** Message with `scheduled_at` 1 hour in the future
   - **When:** Message received
   - **Then:** Message re-published to delay queue or APScheduler job created; not delivered immediately

4. Missing template variable
   - **Given:** Producer sends `appointment_reminder` without required `doctor_name` in data
   - **When:** Template rendering attempted
   - **Then:** Channel marked as permanent failure; Sentry alert with full context; no retry; in-app notification uses fallback template

#### Error Cases
1. Malformed JSON message
   - **Given:** Non-JSON message body in queue
   - **When:** Consumer receives message
   - **Then:** Message ACKed (not retried), Sentry error emitted, structured log entry

2. Recipient user deleted from tenant
   - **Given:** `user_id` in message no longer exists in tenant schema
   - **When:** Preferences lookup attempted
   - **Then:** Permanent failure, message to DLQ, no delivery attempted

### Test Data Requirements

- Tenant schema with `notifications`, `notification_preferences`, `notification_delivery_log` tables
- User with all channels enabled, user with only in_app enabled
- RabbitMQ broker in Docker Compose for integration tests
- Mock SendGrid, Twilio, Meta WhatsApp APIs using `respx` (httpx mock) and SDK test modes

### Mocking Strategy

- SendGrid: Mock via `unittest.mock.patch` on SDK client; integration tests use SendGrid sandbox mode.
- Twilio: Mock via Twilio test credentials (returns predictable responses without real delivery).
- WhatsApp: Mock via `respx` intercepting `https://graph.facebook.com/*` calls.
- RabbitMQ: Real broker in Docker Compose for integration tests; `aio-pika` in-memory broker mock for unit tests.
- Redis: fakeredis for unit tests; real Redis for integration tests.

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Messages consumed from `notification.dispatch` queue and processed correctly
- [ ] In-app notification inserted in tenant schema on every message (always enabled)
- [ ] External channels (email/WhatsApp/SMS) routed per user preferences from N-04
- [ ] Idempotency: duplicate messages with same `idempotency_key` are no-ops
- [ ] Retry with exponential backoff: 3 attempts before DLQ
- [ ] DLQ messages logged to `notification_dlq` table and Sentry alerted
- [ ] Template rendering with Jinja2 for all 11 event types across all channels
- [ ] Per-channel delivery status recorded in `notification_delivery_log`
- [ ] Redis cache invalidated for unread count after in-app insert
- [ ] Throughput: 500 messages/minute per worker instance
- [ ] PHI redacted from Sentry error reports
- [ ] All test cases pass
- [ ] Performance targets met
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- HTTP API for triggering notifications (all callers must use RabbitMQ)
- Real-time WebSocket delivery of in-app notifications (separate spec — polling via N-01 for v1)
- Email template design (HTML/CSS) — handled by design system team
- WhatsApp Business API provisioning and Meta template submission
- Twilio phone number management
- Multi-language support beyond `es` and `en` (v1 is Spanish-first)
- Notification analytics/delivery rate tracking (separate analytics spec)
- Patient portal notification delivery (patients receive a subset of events via this same engine)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (message schema)
- [x] All outputs defined (per-channel delivery, DB writes)
- [x] Service interfaces defined (RabbitMQ queue topology)
- [x] Validation rules stated (message schema, template variables)
- [x] Error cases enumerated (permanent failure, retry exhaustion)
- [x] Auth requirements explicit (internal service, no HTTP auth)
- [x] Side effects listed (DB inserts, cache invalidation)
- [x] Examples provided (message payloads, delivery flow)

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (domain separation)
- [x] Uses tenant schema isolation (dynamic search_path for in-app inserts)
- [x] Matches FastAPI/async conventions (aio-pika, asyncio.gather)
- [x] RabbitMQ topology matches infra/background-processing.md

### Hook 3: Security & Privacy
- [x] No HTTP auth needed — internal RabbitMQ exchange
- [x] PHI handling in templates documented
- [x] PHI redacted from Sentry reports
- [x] API keys in environment secrets only

### Hook 4: Performance & Scalability
- [x] Throughput target defined (500 msg/min per worker)
- [x] Horizontal scaling documented
- [x] External API rate limits addressed
- [x] Caching strategy stated

### Hook 5: Observability
- [x] Structured logging per delivery attempt
- [x] Delivery log table defined
- [x] DLQ monitoring with Sentry alerts
- [x] Queue depth alerting mentioned

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy for all external services
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
