# Payment Gateway Integration Spec

> **Spec ID:** INT-07
> **Status:** Draft
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Online payment collection for the patient portal via Mercado Pago (primary LATAM gateway) and PSE (Colombia bank transfers). Supports card payments, PSE transfers, and refunds. Webhook-based payment confirmation automatically updates invoice status. PCI DSS compliance via tokenization — no card data stored by DentalOS.

**Domain:** integrations / billing

**Priority:** High

**Dependencies:** billing domain, patient portal (portal domain), I-11 (audit-logging), INT-10 (DIAN invoicing — payment triggers invoice status update)

---

## 1. Provider Strategy

### Primary: Mercado Pago

- **Coverage:** Colombia, Mexico, Chile, Argentina, Peru, Uruguay, Brazil
- **Products used:** Checkout Pro, Payment API (for embedded checkout), Subscriptions
- **Authentication:** Access Token per integration + Public Key per tenant (Marketplace mode)
- **Marketplace mode:** DentalOS as Marketplace, each clinic as Seller (OAuth flow)
- **Fee split:** Mercado Pago takes ~3.49% + $900 COP per transaction; DentalOS takes 0% (clinic pays full MP fee)

### Colombia-Specific: PSE (Pagos Seguros en Línea)

- **Coverage:** Colombia bank transfers only
- **Provider:** ACH Colombia via Mercado Pago (MP supports PSE natively)
- **Use case:** Patients who prefer bank transfer over card
- **Settlement:** T+1 business day

### Payment Methods Matrix

| Method | Colombia | Mexico | Chile |
|--------|---------|--------|-------|
| Credit/debit card (Visa, MC, Amex) | Yes (MP) | Yes (MP) | Yes (MP) |
| PSE (bank transfer) | Yes (MP+PSE) | No | No |
| Efecty / cash | Colombia (MP) | No | No |
| OXXO | No | Yes (MP) | No |
| WebPay / Redcompra | No | No | Yes (MP) |

---

## 2. Architecture

### Payment Flow

```
Patient opens portal → sees invoice
    │
    ▼
Patient clicks "Pagar"
    │
    ▼
Portal → POST /api/v1/portal/payments/create-preference
    │
    ▼
DentalOS creates MP Preference (checkout session)
    │
    ▼
Returns preference_id + init_point (MP hosted checkout URL)
    │
    ▼
Portal redirects to Mercado Pago hosted checkout
    │
    ▼
Patient pays (card / PSE / cash)
    │
    ▼
MP sends webhook → POST /api/v1/webhooks/mercadopago/payment
    │
    ▼
DentalOS verifies webhook, updates invoice status
    │
    ▼
DIAN electronic invoice triggered (if Colombia)
    │
    ▼
Email/WhatsApp payment confirmation sent to patient
```

### Marketplace Mode (OAuth per Tenant)

```
Clinic admin → connects MP account
    │
    ▼
DentalOS initiates OAuth flow (MP Marketplace OAuth)
    │
    ▼
Clinic authorizes on MP
    │
    ▼
DentalOS receives access_token + refresh_token per tenant
    │
    ▼
Payments processed on clinic's MP account
    │
    ▼
Fees deducted by MP, net amount to clinic's MP wallet
```

### Per-Tenant Configuration

```sql
CREATE TABLE public.tenant_payment_config (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES public.tenants(id),
    provider                VARCHAR(30) DEFAULT 'mercadopago',
    mp_access_token         TEXT NOT NULL,              -- Encrypted seller access token
    mp_refresh_token        TEXT,                       -- Encrypted for refresh
    mp_public_key           VARCHAR(100) NOT NULL,      -- Public key for frontend SDK
    mp_user_id              VARCHAR(50),                -- MP user/seller ID
    mp_token_expires_at     TIMESTAMPTZ,
    pse_enabled             BOOLEAN DEFAULT FALSE,      -- Colombia only
    is_active               BOOLEAN DEFAULT TRUE,
    connected_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT now()
);
```

---

## 3. Payment API — Endpoints

### 3.1 Create Payment Preference

```
POST /api/v1/portal/payments/create-preference
```

**Auth:** Patient JWT (portal session)

**Request:**

```json
{
  "invoice_id": "uuid",
  "back_urls": {
    "success": "https://portal.dentalos.app/payment/success",
    "failure": "https://portal.dentalos.app/payment/failure",
    "pending": "https://portal.dentalos.app/payment/pending"
  }
}
```

**Response:**

```json
{
  "preference_id": "mp_pref_xxxxxxxx",
  "init_point": "https://www.mercadopago.com.co/checkout/v1/redirect?pref_id=...",
  "sandbox_init_point": "https://sandbox.mercadopago.com.co/checkout/v1/redirect?...",
  "invoice_id": "uuid",
  "amount": 150000,
  "currency": "COP"
}
```

**Business Logic:**

```python
from app.integrations.payment.mercadopago import MercadoPagoService
from decimal import Decimal


async def create_payment_preference(
    invoice_id: str,
    patient_id: str,
    tenant_id: str,
    back_urls: dict,
) -> dict:
    """
    Create a Mercado Pago checkout preference for an invoice.
    """
    async with get_tenant_session(tenant_id) as session:
        # 1. Load invoice
        invoice = await get_invoice(session, invoice_id)
        if invoice.patient_id != patient_id:
            raise Forbidden("No tienes permiso para pagar esta factura")
        if invoice.status in ("paid", "void"):
            raise InvalidOperation("Esta factura ya fue pagada o anulada")

        # 2. Load tenant MP config
        payment_config = await get_tenant_payment_config(session, tenant_id)
        if not payment_config or not payment_config.is_active:
            raise ServiceUnavailable("Pagos en línea no disponibles para esta clínica")

        # 3. Create preference via MP API
        service = MercadoPagoService(
            access_token=payment_config.mp_access_token
        )
        preference = await service.create_preference(
            invoice_id=invoice_id,
            amount=invoice.total_amount,
            currency=invoice.currency,
            description=f"Factura #{invoice.invoice_number} - {invoice.tenant_name}",
            patient_email=invoice.patient_email,
            back_urls=back_urls,
            notification_url=f"{settings.API_BASE_URL}/api/v1/webhooks/mercadopago/payment",
            external_reference=f"{tenant_id}:{invoice_id}",
        )

        # 4. Store pending payment record
        await create_payment_record(session, {
            "invoice_id": invoice_id,
            "preference_id": preference["id"],
            "status": "pending",
            "amount": invoice.total_amount,
            "currency": invoice.currency,
        })

        return preference
```

### 3.2 Get Payment Status

```
GET /api/v1/portal/payments/{payment_id}/status
```

**Auth:** Patient JWT

**Response:**

```json
{
  "payment_id": "uuid",
  "invoice_id": "uuid",
  "status": "approved",
  "amount": 150000,
  "currency": "COP",
  "payment_method": "credit_card",
  "paid_at": "2026-04-15T10:35:00Z"
}
```

---

## 4. Mercado Pago Service

```python
import mercadopago
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MercadoPagoService:
    def __init__(self, access_token: str):
        self.sdk = mercadopago.SDK(access_token)

    async def create_preference(
        self,
        invoice_id: str,
        amount: Decimal,
        currency: str,
        description: str,
        patient_email: str,
        back_urls: dict,
        notification_url: str,
        external_reference: str,
        payment_methods: Optional[dict] = None,
    ) -> dict:
        """Create a Checkout Pro preference."""
        preference_data = {
            "items": [
                {
                    "id": invoice_id,
                    "title": description,
                    "quantity": 1,
                    "unit_price": float(amount),
                    "currency_id": currency,
                }
            ],
            "payer": {"email": patient_email},
            "back_urls": back_urls,
            "auto_return": "approved",
            "notification_url": notification_url,
            "external_reference": external_reference,
            "statement_descriptor": "DentalOS",
            "expires": True,
            "expiration_date_from": datetime.utcnow().isoformat(),
            "expiration_date_to": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }

        if payment_methods:
            preference_data["payment_methods"] = payment_methods

        response = self.sdk.preference().create(preference_data)
        result = response["response"]

        if response["status"] not in (200, 201):
            raise PaymentGatewayError(
                f"MP preference creation failed: {result.get('message', 'Unknown error')}"
            )

        return {
            "id": result["id"],
            "init_point": result["init_point"],
            "sandbox_init_point": result["sandbox_init_point"],
        }

    async def get_payment(self, payment_id: str) -> dict:
        """Get payment details by MP payment ID."""
        response = self.sdk.payment().get(payment_id)
        return response["response"]

    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
    ) -> dict:
        """
        Refund a payment (full or partial).
        amount=None for full refund.
        """
        if amount:
            refund_data = {"amount": float(amount)}
        else:
            refund_data = {}

        response = self.sdk.refund().create(payment_id, refund_data)
        result = response["response"]

        if response["status"] not in (200, 201):
            raise PaymentGatewayError(
                f"MP refund failed: {result.get('message', 'Unknown error')}"
            )

        return {
            "refund_id": result.get("id"),
            "status": result.get("status"),
            "amount": result.get("amount"),
        }
```

---

## 5. Webhook Processing

### Endpoint

```
POST /api/v1/webhooks/mercadopago/payment
```

Public endpoint. Verified via x-signature header.

### Webhook Signature Verification

```python
import hmac
import hashlib
from fastapi import Request, HTTPException
from app.core.config import settings


async def verify_mp_signature(request: Request, body: bytes) -> None:
    """
    Verify Mercado Pago webhook signature.
    See: https://www.mercadopago.com.co/developers/en/docs/notifications/webhooks/security
    """
    x_signature = request.headers.get("x-signature", "")
    x_request_id = request.headers.get("x-request-id", "")
    query_data_id = request.query_params.get("data.id", "")

    # Build manifest
    ts = ""
    v1 = ""
    for part in x_signature.split(","):
        k, v = part.split("=", 1)
        if k.strip() == "ts":
            ts = v.strip()
        elif k.strip() == "v1":
            v1 = v.strip()

    manifest = f"id:{query_data_id};request-id:{x_request_id};ts:{ts};"
    secret = settings.MERCADOPAGO_WEBHOOK_SECRET
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, v1):
        raise HTTPException(status_code=403, detail="Invalid MP webhook signature")
```

### Payment Status Handler

```python
from fastapi import APIRouter, Request, Query
from typing import Optional

router = APIRouter()

@router.post("/webhooks/mercadopago/payment")
async def mercadopago_webhook(
    request: Request,
    topic: Optional[str] = Query(None),
    id: Optional[str] = Query(alias="data.id", default=None),
):
    body = await request.body()
    await verify_mp_signature(request, body)

    if topic != "payment":
        return {"status": "ignored"}

    # Fetch full payment details from MP (webhook payload is minimal)
    payment_details = await fetch_mp_payment(id)

    external_ref = payment_details.get("external_reference", "")
    if ":" not in external_ref:
        return {"status": "invalid_reference"}

    tenant_id, invoice_id = external_ref.split(":", 1)

    status = payment_details.get("status")
    status_detail = payment_details.get("status_detail")

    await handle_payment_status(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        mp_payment_id=str(id),
        status=status,
        status_detail=status_detail,
        payment_data=payment_details,
    )
    return {"status": "ok"}
```

### Payment Status Mapping

| MP Status | MP Status Detail | DentalOS Action |
|----------|-----------------|----------------|
| `approved` | `accredited` | Mark invoice PAID, trigger DIAN invoice, send confirmation |
| `pending` | `pending_waiting_payment` | Mark invoice PENDING, send reminder |
| `pending` | `pending_review_manual` | Mark as manual review, alert staff |
| `rejected` | `cc_rejected_insufficient_amount` | Keep invoice UNPAID, notify patient |
| `rejected` | `cc_rejected_bad_filled_card_number` | Keep invoice UNPAID |
| `in_process` | `pending_contingency` | Temporary state, wait for resolution |
| `refunded` | — | Mark invoice REFUNDED |
| `cancelled` | `expired` | Mark preference expired |

---

## 6. Refund Flow

```python
async def process_refund(
    invoice_id: str,
    tenant_id: str,
    amount: Optional[Decimal],
    reason: str,
) -> dict:
    """
    Process a refund for a paid invoice.
    Optionally partial refund (amount specified) or full refund.
    """
    async with get_tenant_session(tenant_id) as session:
        invoice = await get_invoice(session, invoice_id)
        if invoice.status != "paid":
            raise InvalidOperation("Solo se pueden reembolsar facturas pagadas")

        payment = await get_payment_by_invoice(session, invoice_id)
        config = await get_tenant_payment_config(session, tenant_id)

        service = MercadoPagoService(config.mp_access_token)

        # Execute refund on MP
        refund = await service.refund_payment(
            payment_id=payment.mp_payment_id,
            amount=amount,
        )

        # Update payment record
        payment.status = "refunded"
        payment.refund_id = refund["refund_id"]
        payment.refunded_amount = amount or invoice.total_amount
        payment.refunded_at = datetime.utcnow()
        payment.refund_reason = reason

        # Update invoice status
        if amount and amount < invoice.total_amount:
            invoice.status = "partially_refunded"
        else:
            invoice.status = "refunded"

        await session.commit()

        # Audit log
        await audit_log(session, "refund", "payment", invoice_id, phi=False)

        # Send confirmation to patient
        await enqueue_payment_refund_notification(tenant_id, invoice_id, amount)

        return {"status": "refunded", "amount": float(amount or invoice.total_amount)}
```

---

## 7. PSE Integration (Colombia)

PSE is available through Mercado Pago by specifying the payment method in the preference:

```python
def build_pse_preference(invoice_data: dict) -> dict:
    """Build Mercado Pago preference with PSE as the only payment method."""
    return {
        "payment_methods": {
            "excluded_payment_methods": [
                {"id": "visa"},
                {"id": "master"},
                {"id": "amex"},
                {"id": "efecty"},
            ],
            "excluded_payment_types": [
                {"id": "credit_card"},
                {"id": "debit_card"},
                {"id": "ticket"},
            ],
        }
    }
```

PSE payments require the patient to select their bank from a list. Settlement is T+1 business day. DentalOS shows invoice as "pending" until MP confirms transfer.

---

## 8. Payment Record Table (Tenant Schema)

```sql
CREATE TABLE payments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id          UUID NOT NULL,
    patient_id          UUID NOT NULL,
    amount              NUMERIC(12, 2) NOT NULL,
    currency            VARCHAR(3) NOT NULL DEFAULT 'COP',
    provider            VARCHAR(30) NOT NULL DEFAULT 'mercadopago',
    mp_preference_id    VARCHAR(100),
    mp_payment_id       VARCHAR(50),
    mp_order_id         VARCHAR(50),
    payment_method      VARCHAR(50),            -- credit_card | debit_card | pse | efecty
    payment_method_type VARCHAR(30),
    status              VARCHAR(30) NOT NULL DEFAULT 'pending',
    -- pending | approved | rejected | in_process | refunded | cancelled
    status_detail       VARCHAR(100),
    installments        INTEGER DEFAULT 1,
    refund_id           VARCHAR(50),
    refunded_amount     NUMERIC(12, 2),
    refunded_at         TIMESTAMPTZ,
    refund_reason       VARCHAR(255),
    paid_at             TIMESTAMPTZ,
    failed_at           TIMESTAMPTZ,
    failure_reason      VARCHAR(255),
    raw_mp_response     JSONB,                  -- Full MP payment object
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_payments_invoice_id ON payments(invoice_id);
CREATE INDEX idx_payments_mp_payment_id ON payments(mp_payment_id);
CREATE INDEX idx_payments_status ON payments(status);
```

---

## 9. PCI DSS Compliance

DentalOS does not handle card data directly. PCI DSS compliance is maintained by:

- **Tokenization:** Card data entered in Mercado Pago hosted checkout, never reaches DentalOS servers
- **No card storage:** DentalOS stores only `mp_payment_id` and masked card info (last 4 digits from MP webhook)
- **TLS enforcement:** All payment-related pages use TLS 1.3
- **iFrame / redirect:** Patient is redirected to `mercadopago.com` for checkout — no card form on DentalOS domain
- **MP JavaScript SDK:** When embedded checkout used, card tokenization happens client-side via MP JS

---

## 10. Rate Limiting and Security

```python
# Rate limit payment creation: 10 per hour per patient
PAYMENT_CREATION_LIMIT = 10
PAYMENT_CREATION_WINDOW = 3600

async def check_payment_creation_limit(redis, patient_id: str) -> None:
    key = f"payment:create:rate:{patient_id}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, PAYMENT_CREATION_WINDOW)
    if count > PAYMENT_CREATION_LIMIT:
        raise RateLimitExceeded(
            "Demasiados intentos de pago. Espera antes de intentar de nuevo."
        )
```

---

## 11. OAuth Flow for Clinic MP Account Connection

```python
@router.get("/api/v1/settings/payment/mercadopago/connect")
async def mp_oauth_connect(tenant_id: str = Depends(get_tenant)):
    """Redirect clinic admin to MP OAuth authorization page."""
    oauth_url = (
        f"https://auth.mercadopago.com.co/authorization"
        f"?client_id={settings.MP_CLIENT_ID}"
        f"&response_type=code"
        f"&platform_id=mp"
        f"&state={tenant_id}"
        f"&redirect_uri={settings.MP_REDIRECT_URI}"
    )
    return RedirectResponse(oauth_url)

@router.get("/api/v1/settings/payment/mercadopago/callback")
async def mp_oauth_callback(code: str, state: str):
    """Handle MP OAuth callback, exchange code for access token."""
    tenant_id = state
    tokens = await exchange_mp_code_for_tokens(code)
    await save_tenant_payment_config(tenant_id, tokens)
    return RedirectResponse("/settings/payment?connected=true")
```

---

## 12. Configuration Reference

### Environment Variables

| Variable | Description |
|----------|-------------|
| `MERCADOPAGO_CLIENT_ID` | MP Marketplace Client ID |
| `MERCADOPAGO_CLIENT_SECRET` | MP Marketplace Client Secret |
| `MERCADOPAGO_WEBHOOK_SECRET` | MP webhook signing secret |
| `MERCADOPAGO_REDIRECT_URI` | OAuth callback URL |
| `PAYMENT_SUCCESS_URL` | Portal success redirect |
| `PAYMENT_FAILURE_URL` | Portal failure redirect |

---

## Out of Scope

- Subscriptions / recurring billing via MP
- In-person card reader (POS) integration
- Insurance/HMO payment processing
- Stripe integration (possible future for US market)
- PayU (secondary Colombian gateway) — may add if MP has issues

---

## Acceptance Criteria

**This integration is complete when:**

- [ ] Checkout preference creates successfully for a real invoice
- [ ] MP webhook updates invoice to `paid` on `approved` payment
- [ ] PSE payment method available for Colombian tenants
- [ ] Full refund processes and updates invoice to `refunded`
- [ ] Webhook signature verification rejects tampered requests
- [ ] Rate limiting prevents payment creation abuse (10/hour/patient)
- [ ] No card data touches DentalOS servers
- [ ] Clinic connects MP account via OAuth successfully
- [ ] Payment confirmation email/WhatsApp sent on payment

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
