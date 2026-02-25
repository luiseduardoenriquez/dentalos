# Email Delivery Engine Spec

> **Spec ID:** INT-03
> **Status:** Draft
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Transactional email delivery engine using SendGrid as the primary provider and Amazon SES as failover. Handles template management with MJML/HTML templates, placeholder parsing, delivery tracking, bounce handling, and tenant-branded sender configuration. All email delivery is queue-based via RabbitMQ. Domain verification (SPF/DKIM) is required per tenant for branded sending.

**Domain:** integrations

**Priority:** High

**Dependencies:** I-04 (background-processing), I-05 (caching), I-11 (audit-logging), notifications domain

---

## 1. Provider Strategy

### Primary: SendGrid

- **API:** SendGrid Web API v3 (`https://api.sendgrid.com/v3/`)
- **Authentication:** API key (`SG.xxxx`)
- **Use case:** All transactional emails (appointment reminders, invoices, treatment plans, consent PDFs, OTPs, onboarding)
- **Features used:** Template engine, event webhooks, suppression management, domain authentication

### Fallback: Amazon SES

- **API:** AWS SDK (`boto3.client('ses', region_name='us-east-1')`)
- **Use case:** Fallback when SendGrid is unreachable or returns 5xx errors
- **Trigger:** SendGrid API returns HTTP 5xx on 2 consecutive attempts within 60 seconds

### Provider Selection Logic

```python
from enum import Enum


class EmailProvider(str, Enum):
    SENDGRID = "sendgrid"
    SES = "ses"


class EmailProviderRouter:
    def __init__(self, redis):
        self.redis = redis
        self.CIRCUIT_BREAKER_KEY = "email:provider:circuit"
        self.CIRCUIT_OPEN_TTL = 300  # 5 min before retry

    async def get_provider(self) -> EmailProvider:
        """
        Return active provider. Falls back to SES if SendGrid circuit is open.
        """
        circuit_open = await self.redis.get(self.CIRCUIT_BREAKER_KEY)
        if circuit_open:
            return EmailProvider.SES
        return EmailProvider.SENDGRID

    async def report_failure(self) -> None:
        """Open circuit breaker — switch to SES for 5 minutes."""
        await self.redis.setex(
            self.CIRCUIT_BREAKER_KEY, self.CIRCUIT_OPEN_TTL, "open"
        )

    async def report_success(self) -> None:
        """Reset circuit breaker."""
        await self.redis.delete(self.CIRCUIT_BREAKER_KEY)
```

---

## 2. Template System

### Template Storage

Email templates are stored as MJML source files in the DentalOS repository at `backend/email_templates/`. At deploy time, templates are compiled from MJML → HTML and stored in Redis with versioning.

**Template directory structure:**

```
backend/email_templates/
├── base/
│   ├── layout.mjml          # Base layout with logo, footer, unsubscribe
│   └── colors.mjml          # Brand color variables
├── appointments/
│   ├── reminder_24h.mjml
│   ├── confirmation.mjml
│   └── cancellation.mjml
├── billing/
│   ├── invoice_created.mjml
│   ├── invoice_paid.mjml
│   └── quotation_ready.mjml
├── clinical/
│   ├── treatment_plan_ready.mjml
│   └── consent_signature_required.mjml
├── auth/
│   ├── welcome.mjml
│   ├── password_reset.mjml
│   ├── email_verification.mjml
│   └── otp_code.mjml
└── admin/
    ├── trial_expiring.mjml
    └── subscription_cancelled.mjml
```

### Template Compilation

MJML is compiled to HTML at deploy time (not at send time):

```python
import subprocess
import json


def compile_mjml_template(mjml_source: str) -> str:
    """Compile MJML to HTML using mjml CLI."""
    result = subprocess.run(
        ["mjml", "--stdin", "--output", "-"],
        input=mjml_source.encode(),
        capture_output=True,
    )
    if result.returncode != 0:
        raise ValueError(f"MJML compilation failed: {result.stderr.decode()}")
    return result.stdout.decode()
```

### Placeholder Syntax

All templates use `{{variable_name}}` double-brace syntax. Placeholders are resolved at send time by the `TemplatePlaceholderParser`.

**Standard placeholders:**

| Placeholder | Value | Required |
|------------|-------|---------|
| `{{patient_first_name}}` | Patient first name | Contextual |
| `{{patient_full_name}}` | Patient full name | Contextual |
| `{{clinic_name}}` | Tenant clinic name | Always |
| `{{clinic_phone}}` | Tenant contact phone | Always |
| `{{clinic_email}}` | Tenant contact email | Always |
| `{{clinic_address}}` | Tenant address | Always |
| `{{clinic_logo_url}}` | Signed URL to clinic logo | Always |
| `{{doctor_name}}` | Doctor full name | Contextual |
| `{{appointment_date}}` | Formatted appointment date | Appointment emails |
| `{{appointment_time}}` | Formatted appointment time | Appointment emails |
| `{{appointment_type}}` | Treatment/appointment label | Appointment emails |
| `{{invoice_number}}` | Invoice number | Billing emails |
| `{{invoice_total}}` | Formatted total amount | Billing emails |
| `{{invoice_pdf_url}}` | Signed URL to invoice PDF | Billing emails |
| `{{treatment_plan_url}}` | Link to patient portal | Clinical emails |
| `{{otp_code}}` | 6-digit OTP | Auth emails |
| `{{reset_link}}` | Password reset URL | Auth emails |
| `{{unsubscribe_url}}` | Unsubscribe link | All marketing |
| `{{current_year}}` | Current year (e.g., 2026) | Footer |

### Placeholder Parser

```python
import re
from typing import Dict


class TemplatePlaceholderParser:
    PATTERN = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}")

    def render(self, template_html: str, context: Dict[str, str]) -> str:
        """
        Replace all {{variable}} placeholders in the template.
        Raises MissingPlaceholderError for any unresolved variable.
        """
        missing = []

        def replace_match(match: re.Match) -> str:
            key = match.group(1)
            if key not in context:
                missing.append(key)
                return match.group(0)  # Leave as-is, collect errors
            return self._escape_html(context[key])

        rendered = self.PATTERN.sub(replace_match, template_html)

        if missing:
            raise MissingPlaceholderError(
                f"Missing placeholders: {', '.join(missing)}"
            )
        return rendered

    @staticmethod
    def _escape_html(value: str) -> str:
        """Escape HTML special characters to prevent XSS via email content."""
        return (
            value
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
```

---

## 3. Tenant-Branded Sending

### From Address Format

```
from_name: "{clinic_name}"
from_email: "noreply@{verified_domain}"
reply_to: "{clinic_contact_email}"
```

**Examples:**
- `"Clínica DentoVita" <noreply@dentovita.co>`
- `"DentalOS" <noreply@dentalos.app>` (when no custom domain configured)

### Domain Verification (SPF/DKIM)

To send from a custom domain (e.g., `@dentovita.co`), the clinic must verify domain ownership via DNS records.

**Required DNS records (provided by DentalOS to clinic):**

```
# DKIM — Add as CNAME records
s1._domainkey.{domain}   CNAME   s1.domainkey.sendgrid.net
s2._domainkey.{domain}   CNAME   s2.domainkey.sendgrid.net

# SPF — Add to existing SPF or create new
{domain}   TXT   "v=spf1 include:sendgrid.net ~all"
```

DentalOS stores domain verification status in `public.tenant_email_config`:

```sql
CREATE TABLE public.tenant_email_config (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES public.tenants(id),
    custom_domain       VARCHAR(255),          -- e.g., dentovita.co
    from_email          VARCHAR(254) NOT NULL, -- noreply@domain or fallback
    from_name           VARCHAR(100) NOT NULL,
    reply_to_email      VARCHAR(254),
    sendgrid_domain_id  VARCHAR(50),           -- SendGrid domain authentication ID
    spf_verified        BOOLEAN DEFAULT FALSE,
    dkim_verified       BOOLEAN DEFAULT FALSE,
    domain_verified_at  TIMESTAMPTZ,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT now()
);
```

When no custom domain is verified, sender falls back to `noreply@dentalos.app`.

---

## 4. Email Service Implementation

### SendGrid Service

```python
import sendgrid
from sendgrid.helpers.mail import Mail, To, From, ReplyTo, Content
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class SendGridEmailService:
    def __init__(self, api_key: str):
        self.sg = sendgrid.SendGridAPIClient(api_key=api_key)

    async def send(
        self,
        to_email: str,
        to_name: str,
        from_email: str,
        from_name: str,
        subject: str,
        html_body: str,
        text_body: str,
        reply_to: Optional[str] = None,
        categories: Optional[List[str]] = None,
    ) -> str:
        """Send email via SendGrid. Returns message ID."""
        message = Mail(
            from_email=From(from_email, from_name),
            to_emails=To(to_email, to_name),
            subject=subject,
            html_content=html_body,
            plain_text_content=text_body,
        )
        if reply_to:
            message.reply_to = ReplyTo(reply_to)
        if categories:
            for cat in categories:
                message.add_category(cat)

        response = self.sg.send(message)

        if response.status_code not in (200, 201, 202):
            raise EmailDeliveryError(
                f"SendGrid error {response.status_code}: {response.body}"
            )

        # Extract X-Message-Id header
        message_id = response.headers.get("X-Message-Id", "")
        logger.info(
            "Email sent via SendGrid",
            extra={"message_id": message_id, "status": response.status_code}
        )
        return message_id
```

### Amazon SES Fallback Service

```python
import boto3
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


class SESEmailService:
    def __init__(self, region: str = "us-east-1"):
        self.client = boto3.client("ses", region_name=region)

    async def send(
        self,
        to_email: str,
        from_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> str:
        """Send email via Amazon SES. Returns message ID."""
        try:
            response = self.client.send_email(
                Source=from_email,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_body, "Charset": "UTF-8"},
                        "Text": {"Data": text_body, "Charset": "UTF-8"},
                    },
                },
            )
            message_id = response["MessageId"]
            logger.info(
                "Email sent via SES (fallback)",
                extra={"message_id": message_id}
            )
            return message_id
        except ClientError as exc:
            logger.error("SES error", extra={"error": str(exc)})
            raise
```

---

## 5. Queue-Based Delivery (RabbitMQ)

### Queue Configuration

| Queue | Exchange | Routing Key | Priority |
|-------|----------|-------------|---------|
| `email.outbound` | `notifications` | `email.send` | Normal |
| `email.outbound.priority` | `notifications` | `email.priority` | High (OTP, password reset) |
| `email.outbound.dlq` | `notifications.dlq` | `email.dead` | DLQ |

### Job Payload Schema

```python
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime
import uuid


class EmailJob(BaseModel):
    job_id: str = str(uuid.uuid4())
    tenant_id: str
    message_log_id: Optional[str] = None
    # Recipient
    to_email: str
    to_name: str
    # Sender (resolved by worker from tenant config)
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    reply_to: Optional[str] = None
    # Content
    template_name: str           # e.g., "appointments/reminder_24h"
    subject: str
    context: Dict[str, str]      # Placeholder values
    # Metadata
    category: Optional[str] = None   # e.g., "appointment_reminder"
    priority: str = "normal"         # "normal" | "high"
    attempt: int = 0
    max_attempts: int = 3
    created_at: datetime = datetime.utcnow()
```

### Worker Implementation

```python
class EmailWorker:
    def __init__(self, redis, template_cache):
        self.template_cache = template_cache
        self.parser = TemplatePlaceholderParser()
        self.router = EmailProviderRouter(redis)
        self.sendgrid = SendGridEmailService(settings.SENDGRID_API_KEY)
        self.ses = SESEmailService()

    async def process_job(self, job: EmailJob) -> None:
        # 1. Load template from cache
        template_html = await self.template_cache.get(job.template_name)
        if not template_html:
            raise TemplateNotFoundError(f"Template not found: {job.template_name}")

        # 2. Resolve tenant sender config
        async with get_tenant_session(job.tenant_id) as session:
            email_config = await get_tenant_email_config(session, job.tenant_id)

        from_email = job.from_email or email_config.from_email
        from_name = job.from_name or email_config.from_name

        # 3. Enrich context with standard fields
        job.context.update({
            "clinic_name": email_config.from_name,
            "current_year": str(datetime.utcnow().year),
            "unsubscribe_url": self._build_unsubscribe_url(job),
        })

        # 4. Render template
        html_body = self.parser.render(template_html, job.context)
        text_body = self._strip_html(html_body)

        # 5. Select provider
        provider = await self.router.get_provider()

        # 6. Send
        try:
            if provider == EmailProvider.SENDGRID:
                message_id = await self.sendgrid.send(
                    to_email=job.to_email,
                    to_name=job.to_name,
                    from_email=from_email,
                    from_name=from_name,
                    subject=job.subject,
                    html_body=html_body,
                    text_body=text_body,
                    reply_to=job.reply_to,
                    categories=[job.category] if job.category else None,
                )
                await self.router.report_success()
            else:
                message_id = await self.ses.send(
                    to_email=job.to_email,
                    from_email=from_email,
                    subject=job.subject,
                    html_body=html_body,
                    text_body=text_body,
                )

            await self._update_log(job, "sent", message_id)

        except Exception as exc:
            await self.router.report_failure()
            await self._update_log(job, "failed")
            raise
```

---

## 6. Delivery Tracking

### SendGrid Event Webhook

SendGrid posts delivery events to:
```
POST /api/v1/webhooks/sendgrid/events
```

**Events tracked:**

| Event | Status | Action |
|-------|--------|--------|
| `delivered` | delivered | Update message_log |
| `open` | opened | Update message_log |
| `click` | clicked | Update message_log |
| `bounce` | bounced | Update log + trigger bounce handler |
| `dropped` | dropped | Update log (SendGrid dropped before attempt) |
| `spamreport` | spam | Update log + unsubscribe patient email |
| `unsubscribe` | unsubscribed | Unsubscribe patient email |
| `deferred` | deferred | Retry by SendGrid automatically |

### Webhook Handler

```python
@router.post("/webhooks/sendgrid/events")
async def sendgrid_events(request: Request):
    """Handle SendGrid event webhook (batch of events)."""
    # Verify SendGrid webhook signature
    signature = request.headers.get("X-Twilio-Email-Event-Webhook-Signature")
    timestamp = request.headers.get("X-Twilio-Email-Event-Webhook-Timestamp")
    body = await request.body()
    verify_sendgrid_signature(body, signature, timestamp, settings.SENDGRID_WEBHOOK_KEY)

    events = await request.json()
    for event in events:
        await handle_email_event(event)
    return {"status": "ok"}
```

---

## 7. Bounce Handling

### Bounce Types

| Type | Meaning | Action |
|------|---------|--------|
| Hard bounce | Invalid address | Permanently disable email for patient |
| Soft bounce | Mailbox full / temporary | Retry up to 72h, then disable |
| Spam complaint | Recipient marked as spam | Immediately suppress |

### Auto-Disable Invalid Emails

```python
async def handle_hard_bounce(
    session,
    tenant_id: str,
    email: str,
) -> None:
    """
    On hard bounce: mark patient email as invalid in tenant DB.
    Future emails to this address are blocked.
    """
    await session.execute(
        update(Patient)
        .where(Patient.email == email)
        .values(
            email_valid=False,
            email_bounced_at=datetime.utcnow(),
        )
    )
    await session.commit()
    logger.warning(
        "Patient email hard-bounced, disabled",
        extra={"tenant_id": tenant_id}
        # Do NOT log the email address itself
    )
```

---

## 8. Email Log Table (Tenant Schema)

Email messages share the `message_logs` table, filtered by `channel = 'email'`.

Additional email-specific fields:

```sql
-- Additional columns on message_logs for email:
ALTER TABLE message_logs ADD COLUMN IF NOT EXISTS
    email_subject VARCHAR(998),         -- RFC 5322 max
    sendgrid_message_id VARCHAR(100),
    ses_message_id VARCHAR(100),
    email_opened_at TIMESTAMPTZ,
    email_clicked_at TIMESTAMPTZ,
    bounce_type VARCHAR(20),            -- hard | soft | NULL
    bounce_reason VARCHAR(500);
```

---

## 9. Unsubscribe Management

All non-transactional marketing emails include an unsubscribe link. Transactional emails (appointment reminders, invoices, OTPs) are exempt from unsubscribe (required communication).

**Unsubscribe categories:**

| Category | Can Unsubscribe | Notes |
|----------|----------------|-------|
| Marketing | Yes | Promotional content |
| Appointment reminders | No | Required for clinical continuity |
| Invoices | No | Required for billing |
| OTP / security | No | Required for account security |
| Treatment plan updates | Yes | Optional clinical communications |

**Unsubscribe storage (tenant schema):**

```sql
CREATE TABLE email_suppressions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(254) NOT NULL,
    category    VARCHAR(50) NOT NULL DEFAULT 'all',
    reason      VARCHAR(30),             -- unsubscribe | spam | bounce
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(email, category)
);
```

---

## 10. Security Considerations

- No patient PHI (diagnoses, procedures) in email body — scheduling and administrative data only
- Email addresses are encrypted in `patients` table (PHI direct identifier)
- Worker resolves plain email only at send time; never logs the address
- SendGrid API key stored in environment variable `SENDGRID_API_KEY`
- Webhook signatures verified on all inbound webhooks
- Unsubscribe tokens are HMAC-signed (cannot be forged to unsubscribe other users)
- `Reply-To` set to clinic email — replies go to clinic, not DentalOS

---

## 11. Configuration Reference

### Environment Variables

| Variable | Description |
|----------|-------------|
| `SENDGRID_API_KEY` | SendGrid API key |
| `SENDGRID_WEBHOOK_KEY` | Webhook signing key |
| `AWS_ACCESS_KEY_ID` | AWS credentials for SES |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials for SES |
| `AWS_SES_REGION` | SES region (e.g., `us-east-1`) |
| `EMAIL_DEFAULT_FROM` | Fallback from address |
| `EMAIL_DEFAULT_FROM_NAME` | Fallback from name |

---

## Out of Scope

- Newsletter or mass marketing campaigns
- MJML real-time editing by tenants (templates are managed by DentalOS team)
- Email scheduling beyond queue-based delayed delivery
- Email thread management / inbound email parsing
- Attachments other than generated PDFs (invoice, consent, treatment plan)

---

## Acceptance Criteria

**This integration is complete when:**

- [ ] Appointment reminder emails render correctly with tenant branding
- [ ] SendGrid → SES fallback triggers on circuit breaker open
- [ ] Bounce events auto-disable patient email in tenant DB
- [ ] Placeholder rendering raises error on missing variable
- [ ] Delivery events (delivered/bounced/opened) tracked in message_logs
- [ ] Unsubscribe suppression prevents future marketing emails
- [ ] Custom domain sender verified (SPF/DKIM) for at least one tenant
- [ ] Webhook signatures verified for SendGrid events

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
