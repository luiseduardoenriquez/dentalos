# Twilio SMS Integration Spec

> **Spec ID:** INT-02
> **Status:** Draft
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Twilio SMS integration for sending appointment reminders, OTP verification codes, and notification delivery when WhatsApp is unavailable or not configured. Supports international LATAM country codes (Colombia, Mexico, Chile, Peru, Argentina). Delivery status is tracked via Twilio webhooks. Cost is tracked per tenant. All outbound messages are queue-based via RabbitMQ.

**Domain:** integrations

**Priority:** High

**Dependencies:** INT-01 (WhatsApp Business — SMS is fallback), I-04 (background-processing), I-05 (caching), I-11 (audit-logging)

---

## 1. Provider and Architecture

### Provider

- **Service:** Twilio Programmable SMS
- **API Base:** `https://api.twilio.com/2010-04-01/`
- **Authentication:** HTTP Basic Auth using Account SID and Auth Token
- **SDK:** `twilio` Python library (pinned version)
- **Phone Numbers:** DentalOS purchases one or more Twilio Alphanumeric Sender IDs (where supported) or Long Code numbers per region

### Architecture Overview

```
Trigger (notification service, OTP, WhatsApp fallback)
       │
       ▼
RabbitMQ: sms.outbound queue
       │
       ▼
SMS Worker (consumer)
       │
       ▼
Twilio REST API ──► Carrier Network ──► Patient phone
       │
       ▼
Delivery Status Webhook → FastAPI /webhooks/twilio/status
       │
       ▼
Update message_logs table (tenant schema)
```

### LATAM Phone Number Strategy

| Country | Sender Type | Notes |
|---------|------------|-------|
| Colombia (+57) | Long Code (10DLC) | Alphanumeric sender not supported |
| Mexico (+52) | Alphanumeric Sender ID | Registered brand required |
| Chile (+56) | Alphanumeric Sender ID | Registered brand required |
| Peru (+51) | Long Code | Alphanumeric limited |
| Argentina (+54) | Long Code | Regulatory restrictions |

DentalOS uses a shared Twilio Account SID (sub-accounts per major market) and routes messages through the appropriate sender based on destination country code.

---

## 2. Configuration

### Global Configuration (Environment Variables)

| Variable | Description | Example |
|----------|-------------|---------|
| `TWILIO_ACCOUNT_SID` | Main Twilio Account SID | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_WEBHOOK_AUTH_TOKEN` | Auth token for webhook signature verification | same as above |
| `TWILIO_SENDER_CO` | Colombia sender number | `+15551234567` |
| `TWILIO_SENDER_MX` | Mexico alphanumeric sender | `DentalOS` |
| `TWILIO_SENDER_CL` | Chile alphanumeric sender | `DentalOS` |
| `TWILIO_SENDER_DEFAULT` | Fallback sender | `+15559999999` |

### Tenant-Level Configuration

Tenants do not configure their own Twilio credentials. SMS is sent from DentalOS-owned numbers on behalf of the clinic. The `from_name` is set to the clinic name in the message body when alphanumeric senders are used.

Cost is tracked per tenant (see Section 8).

---

## 3. SMS Use Cases

### 3.1 Appointment Reminders

Sent as fallback when:
- Patient has no WhatsApp, or
- WhatsApp delivery returned `undeliverable`, or
- Tenant does not have WhatsApp configured

**Reminder schedule:**
- 24 hours before appointment
- 2 hours before appointment (optional, clinic configurable)

**Message template:**

```
Recordatorio de cita - {clinic_name}
Hola {first_name}, tienes cita el {date} a las {time}.
Para confirmar responde SI, para cancelar responde NO.
```

Maximum 160 characters (1 SMS unit). If exceeding, message is split into concatenated SMS (counted as multiple units for billing).

### 3.2 OTP Verification Codes

Used for:
- Phone number verification during patient registration
- Two-factor authentication (when enabled by clinic_owner)
- Password reset via phone

**OTP message:**

```
DentalOS: Tu código de verificación es {otp_code}. Válido por 10 minutos. No compartas este código.
```

**OTP properties:**
- 6-digit numeric code
- Expires in 10 minutes
- Maximum 3 attempts before cooldown (5 minutes)
- Rate limit: maximum 5 OTP requests per phone per hour

### 3.3 Notification Delivery

General-purpose notification SMS sent when:
- Email not available and WhatsApp not available
- Patient explicitly prefers SMS
- Urgent notifications (appointment same-day reminder)

---

## 4. Service Implementation

### SMS Service

```python
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TwilioSMSService:
    def __init__(self, account_sid: str, auth_token: str):
        self.client = Client(account_sid, auth_token)

    def get_sender_for_country(self, to_phone: str) -> str:
        """Return appropriate sender for the destination country code."""
        from app.core.config import settings

        if to_phone.startswith("+57"):
            return settings.TWILIO_SENDER_CO
        elif to_phone.startswith("+52"):
            return settings.TWILIO_SENDER_MX
        elif to_phone.startswith("+56"):
            return settings.TWILIO_SENDER_CL
        return settings.TWILIO_SENDER_DEFAULT

    async def send_sms(
        self,
        to_phone: str,
        body: str,
        status_callback_url: Optional[str] = None,
    ) -> dict:
        """
        Send an SMS message via Twilio.
        Returns the Twilio message SID and status.
        """
        from_number = self.get_sender_for_country(to_phone)

        try:
            message = self.client.messages.create(
                to=to_phone,
                from_=from_number,
                body=body,
                status_callback=status_callback_url,
            )
            return {
                "sid": message.sid,
                "status": message.status,
                "num_segments": message.num_segments,
                "price": message.price,
                "price_unit": message.price_unit,
            }
        except TwilioRestException as exc:
            logger.error(
                "Twilio SMS send failed",
                extra={"error_code": exc.code, "error_msg": exc.msg}
            )
            raise
```

### OTP Service

```python
import secrets
import hashlib
from datetime import datetime, timedelta
from app.db.redis import get_redis


class OTPService:
    OTP_TTL_SECONDS = 600       # 10 minutes
    OTP_MAX_ATTEMPTS = 3
    OTP_COOLDOWN_SECONDS = 300  # 5 minutes after max attempts
    OTP_HOURLY_LIMIT = 5

    async def generate_and_send_otp(
        self,
        phone: str,
        purpose: str,   # "verify_phone" | "2fa" | "password_reset"
        tenant_id: str,
    ) -> str:
        """Generate OTP, store in Redis, enqueue SMS."""
        redis = await get_redis()

        # Check hourly rate limit
        rate_key = f"otp:rate:{phone}"
        count = await redis.incr(rate_key)
        if count == 1:
            await redis.expire(rate_key, 3600)
        if count > self.OTP_HOURLY_LIMIT:
            raise RateLimitExceeded(
                "Demasiados códigos solicitados. Intenta en una hora."
            )

        # Generate OTP
        code = "".join([str(secrets.randbelow(10)) for _ in range(6)])

        # Store hashed OTP in Redis
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        otp_key = f"otp:{purpose}:{phone}"
        await redis.setex(
            otp_key,
            self.OTP_TTL_SECONDS,
            f"{code_hash}:0",  # hash:attempts
        )

        # Enqueue SMS
        from app.integrations.sms.jobs import SMSJob
        job = SMSJob(
            tenant_id=tenant_id,
            to_phone=phone,
            body=(
                f"DentalOS: Tu código de verificación es {code}. "
                f"Válido por 10 minutos. No compartas este código."
            ),
            purpose="otp",
        )
        await enqueue_sms_job(job)

        return "OTP enviado"

    async def verify_otp(
        self,
        phone: str,
        code: str,
        purpose: str,
    ) -> bool:
        """Verify OTP code. Returns True if valid."""
        redis = await get_redis()
        otp_key = f"otp:{purpose}:{phone}"
        stored = await redis.get(otp_key)

        if not stored:
            raise InvalidOTP("Código expirado o inválido")

        stored_str = stored.decode() if isinstance(stored, bytes) else stored
        stored_hash, attempts_str = stored_str.split(":", 1)
        attempts = int(attempts_str)

        if attempts >= self.OTP_MAX_ATTEMPTS:
            await redis.delete(otp_key)
            raise OTPLockedOut("Demasiados intentos. Solicita un nuevo código.")

        code_hash = hashlib.sha256(code.encode()).hexdigest()
        if code_hash != stored_hash:
            new_attempts = attempts + 1
            if new_attempts >= self.OTP_MAX_ATTEMPTS:
                await redis.delete(otp_key)
                # Set cooldown
                cooldown_key = f"otp:cooldown:{phone}"
                await redis.setex(cooldown_key, self.OTP_COOLDOWN_SECONDS, "1")
                raise OTPLockedOut("Código incorrecto. Solicita un nuevo código.")

            await redis.setex(
                otp_key,
                await redis.ttl(otp_key),
                f"{stored_hash}:{new_attempts}",
            )
            raise InvalidOTP(f"Código incorrecto. {self.OTP_MAX_ATTEMPTS - new_attempts} intento(s) restante(s).")

        await redis.delete(otp_key)
        return True
```

---

## 5. Queue-Based Delivery (RabbitMQ)

### Queue Configuration

| Queue | Exchange | Routing Key | Consumer |
|-------|----------|-------------|---------|
| `sms.outbound` | `notifications` | `sms.send` | `SMSWorker` |
| `sms.outbound.dlq` | `notifications.dlq` | `sms.dead` | `DLQMonitor` |

### Job Payload Schema

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class SMSJob(BaseModel):
    job_id: str = str(uuid.uuid4())
    tenant_id: str
    message_log_id: Optional[str] = None
    to_phone: str               # E.164 format
    body: str                   # Message text (max 1600 chars for concatenated)
    purpose: str                # "reminder" | "otp" | "notification" | "fallback_whatsapp"
    # Fallback context:
    fallback_from: Optional[str] = None   # "whatsapp" if this is a fallback
    original_message_log_id: Optional[str] = None
    # Metadata:
    attempt: int = 0
    max_attempts: int = 3
    created_at: datetime = datetime.utcnow()
```

### Worker Implementation

```python
import logging
from app.integrations.sms.service import TwilioSMSService
from app.integrations.sms.jobs import SMSJob
from app.core.config import settings

logger = logging.getLogger(__name__)


class SMSWorker:
    def __init__(self):
        self.service = TwilioSMSService(
            account_sid=settings.TWILIO_ACCOUNT_SID,
            auth_token=settings.TWILIO_AUTH_TOKEN,
        )
        self.callback_url = f"{settings.API_BASE_URL}/api/v1/webhooks/twilio/status"

    async def process_job(self, job: SMSJob) -> None:
        try:
            result = await self.service.send_sms(
                to_phone=job.to_phone,
                body=job.body,
                status_callback_url=self.callback_url,
            )

            # Update message log
            async with get_tenant_session(job.tenant_id) as session:
                await update_message_log_status(
                    session,
                    job.message_log_id,
                    status="sent",
                    provider_message_id=result["sid"],
                    cost=result.get("price"),
                    cost_unit=result.get("price_unit"),
                )

            logger.info(
                "SMS sent",
                extra={
                    "tenant_id": job.tenant_id,
                    "twilio_sid": result["sid"],
                    "purpose": job.purpose,
                }
            )

        except Exception as exc:
            logger.error(
                "SMS send failed",
                extra={"tenant_id": job.tenant_id, "error": str(exc)}
            )
            raise
```

### Retry Logic

| Attempt | Delay | Behavior |
|---------|-------|---------|
| 1st | Immediate | Normal processing |
| 2nd | 2 minutes | After nack |
| 3rd | 10 minutes | After second nack |
| 4th | Dead letter | Permanent failure, alert |

OTP messages: **No retries** — user must request a new code. Only reminder/notification messages retry.

---

## 6. Delivery Status Webhook

### Endpoint

```
POST /api/v1/webhooks/twilio/status
```

Public endpoint. Verified via Twilio signature.

### Twilio Signature Verification

```python
from twilio.request_validator import RequestValidator
from fastapi import Request, HTTPException
from app.core.config import settings


async def verify_twilio_signature(request: Request) -> None:
    """Verify Twilio webhook signature."""
    validator = RequestValidator(settings.TWILIO_WEBHOOK_AUTH_TOKEN)
    url = str(request.url)
    form_data = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")

    if not validator.validate(url, dict(form_data), signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
```

### Status Update Handler

```python
from fastapi import APIRouter, Request, Form
from typing import Optional

router = APIRouter()

@router.post("/webhooks/twilio/status")
async def twilio_status_callback(
    request: Request,
    MessageSid: str = Form(...),
    MessageStatus: str = Form(...),
    To: str = Form(...),
    From: str = Form(...),
    ErrorCode: Optional[str] = Form(None),
    Price: Optional[str] = Form(None),
    PriceUnit: Optional[str] = Form(None),
):
    await verify_twilio_signature(request)

    # Look up message log by provider_message_id = MessageSid
    # Update status in message_logs
    # If failed: log error code, trigger fallback if applicable

    status_map = {
        "queued": "queued",
        "sending": "sending",
        "sent": "sent",
        "delivered": "delivered",
        "undelivered": "undelivered",
        "failed": "failed",
    }

    await handle_sms_status_update(
        provider_message_id=MessageSid,
        status=status_map.get(MessageStatus, "unknown"),
        error_code=ErrorCode,
        cost=Price,
        cost_unit=PriceUnit,
    )
    return {"status": "ok"}
```

### Twilio Error Codes

| Error Code | Meaning | Handling |
|-----------|---------|---------|
| 30003 | Unreachable destination | Mark undeliverable |
| 30004 | Message blocked | Check carrier filtering |
| 30005 | Unknown destination handset | Phone may be off, retry once |
| 30006 | Landline or unreachable | Mark undeliverable |
| 30007 | Carrier violation | Content or sender issue |
| 30008 | Unknown error | Retry once |
| 21211 | Invalid phone number | Validate E.164 format |
| 21408 | Permission restricted | Country blocked |

---

## 7. Rate Limiting

### DentalOS Application-Level Limits

```python
async def check_sms_rate_limit(
    redis,
    tenant_id: str,
    to_phone: str,
    purpose: str,
) -> None:
    """Enforce per-phone and per-tenant SMS rate limits."""
    if purpose == "otp":
        # OTP: 5 per phone per hour
        key = f"sms:otp:rate:{to_phone}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 3600)
        if count > 5:
            raise RateLimitExceeded(
                "Demasiados códigos OTP solicitados. Espera una hora."
            )
    else:
        # Reminders/notifications: 3 per phone per day
        key = f"sms:daily:{tenant_id}:{to_phone}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 86400)
        if count > 3:
            raise RateLimitExceeded(
                "Límite diario de SMS para este número alcanzado."
            )
```

### Tenant-Level Daily Limits

| Plan | SMS/day |
|------|---------|
| Free | 50 |
| Starter | 500 |
| Pro | 2,000 |
| Clínica | 5,000 |

---

## 8. Cost Tracking

### Twilio Pricing (Approximate, 2026)

| Country | Outbound SMS Price (USD) |
|---------|--------------------------|
| Colombia | $0.0400 |
| Mexico | $0.0500 |
| Chile | $0.0450 |

### Cost Tracking Table (Tenant Schema)

```sql
CREATE TABLE sms_cost_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    month           DATE NOT NULL,
    to_country      VARCHAR(5),         -- ISO country code
    purpose         VARCHAR(30),        -- reminder | otp | notification
    message_count   INTEGER NOT NULL,
    segment_count   INTEGER NOT NULL,   -- SMS units (each 160 chars)
    cost_usd        NUMERIC(10, 6),
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

Cost is populated from Twilio delivery webhook `Price` and `PriceUnit` fields.

---

## 9. Message Character Limits

| Encoding | Max per SMS | Max concatenated |
|----------|------------|-----------------|
| GSM-7 (ASCII + basic) | 160 chars | 1530 chars (10 parts) |
| Unicode (emojis, accented) | 70 chars | 630 chars (9 parts) |

All DentalOS SMS messages are crafted in GSM-7 compatible Spanish (avoiding emojis and rare accented characters where possible). If a message requires Unicode (patient name with special chars), it automatically splits into multiple segments.

**Message length validation:**

```python
def validate_sms_body(body: str) -> dict:
    """Return character count, encoding, and segment count."""
    import re
    gsm7_chars = set(
        "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./"
        "0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§"
        "¿abcdefghijklmnopqrstuvwxyzäöñüà"
    )
    is_gsm7 = all(c in gsm7_chars for c in body)
    if is_gsm7:
        max_single = 160
        max_part = 153
    else:
        max_single = 70
        max_part = 67

    length = len(body)
    if length <= max_single:
        segments = 1
    else:
        segments = (length + max_part - 1) // max_part

    return {"length": length, "encoding": "GSM-7" if is_gsm7 else "Unicode", "segments": segments}
```

---

## 10. Inbound SMS (Optional)

DentalOS can optionally configure a Twilio inbound number to receive patient replies (SI/NO for appointment confirmation).

**Webhook:**
```
POST /api/v1/webhooks/twilio/inbound
```

**Auto-response mapping (same as WhatsApp):**

| Patient Reply | Action |
|---------------|--------|
| `SI`, `SÍ`, `1` | Confirm appointment |
| `NO`, `2` | Cancel appointment |
| Other | Route to staff notification |

---

## 11. Message Log Table (Tenant Schema)

SMS messages share the `message_logs` table with WhatsApp (INT-01), filtered by `channel = 'sms'`.

Additional SMS-specific fields tracked:
- `num_segments` — number of SMS billing units
- `cost_usd` — from Twilio delivery webhook
- `error_code` — Twilio error code if failed

---

## Out of Scope

- MMS (multimedia messages) — not planned
- Twilio Verify API (DentalOS implements own OTP with Redis for cost control)
- Twilio Studio flows
- WhatsApp via Twilio Business — use INT-01 (Meta direct) instead
- Two-way conversational SMS chatbot

---

## Acceptance Criteria

**This integration is complete when:**

- [ ] OTP codes sent and verified end-to-end for phone number verification
- [ ] Appointment reminder SMS sends correctly with patient name, date, time
- [ ] Delivery status (sent/delivered/failed) tracked via webhook
- [ ] Twilio signature verification rejects tampered requests
- [ ] Rate limits enforced per phone and per tenant
- [ ] SMS fallback triggered when WhatsApp delivery fails with undeliverable status
- [ ] Cost tracking populated from delivery webhook
- [ ] Country-specific sender routing works (CO, MX, CL)
- [ ] Character limit validation prevents over-length messages

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All use cases defined (OTP, reminders, fallback)
- [x] Queue architecture defined
- [x] Webhook handling defined (status + inbound)
- [x] Error codes handled
- [x] Rate limits defined

### Hook 2: Architecture Compliance
- [x] Queue-based delivery via RabbitMQ
- [x] Async worker pattern
- [x] Shared message_logs table

### Hook 3: Security & Privacy
- [x] Webhook signature verification
- [x] OTP hashed in Redis (SHA-256)
- [x] Rate limiting on OTP (anti-abuse)
- [x] No PHI in message body (name/time only)

### Hook 4: Performance & Scalability
- [x] Retry logic per message type
- [x] Per-tenant daily limits
- [x] Segment counting for cost control

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
