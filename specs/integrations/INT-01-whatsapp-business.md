# WhatsApp Business API Integration Spec

> **Spec ID:** INT-01
> **Status:** Draft
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Integration with the Meta WhatsApp Business Platform API (Cloud API) for sending appointment reminders, payment reminders, treatment plan notifications, and supporting two-way chat with patients. Messages are delivered via a queue-based architecture using RabbitMQ to ensure reliability and rate-limit compliance.

**Domain:** integrations

**Priority:** High

**Dependencies:** I-04 (background-processing), I-05 (caching), I-11 (audit-logging), notifications domain specs

---

## 1. Provider and Architecture

### Provider

- **Service:** Meta WhatsApp Business Platform — Cloud API (hosted by Meta, no on-premise BSP)
- **API Base:** `https://graph.facebook.com/v20.0/`
- **Authentication:** System User Access Token (long-lived, non-expiring, scoped to `whatsapp_business_messaging`)
- **Phone Number:** One dedicated WhatsApp Business phone number per tenant (each clinic registers their own number via the Meta Business Manager, linked to DentalOS via the shared WABA — WhatsApp Business Account)

### Architecture Overview

```
Clinic Action (appt confirmed, payment due, etc.)
       │
       ▼
RabbitMQ: whatsapp.outbound queue
       │
       ▼
WhatsApp Worker (consumer)
       │
  ┌────┴────────────────────────────┐
  │  Template message? → Template API │
  │  Session message?  → Messages API │
  └────────────────────────────────┘
       │
       ▼
Meta Graph API ──► Patient WhatsApp
       │
       ▼
Delivery webhook → FastAPI /webhooks/whatsapp
       │
       ▼
Update message_logs table (tenant schema)
```

### Configuration per Tenant

Each tenant that subscribes to WhatsApp notifications must complete:

1. Meta Business Verification (business identity verified by Meta)
2. Display name approval
3. WhatsApp Business Account (WABA) creation and linking to DentalOS system user
4. Phone number registration and verification (OTP)
5. Template submission and approval (per template category)

**Tenant WhatsApp config stored in `public.tenant_whatsapp_config`:**

```sql
CREATE TABLE public.tenant_whatsapp_config (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id),
    waba_id         VARCHAR(50) NOT NULL,           -- WhatsApp Business Account ID
    phone_number_id VARCHAR(50) NOT NULL,           -- Registered phone number ID (Meta)
    display_phone   VARCHAR(20) NOT NULL,           -- E.164 format: +573001234567
    access_token    TEXT NOT NULL,                  -- Encrypted system user access token
    is_active       BOOLEAN DEFAULT TRUE,
    verified_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## 2. Message Templates

### Purpose

Template messages (HSM — Highly Structured Messages) are required for:
- Outbound messages to patients who have not messaged the clinic in the last 24 hours
- Appointment reminders
- Payment reminders
- Treatment plan ready notifications

Templates must be pre-approved by Meta before use. Approval typically takes 24–72 hours.

### Template Categories

| Category | Use Case | Meta Category | Cost Tier |
|----------|----------|---------------|-----------|
| `appointment_reminder_24h` | Reminder 24h before appointment | UTILITY | Utility |
| `appointment_reminder_1h` | Reminder 1h before appointment | UTILITY | Utility |
| `appointment_confirmed` | Appointment confirmation | UTILITY | Utility |
| `appointment_cancelled` | Appointment cancellation | UTILITY | Utility |
| `appointment_rescheduled` | Rescheduled notification | UTILITY | Utility |
| `payment_reminder` | Outstanding balance reminder | UTILITY | Utility |
| `treatment_plan_ready` | Treatment plan created and ready | UTILITY | Utility |
| `quotation_ready` | Cost quotation ready to review | UTILITY | Utility |
| `consent_signature_required` | Consent pending signature | UTILITY | Utility |
| `prescription_ready` | Prescription available | UTILITY | Utility |

### Template Registration

Templates are defined in DentalOS and submitted to Meta via the API. They are registered once at the WABA level and can be used by all tenants under that WABA.

**Template definition model:**

```python
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class TemplateComponentType(str, Enum):
    HEADER = "HEADER"
    BODY = "BODY"
    FOOTER = "FOOTER"
    BUTTONS = "BUTTONS"


class TemplateLanguage(str, Enum):
    ES = "es"          # Spanish (generic)
    ES_CO = "es_CO"    # Spanish (Colombia)
    ES_MX = "es_MX"    # Spanish (Mexico)
    PT_BR = "pt_BR"    # Portuguese (Brazil — future)


class WhatsAppTemplate(BaseModel):
    name: str                    # snake_case, e.g., "appointment_reminder_24h"
    language: TemplateLanguage
    category: str                # UTILITY | MARKETING | AUTHENTICATION
    components: List[dict]       # Header, body, footer, buttons

APPOINTMENT_REMINDER_24H = WhatsAppTemplate(
    name="appointment_reminder_24h",
    language=TemplateLanguage.ES,
    category="UTILITY",
    components=[
        {
            "type": "BODY",
            "text": (
                "Hola {{1}}, te recordamos que tienes una cita dental mañana "
                "a las {{2}} en {{3}}. "
                "Para confirmar responde *SI*, para cancelar responde *NO*."
            ),
            "example": {
                "body_text": [["María García", "10:00 AM", "Clínica DentoVita"]]
            }
        },
        {
            "type": "FOOTER",
            "text": "No respondas con información personal"
        }
    ]
)
```

### Template Variable Mapping

| Template Variable | Source Field |
|-------------------|-------------|
| `{{1}}` | `patient.first_name` |
| `{{2}}` | `appointment.scheduled_at` formatted per locale |
| `{{3}}` | `tenant.clinic_name` |
| `{{4}}` | `appointment.doctor_name` (when applicable) |
| `{{5}}` | `invoice.total_amount` formatted as currency |

---

## 3. Message Sending — API Interface

### Outbound Message Service

```python
import httpx
from typing import Optional
from app.integrations.whatsapp.models import (
    WhatsAppOutboundMessage,
    MessageType,
    DeliveryStatus,
)
from app.core.config import settings


class WhatsAppService:
    BASE_URL = "https://graph.facebook.com/v20.0"

    async def send_template_message(
        self,
        phone_number_id: str,
        access_token: str,
        to_phone: str,
        template_name: str,
        language_code: str,
        variables: list[str],
    ) -> dict:
        """
        Send a pre-approved template message.
        to_phone must be in E.164 format (e.g., +573001234567).
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": var} for var in variables
                        ],
                    }
                ],
            },
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.BASE_URL}/{phone_number_id}/messages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def send_session_message(
        self,
        phone_number_id: str,
        access_token: str,
        to_phone: str,
        text: str,
    ) -> dict:
        """
        Send a free-form text message within an active 24h session window.
        Only valid when the patient has messaged the clinic within the last 24 hours.
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {"body": text, "preview_url": False},
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.BASE_URL}/{phone_number_id}/messages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return response.json()
```

---

## 4. Queue-Based Delivery (RabbitMQ)

### Queue Configuration

| Queue | Exchange | Routing Key | Consumer | Purpose |
|-------|----------|-------------|----------|---------|
| `whatsapp.outbound` | `notifications` | `whatsapp.send` | `WhatsAppWorker` | Messages to send |
| `whatsapp.outbound.dlq` | `notifications.dlq` | `whatsapp.dead` | `DLQMonitor` | Failed after retries |
| `whatsapp.webhook` | `webhooks` | `whatsapp.status` | `WhatsAppStatusWorker` | Delivery status updates |

### Job Payload Schema

```python
from pydantic import BaseModel
from typing import Optional
from enum import Enum
import uuid
from datetime import datetime


class WhatsAppMessageType(str, Enum):
    TEMPLATE = "template"
    SESSION = "session"


class WhatsAppJob(BaseModel):
    job_id: str = str(uuid.uuid4())
    tenant_id: str
    message_log_id: str         # FK to message_logs for tracking
    phone_number_id: str        # Meta phone number ID (from tenant config)
    to_phone: str               # E.164 format
    message_type: WhatsAppMessageType
    # For template messages:
    template_name: Optional[str] = None
    template_language: Optional[str] = "es"
    template_variables: Optional[list[str]] = None
    # For session messages:
    text: Optional[str] = None
    # Metadata:
    scheduled_at: Optional[datetime] = None   # For delayed sends
    attempt: int = 0
    max_attempts: int = 3
    created_at: datetime = datetime.utcnow()
```

### Worker Implementation

```python
import asyncio
import aio_pika
import json
import logging
from app.integrations.whatsapp.service import WhatsAppService
from app.integrations.whatsapp.jobs import WhatsAppJob
from app.db.tenant import get_tenant_session
from app.repositories.whatsapp import (
    get_tenant_whatsapp_config,
    update_message_log_status,
)

logger = logging.getLogger(__name__)


class WhatsAppWorker:
    def __init__(self, rabbitmq_url: str):
        self.rabbitmq_url = rabbitmq_url
        self.service = WhatsAppService()

    async def process_job(self, job: WhatsAppJob) -> None:
        async with get_tenant_session(job.tenant_id) as session:
            config = await get_tenant_whatsapp_config(session, job.tenant_id)
            if not config or not config.is_active:
                logger.warning(
                    "WhatsApp not configured for tenant",
                    extra={"tenant_id": job.tenant_id}
                )
                return

            try:
                if job.message_type == "template":
                    result = await self.service.send_template_message(
                        phone_number_id=config.phone_number_id,
                        access_token=config.access_token,
                        to_phone=job.to_phone,
                        template_name=job.template_name,
                        language_code=job.template_language,
                        variables=job.template_variables or [],
                    )
                else:
                    result = await self.service.send_session_message(
                        phone_number_id=config.phone_number_id,
                        access_token=config.access_token,
                        to_phone=job.to_phone,
                        text=job.text,
                    )

                meta_message_id = result.get("messages", [{}])[0].get("id")
                await update_message_log_status(
                    session,
                    job.message_log_id,
                    status="sent",
                    provider_message_id=meta_message_id,
                )
                logger.info(
                    "WhatsApp message sent",
                    extra={
                        "tenant_id": job.tenant_id,
                        "meta_message_id": meta_message_id,
                    }
                )

            except Exception as exc:
                logger.error(
                    "WhatsApp send failed",
                    extra={"tenant_id": job.tenant_id, "error": str(exc)}
                )
                await update_message_log_status(
                    session, job.message_log_id, status="failed"
                )
                raise  # Re-queue by aio_pika nack
```

### Retry Logic

| Attempt | Delay | Behavior |
|---------|-------|---------|
| 1st | Immediate | Process normally |
| 2nd | 5 minutes | After nack with `requeue=False` → DLQ with TTL |
| 3rd | 30 minutes | From DLQ with TTL |
| 4th+ | Dead letter | Move to permanent DLQ, alert on-call |

---

## 5. Inbound Webhook — Patient Replies

### Webhook Endpoint

```
POST /api/v1/webhooks/whatsapp
```

This endpoint is public (no auth header required) but verified via Meta webhook signature verification.

### Webhook Verification (GET)

Meta sends a GET request to verify the webhook on registration:

```
GET /api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=TOKEN&hub.challenge=CHALLENGE
```

**Handler:**

```python
from fastapi import APIRouter, Query, HTTPException
from app.core.config import settings

router = APIRouter()

@router.get("/webhooks/whatsapp")
async def whatsapp_webhook_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")
```

### Webhook Signature Verification

All inbound POST webhooks are verified using the Meta app secret:

```python
import hmac
import hashlib
from fastapi import Request, HTTPException
from app.core.config import settings


async def verify_whatsapp_signature(request: Request) -> bytes:
    """Verify Meta webhook signature (X-Hub-Signature-256 header)."""
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header.startswith("sha256="):
        raise HTTPException(status_code=403, detail="Missing signature")

    body = await request.body()
    expected = hmac.new(
        settings.WHATSAPP_APP_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header[7:]
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=403, detail="Invalid signature")
    return body
```

### Inbound Message Processing

When a patient replies to a WhatsApp message:

1. Webhook fires on DentalOS (`POST /webhooks/whatsapp`)
2. Signature verified
3. Phone number matched to patient via `patients.phone` (E.164)
4. Phone number matched to tenant via `tenant_whatsapp_config.display_phone`
5. Message stored in `tenant_schema.whatsapp_messages` table
6. Session window updated (24h counter resets)
7. If reply is `SI`/`NO` to appointment reminder → trigger appointment confirm/cancel flow
8. Otherwise → enqueue for human staff review (`whatsapp.inbound` queue)

**Auto-response mapping:**

| Patient Reply | Action Triggered |
|---------------|-----------------|
| `SI`, `SÍ`, `1`, `s`, `si` | Confirm appointment (call appointment confirm handler) |
| `NO`, `2`, `n`, `no` | Cancel appointment (call appointment cancel handler) |
| Any other text | Route to staff inbox, send acknowledgment template |

---

## 6. Message Log Table

Stored in the **tenant schema** (`{tenant_id}.message_logs`):

```sql
CREATE TABLE message_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel             VARCHAR(20) NOT NULL DEFAULT 'whatsapp',
    direction           VARCHAR(10) NOT NULL CHECK (direction IN ('outbound', 'inbound')),
    to_phone            VARCHAR(20),
    from_phone          VARCHAR(20),
    patient_id          UUID,
    template_name       VARCHAR(100),
    message_type        VARCHAR(20),        -- template | session | text
    body_preview        VARCHAR(500),       -- First 500 chars (no PHI in logs)
    status              VARCHAR(30) NOT NULL DEFAULT 'queued',
    -- status: queued | sent | delivered | read | failed | undeliverable
    provider_message_id VARCHAR(100),       -- Meta message ID
    sent_at             TIMESTAMPTZ,
    delivered_at        TIMESTAMPTZ,
    read_at             TIMESTAMPTZ,
    failed_at           TIMESTAMPTZ,
    failure_reason      VARCHAR(255),
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_message_logs_patient_id ON message_logs(patient_id);
CREATE INDEX idx_message_logs_provider_message_id ON message_logs(provider_message_id);
CREATE INDEX idx_message_logs_status ON message_logs(status);
CREATE INDEX idx_message_logs_created_at ON message_logs(created_at);
```

---

## 7. Rate Limits

### Meta WhatsApp Business API Rate Limits

| Tier | Limit | Applies To |
|------|-------|-----------|
| Free tier | 1,000 unique users/day | Per WABA |
| Tier 1 | 10,000 unique users/day | After quality score met |
| Tier 2 | 100,000 unique users/day | After quality score met |
| Tier 3 | Unlimited | Enterprise |

### DentalOS Application Rate Limits

In addition to Meta limits, DentalOS enforces:
- Maximum 3 outbound messages per patient per 24-hour window (prevents spam)
- Maximum 500 template messages per tenant per day on starter plan
- Maximum 2,000 template messages per tenant per day on pro/clinica plans

**Rate limit check before enqueue:**

```python
async def check_whatsapp_rate_limit(
    redis: Redis,
    tenant_id: str,
    patient_phone: str,
) -> None:
    """
    Check per-patient daily limit.
    Raises RateLimitExceeded if limit reached.
    """
    key = f"whatsapp:patient_daily:{tenant_id}:{patient_phone}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 86400)  # 24h TTL
    if count > 3:
        raise RateLimitExceeded("Límite de mensajes WhatsApp para este paciente alcanzado")
```

---

## 8. Cost Tracking

### Meta Pricing Model

WhatsApp Business charges per conversation (24h window), not per message. Pricing varies by country and conversation category:

| Country | Utility Conversation | Marketing Conversation |
|---------|---------------------|----------------------|
| Colombia | ~$0.015 USD | ~$0.045 USD |
| Mexico | ~$0.020 USD | ~$0.060 USD |
| Chile | ~$0.018 USD | ~$0.054 USD |

### Cost Tracking per Tenant

```sql
-- In tenant schema
CREATE TABLE whatsapp_cost_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    month           DATE NOT NULL,              -- First day of the month
    conversation_id VARCHAR(100),               -- Meta conversation ID
    category        VARCHAR(30),                -- utility | marketing | authentication
    cost_usd        NUMERIC(10, 6),
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## 9. Error Handling

### Meta API Error Codes

| Error Code | Meaning | Handling |
|-----------|---------|---------|
| 130429 | Rate limit hit (high volume) | Exponential backoff, retry after `retry_after` |
| 131047 | Re-engagement message to 24h expired window | Use template instead of session message |
| 131026 | Recipient phone not registered on WhatsApp | Mark as `undeliverable`, try SMS fallback |
| 131000 | Message failed (generic) | Log, alert, try once more |
| 130472 | Invalid recipient format | Validate E.164 format; reject and log |
| 132000 | Template does not exist | Alert admin, disable template until re-approved |
| 100 | Invalid access token | Alert superadmin, mark tenant config inactive |

### Fallback to SMS

When WhatsApp delivery fails with error `131026` (phone not on WhatsApp):
1. Mark WhatsApp message as `undeliverable`
2. Enqueue fallback SMS job to `sms.outbound` queue (see INT-02)
3. Log fallback in `message_logs` with `fallback_from: whatsapp`

---

## 10. Security Considerations

- Access tokens stored encrypted (AES-256-GCM) in `public.tenant_whatsapp_config.access_token`
- Webhook verify token stored in environment variable `WHATSAPP_VERIFY_TOKEN`
- App secret stored in environment variable `WHATSAPP_APP_SECRET`
- Patient phone numbers in message logs are stored as plain E.164 (no PHI encryption at this level — phone is already in `patients` table encrypted)
- No clinical content (diagnoses, procedures) in WhatsApp messages — only scheduling and administrative data
- Template variables limited to: name, date/time, clinic name, amount — never clinical data

---

## 11. Meta Business Verification Process

### Steps for Onboarding a New Tenant

1. Tenant admin visits `Settings → Notifications → WhatsApp Setup`
2. DentalOS initiates embedded signup flow (Meta Business Login)
3. Clinic completes Meta Business Verification (requires: business registration document, website, phone)
4. Meta reviews and approves (1–5 business days)
5. DentalOS links the clinic's phone number to the shared WABA (or tenant creates own WABA)
6. Phone number registered and OTP-verified
7. Default templates submitted for approval
8. Templates approved (24–72 hours)
9. Tenant WhatsApp config marked `is_active = true`

---

## 12. Configuration Reference

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `WHATSAPP_APP_ID` | Meta App ID | `1234567890` |
| `WHATSAPP_APP_SECRET` | Meta App Secret (for webhook sig) | `abc123...` |
| `WHATSAPP_VERIFY_TOKEN` | Static webhook verify token | `dentalos_wh_token_abc` |
| `WHATSAPP_DEFAULT_LANGUAGE` | Default template language | `es` |

---

## Out of Scope

- Two-way conversational chat UI (staff messaging inbox — see `messages/` domain)
- WhatsApp Business API on-premise (BSP) deployment
- WhatsApp Flows (interactive forms) — future feature
- Broadcast/bulk marketing messages (marketing templates — not planned for v1)
- Auto-replies beyond SI/NO appointment confirmation

---

## Acceptance Criteria

**This integration is complete when:**

- [ ] Template messages send successfully for appointment reminders (24h and 1h)
- [ ] Delivery status (sent/delivered/read) tracked in `message_logs`
- [ ] Inbound SI/NO replies trigger appointment confirm/cancel flows
- [ ] Webhook signature verification rejects invalid requests
- [ ] Fallback to SMS when phone not registered on WhatsApp
- [ ] Per-patient rate limiting (3 messages/day) enforced
- [ ] Access tokens stored encrypted at rest
- [ ] Cost tracking logs populated per conversation
- [ ] Worker processes jobs from RabbitMQ queue with retry logic
- [ ] Dead-letter queue alerts fire after 3 failed attempts

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] Provider and authentication defined
- [x] Message templates defined with variable mappings
- [x] Queue architecture defined
- [x] Webhook handling defined (inbound + verification)
- [x] Error codes and handling defined
- [x] Rate limits defined

### Hook 2: Architecture Compliance
- [x] Queue-based delivery via RabbitMQ
- [x] Tenant config isolated (public schema)
- [x] Message logs in tenant schema

### Hook 3: Security & Privacy
- [x] Webhook signature verification
- [x] Access token encryption at rest
- [x] No PHI/clinical data in message content
- [x] Rate limiting per patient

### Hook 4: Performance & Scalability
- [x] Async worker with backpressure
- [x] Retry with exponential backoff
- [x] Dead-letter queue for permanent failures

### Hook 5: Observability
- [x] Structured logging with tenant_id
- [x] Message log table for delivery tracking
- [x] Cost tracking per tenant/month

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
