# MATIAS API — DIAN Electronic Invoicing Spec

> **Spec ID:** INT-10
> **Status:** Draft
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Integration with the MATIAS API for Colombian DIAN electronic invoicing using the "Casa de Software" model. MATIAS abstracts all DIAN complexity (XML generation, digital signatures, CUFE computation, DIAN web service calls, test mode management). DentalOS acts as a technology provider; each dental clinic invoices under their own NIT. Setup requires NIT registration, resolution number, and certificate upload per tenant. ~$400,000 COP/year for multi-client package.

**Domain:** integrations / compliance / billing

**Priority:** Critical — required for Colombia Resolución 1888 compliance by April 2026

**Dependencies:** billing domain specs, I-13 (compliance engine — ColombiaAdapter), ADR-007 (country adapter), INT-04 (direct DIAN — reference spec)

---

## 1. What is MATIAS?

MATIAS (Módulo de Atención Tributaria e Integración de Aplicaciones al Sistema) is a Colombian authorized software provider (Proveedor de Soluciones Tecnológicas — PST) for DIAN electronic invoicing.

Under the "Casa de Software" model:
- **DentalOS** is the software provider (Casa de Software)
- **Each dental clinic** is an "Obligado a Facturar" under their own NIT
- **MATIAS** handles all DIAN integration (sign, submit, validate, respond)
- **DentalOS** sends invoice data via MATIAS REST API

Benefits over direct DIAN integration (INT-04):
- No XML generation or XAdES signature management
- No DIAN SOAP client
- MATIAS handles certificate management per tenant
- Simpler REST API with JSON
- Better error messages
- Habilitación (test mode) managed by MATIAS
- SLA with MATIAS for DIAN-related issues

**Cost:** ~$400,000 COP/year for the multi-client plan (covers unlimited clinics under DentalOS Casa de Software account).

---

## 2. Architecture

```
DentalOS Billing Service
    │
    │  Creates invoice in tenant schema
    ▼
DIAN Invoice Job (RabbitMQ: dian.outbound)
    │
    ▼
MATIAS Worker (consumer)
    │
    ▼
MATIAS REST API
    │  POST /api/v2/invoices/{nit}/emit
    ▼
MATIAS → DIAN (internal, opaque to DentalOS)
    │
    ▼
MATIAS returns: CUFE + XML + PDF + status
    │
    ▼
Update tenant schema: electronic_invoice_logs
    │
    ▼
Trigger: send invoice PDF to patient (email/WhatsApp)
```

---

## 3. Per-Tenant Setup

### Setup Steps (Onboarding a Colombia Clinic for DIAN)

1. **DentalOS registers clinic NIT** via MATIAS API: `POST /api/v2/clients/{nit}/register`
2. **Clinic uploads** DIAN resolution data (resolution number, date, prefix, range) via DentalOS settings
3. **Clinic uploads** X.509 certificate (PKCS#12) via DentalOS settings — stored encrypted, forwarded to MATIAS
4. **Habilitación (test mode):** DentalOS submits standard test set (57 test invoices) via MATIAS
5. **MATIAS completes habilitación** with DIAN
6. **Production activated:** Clinic's DIAN config environment set to `produccion`

### Tenant DIAN Config Table

```sql
CREATE TABLE public.tenant_dian_matias_config (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES public.tenants(id),
    nit                     VARCHAR(15) NOT NULL,          -- Without check digit
    nit_check_digit         VARCHAR(1) NOT NULL,
    razon_social            VARCHAR(255) NOT NULL,
    address                 VARCHAR(200),
    city                    VARCHAR(100),
    department              VARCHAR(100),
    tax_regime              VARCHAR(30) DEFAULT 'REGIMEN_COMUN',
    -- REGIMEN_COMUN | GRAN_CONTRIBUYENTE | AUTORETENEDOR
    resolution_number       VARCHAR(50) NOT NULL,
    resolution_date         DATE NOT NULL,
    resolution_prefix       VARCHAR(10),                   -- e.g., "FV", "FE"
    resolution_range_from   INTEGER NOT NULL,
    resolution_range_to     INTEGER NOT NULL,
    current_invoice_number  INTEGER DEFAULT 0,
    matias_client_id        VARCHAR(100),                  -- MATIAS internal client ID
    certificate_p12         BYTEA NOT NULL,                -- X.509 cert encrypted
    certificate_password    TEXT NOT NULL,                 -- Encrypted
    certificate_valid_until DATE NOT NULL,
    environment             VARCHAR(20) DEFAULT 'habilitacion',
    -- habilitacion | produccion
    habilitacion_completed  BOOLEAN DEFAULT FALSE,
    habilitacion_completed_at TIMESTAMPTZ,
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMPTZ DEFAULT now()
);
```

---

## 4. MATIAS API Client

### Authentication

MATIAS uses HTTP Basic Auth with the DentalOS Casa de Software credentials (single set of credentials for all tenants).

```python
from app.core.config import settings

MATIAS_AUTH = (settings.MATIAS_CLIENT_ID, settings.MATIAS_API_KEY)
MATIAS_BASE_URL_HAB = "https://hab.api.matias.com.co/v2"  # Habilitación
MATIAS_BASE_URL_PROD = "https://api.matias.com.co/v2"       # Producción
```

### Invoice Emission

```python
import httpx
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MATIASService:
    def __init__(self, environment: str = "habilitacion"):
        self.base_url = (
            MATIAS_BASE_URL_PROD
            if environment == "produccion"
            else MATIAS_BASE_URL_HAB
        )

    async def emit_invoice(
        self,
        nit: str,
        invoice_payload: dict,
    ) -> dict:
        """
        Submit an invoice to DIAN via MATIAS.

        invoice_payload must contain the structured invoice data.
        MATIAS handles XML generation, signing, and DIAN submission.
        Returns CUFE, signed XML URL, and PDF URL.
        """
        endpoint = f"{self.base_url}/clients/{nit}/invoices"

        async with httpx.AsyncClient(timeout=60, auth=MATIAS_AUTH) as client:
            response = await client.post(endpoint, json=invoice_payload)

        if response.status_code == 201:
            data = response.json()
            logger.info(
                "MATIAS invoice emitted",
                extra={
                    "nit": nit,
                    "cufe": data.get("cufe"),
                    "invoice_number": invoice_payload.get("invoiceNumber"),
                }
            )
            return {
                "cufe": data["cufe"],
                "invoice_number": data["invoiceNumber"],
                "xml_url": data.get("xmlUrl"),
                "pdf_url": data.get("pdfUrl"),
                "dian_status": data.get("dianStatus"),
                "issued_at": data.get("issuedAt"),
                "matias_id": data.get("id"),
            }
        else:
            error = response.json()
            raise MATIASError(
                f"MATIAS error {response.status_code}: "
                f"{error.get('message', error.get('error', 'Unknown error'))}"
            )

    async def check_invoice_status(
        self,
        nit: str,
        matias_id: str,
    ) -> dict:
        """Poll DIAN status for a submitted invoice via MATIAS."""
        async with httpx.AsyncClient(timeout=30, auth=MATIAS_AUTH) as client:
            response = await client.get(
                f"{self.base_url}/clients/{nit}/invoices/{matias_id}"
            )
        data = response.json()
        return {
            "dian_status": data.get("dianStatus"),
            "cufe": data.get("cufe"),
            "is_accepted": data.get("isAccepted", False),
            "rejection_reason": data.get("rejectionReason"),
        }

    async def emit_credit_note(
        self,
        nit: str,
        credit_note_payload: dict,
    ) -> dict:
        """Submit a credit note (Nota Crédito, document type 91)."""
        endpoint = f"{self.base_url}/clients/{nit}/credit-notes"

        async with httpx.AsyncClient(timeout=60, auth=MATIAS_AUTH) as client:
            response = await client.post(endpoint, json=credit_note_payload)

        if response.status_code == 201:
            data = response.json()
            return {
                "cufe": data["cufe"],
                "credit_note_number": data["creditNoteNumber"],
                "xml_url": data.get("xmlUrl"),
                "pdf_url": data.get("pdfUrl"),
                "dian_status": data.get("dianStatus"),
            }
        else:
            error = response.json()
            raise MATIASError(f"MATIAS credit note error: {error.get('message')}")

    async def register_client(
        self,
        nit: str,
        nit_check_digit: str,
        razon_social: str,
        address: str,
        city: str,
        department: str,
        tax_regime: str,
        certificate_p12_base64: str,
        certificate_password: str,
        resolution_number: str,
        resolution_date: str,
        resolution_prefix: Optional[str],
        range_from: int,
        range_to: int,
    ) -> dict:
        """
        Register a new clinic (NIT) under the DentalOS Casa de Software account.
        Must be called once per tenant during onboarding.
        """
        payload = {
            "nit": nit,
            "nitCheckDigit": nit_check_digit,
            "razonSocial": razon_social,
            "address": address,
            "city": city,
            "department": department,
            "taxRegime": tax_regime,
            "certificate": certificate_p12_base64,
            "certificatePassword": certificate_password,
            "resolution": {
                "number": resolution_number,
                "date": resolution_date,
                "prefix": resolution_prefix or "",
                "rangeFrom": range_from,
                "rangeTo": range_to,
            },
        }

        async with httpx.AsyncClient(timeout=60, auth=MATIAS_AUTH) as client:
            response = await client.post(
                f"{self.base_url}/clients",
                json=payload,
            )

        if response.status_code in (200, 201):
            data = response.json()
            return {"matias_client_id": data.get("id"), "status": "registered"}
        else:
            raise MATIASError(f"MATIAS registration failed: {response.text}")
```

---

## 5. Invoice Payload Format

### DentalOS → MATIAS Invoice Structure

```python
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class MATIASInvoiceLine(BaseModel):
    code: str                   # Internal code or CUPS service code
    description: str            # Service/product description
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal
    iva_rate: Decimal = Decimal("0")   # Dental services are IVA-exempt
    iva_amount: Decimal = Decimal("0")
    total: Decimal


class MATIASInvoiceCustomer(BaseModel):
    document_type: str          # CC | NIT | CE | PASAPORTE
    document_number: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    department: Optional[str] = None


class MATIASInvoicePayload(BaseModel):
    invoice_number: str                 # e.g., "FV00000123"
    issue_date: str                     # ISO date YYYY-MM-DD
    issue_time: str                     # HH:MM:SS-05:00 (Colombia timezone)
    due_date: Optional[str] = None      # For credit invoices
    currency: str = "COP"
    payment_method: str = "EFECTIVO"    # EFECTIVO | CREDITO | TARJETA_DEBITO | etc.
    customer: MATIASInvoiceCustomer
    lines: List[MATIASInvoiceLine]
    subtotal: Decimal
    iva_total: Decimal = Decimal("0")
    total: Decimal
    notes: Optional[str] = None
    # For credit notes:
    referenced_invoice_number: Optional[str] = None
    referenced_invoice_cufe: Optional[str] = None
    credit_note_reason: Optional[str] = None


def build_matias_payload(invoice: dict, patient: dict, config: dict) -> dict:
    """
    Build the MATIAS API invoice payload from DentalOS invoice data.
    """
    return {
        "invoiceNumber": invoice["invoice_number"],
        "issueDate": invoice["issue_date"],
        "issueTime": invoice["issue_time"],
        "currency": "COP",
        "paymentMethod": _map_payment_method(invoice["payment_method"]),
        "customer": {
            "documentType": patient["document_type"],
            "documentNumber": patient["document_number"],
            "firstName": patient["first_name"],
            "lastName": patient["last_name"],
            "email": patient["email"],
            "phone": patient.get("phone"),
            "address": patient.get("address"),
            "city": patient.get("city"),
        },
        "lines": [
            {
                "code": line["service_code"],
                "description": line["description"],
                "quantity": str(line["quantity"]),
                "unitPrice": str(line["unit_price"]),
                "subtotal": str(line["subtotal"]),
                "ivaRate": "0",          # Dental services IVA-exempt
                "ivaAmount": "0",
                "total": str(line["total"]),
            }
            for line in invoice["lines"]
        ],
        "subtotal": str(invoice["subtotal"]),
        "ivaTotal": "0",
        "total": str(invoice["total"]),
        "notes": invoice.get("notes"),
    }


PAYMENT_METHOD_MAP = {
    "cash": "EFECTIVO",
    "card_credit": "TARJETA_CREDITO",
    "card_debit": "TARJETA_DEBITO",
    "transfer": "TRANSFERENCIA",
    "pse": "PSE",
    "check": "CHEQUE",
    "other": "OTRO",
}

def _map_payment_method(internal_method: str) -> str:
    return PAYMENT_METHOD_MAP.get(internal_method, "EFECTIVO")
```

---

## 6. Queue-Based Processing (RabbitMQ)

### Queue Configuration

| Queue | Exchange | Routing Key | Consumer |
|-------|----------|-------------|---------|
| `dian.outbound` | `billing` | `dian.emit` | `MATIASWorker` |
| `dian.credit_notes` | `billing` | `dian.credit_note` | `MATIASWorker` |
| `dian.outbound.dlq` | `billing.dlq` | `dian.dead` | `DLQMonitor` |

### Job Payload

```python
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime


class MATIASJob(BaseModel):
    job_id: str = str(uuid.uuid4())
    tenant_id: str
    invoice_id: str
    action: str = "emit"            # emit | credit_note | check_status
    matias_id: Optional[str] = None  # For check_status
    attempt: int = 0
    max_attempts: int = 5
    created_at: datetime = datetime.utcnow()
```

### Worker

```python
import logging
from app.integrations.matias.service import MATIASService
from app.repositories.dian import (
    get_tenant_dian_config,
    get_invoice_for_dian,
    get_patient_for_invoice,
    create_electronic_invoice_log,
    update_electronic_invoice_log,
)

logger = logging.getLogger(__name__)


class MATIASWorker:
    async def process_job(self, job: MATIASJob) -> None:
        async with get_tenant_session(job.tenant_id) as session:
            # 1. Load tenant DIAN config
            config = await get_tenant_dian_config(session, job.tenant_id)
            if not config or not config.is_active:
                logger.warning(
                    "DIAN not configured for tenant",
                    extra={"tenant_id": job.tenant_id}
                )
                return

            # 2. Check environment
            matias = MATIASService(environment=config.environment)

            # 3. Load invoice and patient
            invoice = await get_invoice_for_dian(session, job.invoice_id)
            patient = await get_patient_for_invoice(session, invoice.patient_id)

            # 4. Build payload
            payload = build_matias_payload(invoice, patient, config)

            try:
                # 5. Emit via MATIAS
                result = await matias.emit_invoice(
                    nit=config.nit,
                    invoice_payload=payload,
                )

                # 6. Store result
                await create_electronic_invoice_log(session, {
                    "invoice_id": job.invoice_id,
                    "cufe": result["cufe"],
                    "matias_id": result["matias_id"],
                    "xml_url": result["xml_url"],
                    "pdf_url": result["pdf_url"],
                    "dian_status": result["dian_status"],
                    "submitted_at": datetime.utcnow(),
                    "environment": config.environment,
                })

                # 7. Update invoice with CUFE
                await update_invoice_cufe(
                    session,
                    job.invoice_id,
                    cufe=result["cufe"],
                    electronic_status="accepted",
                )

                # 8. Download PDF from MATIAS and store in S3
                await enqueue_download_invoice_pdf(
                    job.tenant_id,
                    job.invoice_id,
                    result["pdf_url"],
                )

                logger.info(
                    "DIAN invoice emitted via MATIAS",
                    extra={
                        "tenant_id": job.tenant_id,
                        "invoice_id": job.invoice_id,
                        "cufe": result["cufe"],
                    }
                )

            except MATIASError as exc:
                logger.error(
                    "MATIAS error",
                    extra={"tenant_id": job.tenant_id, "error": str(exc)}
                )
                await update_electronic_invoice_log(
                    session,
                    invoice_id=job.invoice_id,
                    dian_status="error",
                    error_message=str(exc),
                )
                raise  # Trigger retry
```

---

## 7. Invoice Number Sequence

```python
async def get_next_invoice_number(tenant_id: str) -> str:
    """
    Atomically increment invoice number within DIAN resolution range.
    Uses SELECT FOR UPDATE to prevent race conditions.
    """
    async with get_public_session() as session:
        result = await session.execute(
            select(TenantDIANMatiasConfig)
            .where(TenantDIANMatiasConfig.tenant_id == tenant_id)
            .with_for_update()
        )
        config = result.scalar_one()

        next_number = config.current_invoice_number + 1

        if next_number > config.resolution_range_to:
            raise InvoiceRangeExhausted(
                "Rango de numeración DIAN agotado. "
                "Solicita una nueva resolución al equipo DentalOS."
            )

        await session.execute(
            update(TenantDIANMatiasConfig)
            .where(TenantDIANMatiasConfig.tenant_id == tenant_id)
            .values(current_invoice_number=next_number)
        )
        await session.commit()

        prefix = config.resolution_prefix or ""
        return f"{prefix}{str(next_number).zfill(8)}"
```

---

## 8. Electronic Invoice Log (Tenant Schema)

```sql
CREATE TABLE electronic_invoice_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id          UUID NOT NULL,
    document_type       VARCHAR(5) NOT NULL DEFAULT '01',  -- 01 | 91 | 92
    invoice_number      VARCHAR(30) NOT NULL,
    cufe                VARCHAR(96),                        -- SHA-384 hex
    matias_id           VARCHAR(100),                       -- MATIAS internal ID
    xml_url             TEXT,                               -- MATIAS-hosted XML URL
    pdf_url             TEXT,                               -- MATIAS-hosted PDF URL
    pdf_s3_key          VARCHAR(500),                       -- Local S3 copy
    dian_status         VARCHAR(30) DEFAULT 'pending',
    -- pending | accepted | rejected | error
    dian_rejection_reason TEXT,
    submitted_at        TIMESTAMPTZ,
    accepted_at         TIMESTAMPTZ,
    rejected_at         TIMESTAMPTZ,
    attempt_count       INTEGER DEFAULT 1,
    environment         VARCHAR(20),                        -- habilitacion | produccion
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_elec_invoice_invoice_id ON electronic_invoice_logs(invoice_id);
CREATE INDEX idx_elec_invoice_cufe ON electronic_invoice_logs(cufe) WHERE cufe IS NOT NULL;
CREATE INDEX idx_elec_invoice_status ON electronic_invoice_logs(dian_status);
```

---

## 9. Credit Note (Nota Crédito — Document 91)

When a paid invoice requires a full or partial credit:

```python
async def emit_credit_note(
    original_invoice_id: str,
    tenant_id: str,
    credit_amount: Decimal,
    reason: str,
) -> dict:
    """
    Emit a DIAN Nota Crédito for an original invoice.
    Requires original invoice CUFE.
    """
    async with get_tenant_session(tenant_id) as session:
        original_invoice = await get_invoice(session, original_invoice_id)
        original_log = await get_electronic_invoice_log(session, original_invoice_id)

        if not original_log or not original_log.cufe:
            raise InvalidOperation(
                "La factura original no tiene CUFE. No se puede emitir nota crédito."
            )

        config = await get_tenant_dian_config(session, tenant_id)

    credit_note_number = await get_next_credit_note_number(tenant_id)
    matias = MATIASService(environment=config.environment)

    payload = {
        "creditNoteNumber": credit_note_number,
        "originalInvoiceNumber": original_invoice.invoice_number,
        "originalInvoiceCufe": original_log.cufe,
        "discrepancyReasonCode": "2",      # Devolución parcial or "1" Devolución total
        "discrepancyReasonDescription": reason,
        "issueDate": datetime.utcnow().strftime("%Y-%m-%d"),
        "issueTime": datetime.utcnow().strftime("%H:%M:%S-05:00"),
        "currency": "COP",
        "customer": build_customer_from_invoice(original_invoice),
        "lines": build_credit_lines(original_invoice, credit_amount),
        "subtotal": str(credit_amount),
        "ivaTotal": "0",
        "total": str(credit_amount),
    }

    result = await matias.emit_credit_note(nit=config.nit, credit_note_payload=payload)
    return result
```

---

## 10. Error Handling

### MATIAS Error Response Format

```json
{
  "error": "DIAN_REJECTION",
  "message": "La factura fue rechazada por la DIAN",
  "code": "ZD02",
  "details": {
    "dianErrors": [
      {
        "errorCode": "FAB19",
        "errorMessage": "El NIT del emisor no coincide con el registrado en la DIAN"
      }
    ]
  }
}
```

### Error Handling Matrix

| Error Code | Meaning | Action |
|-----------|---------|--------|
| `DIAN_REJECTION` | DIAN rejected invoice | Parse DIAN sub-errors, alert clinic admin |
| `CERTIFICATE_EXPIRED` | X.509 cert expired | Alert clinic admin to upload new cert |
| `RESOLUTION_EXHAUSTED` | Invoice range exhausted | Alert clinic admin to request new resolution |
| `RESOLUTION_INVALID` | Resolution not found in DIAN | Verify resolution data |
| `CLIENT_NOT_FOUND` | NIT not registered in MATIAS | Re-register client |
| `NETWORK_ERROR` | MATIAS unreachable | Retry with exponential backoff |
| `503` | MATIAS/DIAN maintenance | Retry after 30 minutes; log as contingency |

### Retry Logic

| Attempt | Delay | Max Attempts |
|---------|-------|-------------|
| 1st | Immediate | — |
| 2nd | 30 seconds | — |
| 3rd | 5 minutes | — |
| 4th | 30 minutes | — |
| 5th | 2 hours | — |
| 6th+ | Dead letter, alert | 5 total |

DIAN/MATIAS downtime is tracked in Redis; all new jobs are held (not queued to fail) during known downtime.

---

## 11. Habilitación (Test Mode) Process

Before a clinic can issue real invoices, DIAN requires passing a set of test cases:

```python
async def run_habilitacion_test_set(tenant_id: str) -> None:
    """
    Submit the DIAN standard test set (57 test invoices) via MATIAS.
    This is a one-time process per tenant before going live.
    """
    matias = MATIASService(environment="habilitacion")

    test_invoices = load_standard_test_set()  # 57 pre-defined test scenarios
    results = []

    for test_case in test_invoices:
        result = await matias.emit_invoice(
            nit=config.nit,
            invoice_payload=test_case["payload"],
        )
        results.append({
            "test_id": test_case["id"],
            "passed": result["dian_status"] in ("ACCEPTED", "ACCEPTED_WITH_OBSERVATIONS"),
            "cufe": result.get("cufe"),
        })

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    if passed == total:
        async with get_public_session() as session:
            await session.execute(
                update(TenantDIANMatiasConfig)
                .where(TenantDIANMatiasConfig.tenant_id == tenant_id)
                .values(
                    habilitacion_completed=True,
                    habilitacion_completed_at=datetime.utcnow(),
                )
            )

    return {"passed": passed, "total": total, "ready_for_production": passed == total}
```

---

## 12. Resolution Expiry Monitoring

```python
# Scheduled job: daily at 7AM
async def check_resolution_expiry() -> None:
    """
    Alert clinic admins when:
    - Invoice number > 80% of resolution range
    - Certificate expires within 60 days
    """
    all_configs = await get_all_active_dian_configs()

    for config in all_configs:
        # Check resolution range
        range_total = config.resolution_range_to - config.resolution_range_from
        used = config.current_invoice_number - config.resolution_range_from
        usage_pct = used / range_total if range_total > 0 else 0

        if usage_pct >= 0.80:
            await send_resolution_expiry_alert(
                config.tenant_id,
                used=used,
                total=range_total,
                remaining=range_total - used,
            )

        # Check certificate
        days_to_cert_expiry = (config.certificate_valid_until - date.today()).days
        if days_to_cert_expiry <= 60:
            await send_certificate_expiry_alert(
                config.tenant_id,
                days_remaining=days_to_cert_expiry,
            )
```

---

## 13. Configuration Reference

### Environment Variables

| Variable | Description |
|----------|-------------|
| `MATIAS_CLIENT_ID` | DentalOS Casa de Software client ID |
| `MATIAS_API_KEY` | MATIAS API key |
| `MATIAS_BASE_URL_HAB` | Habilitación endpoint |
| `MATIAS_BASE_URL_PROD` | Production endpoint |

---

## Out of Scope

- RIPS (health claims report to Ministerio de Salud) — see compliance domain
- DIAN income tax / withholding (retención en la fuente) — clinic responsibility
- Payroll electronic documents
- DIAN MUISCA portal access
- SII Chile — see INT-06
- SAT Mexico — see INT-05
- Direct DIAN integration — see INT-04 (reference only)

---

## Acceptance Criteria

**This integration is complete when:**

- [ ] Clinic NIT registered in MATIAS successfully
- [ ] Habilitación test set passes (57 test invoices accepted by DIAN)
- [ ] Production invoice emits with valid CUFE
- [ ] CUFE stored in tenant DB and displayed on invoice PDF
- [ ] Credit note emits referencing original invoice CUFE
- [ ] Certificate expiry alerts fire at 60 days
- [ ] Resolution range alerts fire at 80% usage
- [ ] Retry logic handles MATIAS/DIAN transient errors
- [ ] Dead letter queue fires alert on 5th failure
- [ ] Invoice PDF downloaded from MATIAS and stored in S3

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All API calls defined with payloads
- [x] Setup process documented
- [x] Error handling matrix complete
- [x] Retry logic defined

### Hook 2: Architecture Compliance
- [x] Queue-based processing via RabbitMQ
- [x] Tenant config in public schema
- [x] Logs in tenant schema

### Hook 3: Security & Privacy
- [x] Certificates stored encrypted (AES-256-GCM)
- [x] MATIAS credentials in environment variables
- [x] No PHI in application logs (NIT only, not patient data)

### Hook 4: Performance & Scalability
- [x] Atomic invoice number increment (SELECT FOR UPDATE)
- [x] Retry with exponential backoff
- [x] Dead letter for permanent failures

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec — MATIAS API as primary Colombia DIAN approach |
