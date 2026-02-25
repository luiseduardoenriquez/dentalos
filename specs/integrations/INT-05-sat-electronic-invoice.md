# SAT CFDI Electronic Invoice — Mexico Spec

> **Spec ID:** INT-05
> **Status:** Draft — Future (Sprint 15-16, Mexico Launch)
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Integration with Mexico's SAT (Servicio de Administración Tributaria) for generating and certifying CFDI 4.0 (Comprobante Fiscal Digital por Internet) electronic invoices. DentalOS uses a PAC (Proveedor Autorizado de Certificación) to stamp CFDIs with the official fiscal folio (UUID). Supports factura, nota de crédito, and cancellation flows. Requires RFC and CSD certificate per tenant.

**Domain:** integrations / compliance

**Priority:** Medium — Future Sprint (Mexico launch Sprint 15-16)

**Dependencies:** INT-10 (MATIAS API — may provide Mexico support), billing domain, I-13 (compliance engine), ADR-007 (country adapter pattern)

---

## 1. Mexican Electronic Invoicing Background

### Regulatory Context

| Regulation | Description |
|-----------|------------|
| CFDI 4.0 (Anexo 20, Versión 4.0) | Current CFDI specification since January 2022 |
| NOM-024-SSA3-2010 | Healthcare information systems norm (data interoperability) |
| LIVA (Ley del IVA) | 16% VAT in Mexico; dental services may be exempt |
| CFF Art. 29-A | Required fields for fiscal receipts |
| Acuerdo SAT 2023 | Mandatory CFDI 4.0 since April 2023 |

### Key Concepts

| Term | Description |
|------|-------------|
| CFDI | Comprobante Fiscal Digital por Internet — the electronic invoice XML |
| PAC | Proveedor Autorizado de Certificación — third-party certifying provider |
| UUID / Folio Fiscal | Unique identifier assigned by PAC during stamping |
| CSD | Certificado de Sello Digital — digital signing certificate from SAT |
| RFC | Registro Federal de Contribuyentes — Mexican tax ID |
| Timbrado | The stamping process that gives legal validity to a CFDI |
| Cancelación | Cancellation of a previously issued CFDI |
| CFDI de Traslado | Transfer-type CFDI (not used by clinics) |

### CFDI Types Used by DentalOS

| Type (TipoDeComprobante) | Use |
|--------------------------|-----|
| `I` — Ingreso | Standard invoice (sale) |
| `E` — Egreso | Credit note (discount, refund) |

---

## 2. Architecture

### PAC Selection

DentalOS integrates with a PAC for the actual timbrado. Recommended PACs for LATAM SaaS:
- **Facturama** — REST API, LATAM-friendly, multi-tenant support
- **EDICOM** — Enterprise, higher cost
- **SW Sapien (SMARTER WEB)** — Cost-effective, REST API

Recommended: **Facturama** for initial Mexico launch.

```
DentalOS Billing Service
    │
    ▼
CFDI Builder (generate XML per Anexo 20)
    │
    ▼
CSD Signer (sign with clinic's CSD certificate)
    │
    ▼
RabbitMQ: cfdi.outbound queue
    │
    ▼
CFDI Worker → PAC REST API (Facturama)
    │
    ▼
PAC stamps XML → Returns UUID + TimbreFiscalDigital
    │
    ▼
Store signed CFDI + UUID in tenant schema
    │
    ▼
Generate PDF representation (CFDI PDF)
```

### Per-Tenant Configuration

```sql
CREATE TABLE public.tenant_sat_config (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES public.tenants(id),
    rfc                     VARCHAR(13) NOT NULL,          -- 12 chars (moral) or 13 (física)
    razon_social            VARCHAR(255) NOT NULL,
    regimen_fiscal          VARCHAR(5) NOT NULL,           -- e.g., 612 (Personas Físicas c/ actividad empresarial)
    codigo_postal           VARCHAR(5) NOT NULL,           -- Required in CFDI 4.0
    csd_cert                BYTEA NOT NULL,                -- CSD .cer file (encrypted)
    csd_key                 BYTEA NOT NULL,                -- CSD .key file (encrypted)
    csd_password            TEXT NOT NULL,                 -- CSD key password (encrypted)
    csd_valid_until         DATE NOT NULL,
    pac_username            VARCHAR(100),                  -- PAC API credentials
    pac_password            TEXT,
    pac_environment         VARCHAR(20) DEFAULT 'sandbox', -- sandbox | production
    series                  VARCHAR(25) DEFAULT 'A',       -- CFDI series
    current_folio           INTEGER DEFAULT 0,             -- Internal folio counter
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMPTZ DEFAULT now()
);
```

---

## 3. CFDI 4.0 XML Structure

### Required Fields (Anexo 20)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante
    xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.sat.gob.mx/cfd/4
        http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd"
    Version="4.0"
    Serie="A"
    Folio="000001"
    Fecha="2026-04-15T10:30:00"
    Sello=""
    FormaPago="99"
    NoCertificado="00001000000504465028"
    Certificado=""
    SubTotal="1500.00"
    Descuento="0.00"
    Moneda="MXN"
    Total="1740.00"
    TipoDeComprobante="I"
    Exportacion="01"
    MetodoPago="PUE"
    LugarExpedicion="06600"
    Confirmacion="">

    <cfdi:InformacionGlobal
        Periodicidad="01"
        Meses="01"
        Año="2026"/>

    <cfdi:Emisor
        Rfc="XAXX010101000"
        Nombre="Clínica Dental del Sur S.A. de C.V."
        RegimenFiscal="612"/>

    <cfdi:Receptor
        Rfc="XAXX010101000"
        Nombre="PACIENTE GENERAL"
        DomicilioFiscalReceptor="06600"
        RegimenFiscalReceptor="616"
        UsoCFDI="S01"/>

    <cfdi:Conceptos>
        <cfdi:Concepto
            ClaveProdServ="85121800"
            Cantidad="1"
            ClaveUnidad="E48"
            Descripcion="Consulta dental general"
            ValorUnitario="1500.00"
            Importe="1500.00"
            ObjetoImp="02">
            <cfdi:Impuestos>
                <cfdi:Traslados>
                    <cfdi:Traslado
                        Base="1500.00"
                        Impuesto="002"
                        TipoFactor="Tasa"
                        TasaOCuota="0.160000"
                        Importe="240.00"/>
                </cfdi:Traslados>
            </cfdi:Impuestos>
        </cfdi:Concepto>
    </cfdi:Conceptos>

    <cfdi:Impuestos TotalImpuestosTrasladados="240.00">
        <cfdi:Traslados>
            <cfdi:Traslado
                Base="1500.00"
                Impuesto="002"
                TipoFactor="Tasa"
                TasaOCuota="0.160000"
                Importe="240.00"/>
        </cfdi:Traslados>
    </cfdi:Impuestos>

</cfdi:Comprobante>
```

### Dental Service SAT Product Codes (ClaveProdServ)

| ClaveProdServ | Description |
|--------------|-------------|
| `85121800` | Servicios de salud dental |
| `85121801` | Consulta dental |
| `85101500` | Servicios de cirugía oral |
| `85121500` | Servicios de ortodoncia |

### Tax Treatment for Dental Services

Dental services in Mexico are generally **exempt from IVA** (Act of Services with 0% IVA for healthcare), but this depends on the service type and clinic tax regime. DentalOS configures per service:

```python
from decimal import Decimal
from enum import Enum


class IVATreatment(str, Enum):
    EXEMPT = "exempt"        # 0% IVA, ObjetoImp=01
    RATE_16 = "rate_16"      # 16% IVA, ObjetoImp=02
    REDUCED = "reduced"      # 0% IVA (tasa 0%), ObjetoImp=02


def get_iva_for_service(service_code: str, tenant_config: dict) -> IVATreatment:
    """
    Determine IVA treatment for a dental service.
    Most dental services are IVA-exempt in Mexico.
    """
    EXEMPT_SERVICES = {
        "85121800", "85121801", "85101500",  # Dental services
    }
    if service_code in EXEMPT_SERVICES:
        return IVATreatment.EXEMPT
    return IVATreatment.RATE_16
```

---

## 4. CSD Digital Signing

The CFDI XML must be signed with the clinic's CSD (Certificado de Sello Digital) before submission to the PAC.

```python
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import base64


class CFDISigner:
    def sign(
        self,
        xml_bytes: bytes,
        csd_key_bytes: bytes,
        csd_password: str,
        csd_cert_bytes: bytes,
    ) -> dict:
        """
        Sign CFDI XML with CSD private key.
        Returns the base64-encoded signature and certificate.
        """
        # Load private key
        private_key = serialization.load_der_private_key(
            csd_key_bytes,
            password=csd_password.encode(),
        )

        # Compute SHA-256 digest of the XML's cadena original
        cadena = self._compute_cadena_original(xml_bytes)

        # Sign
        signature = private_key.sign(cadena.encode(), padding.PKCS1v15(), hashes.SHA256())
        signature_b64 = base64.b64encode(signature).decode()

        # Certificate as base64
        cert_b64 = base64.b64encode(csd_cert_bytes).decode()

        # Extract certificate number
        from cryptography import x509
        cert = x509.load_der_x509_certificate(csd_cert_bytes)
        no_cert = cert.serial_number

        return {
            "sello": signature_b64,
            "certificado": cert_b64,
            "no_certificado": str(no_cert),
        }

    def _compute_cadena_original(self, xml_bytes: bytes) -> str:
        """
        Apply XSLT transformation to compute cadena original.
        SAT provides the XSLT at:
        http://www.sat.gob.mx/sitio_internet/cfd/4/cadenaoriginal_4_0/cadenaoriginal_4_0.xslt
        """
        from lxml import etree
        import urllib.request

        # Cache XSLT locally (downloaded once)
        xslt_doc = etree.parse("resources/cadenaoriginal_4_0.xslt")
        transform = etree.XSLT(xslt_doc)
        doc = etree.fromstring(xml_bytes)
        result = transform(doc)
        return str(result)
```

---

## 5. PAC Integration (Facturama)

### Facturama API

```python
import httpx
from typing import Optional
import base64
import logging

logger = logging.getLogger(__name__)


class FacturamaService:
    SANDBOX_URL = "https://apisandbox.facturama.mx"
    PRODUCTION_URL = "https://api.facturama.mx"

    def __init__(self, username: str, password: str, environment: str = "sandbox"):
        self.base_url = (
            self.SANDBOX_URL if environment == "sandbox" else self.PRODUCTION_URL
        )
        self.auth = (username, password)

    async def stamp_cfdi(self, signed_xml: str) -> dict:
        """
        Submit a signed CFDI XML to Facturama for timbrado.
        Returns the UUID, XML with TimbreFiscalDigital, and PDF.
        """
        payload = {
            "type": "issuedLite",
            "version": "4.0",
            "xml": base64.b64encode(signed_xml.encode()).decode(),
        }

        async with httpx.AsyncClient(timeout=60, auth=self.auth) as client:
            response = await client.post(
                f"{self.base_url}/api-lite/3/cfdis",
                json=payload,
            )

        if response.status_code == 201:
            data = response.json()
            return {
                "uuid": data["Id"],
                "xml_content": base64.b64decode(data["Content"]["XML"]).decode(),
                "pdf_content": base64.b64decode(data["Content"]["PDF"]),
                "status": "stamped",
            }
        else:
            error = response.json()
            raise CFDIStampingError(
                f"PAC error: {error.get('ModelState', error.get('Message', 'Unknown'))}"
            )

    async def cancel_cfdi(
        self,
        rfc_emisor: str,
        uuid: str,
        motivo: str,
        uuid_sustitucion: Optional[str] = None,
    ) -> dict:
        """
        Cancel a previously issued CFDI.
        Motivos: 01=Comprobante emitido con errores con relación,
                 02=Comprobante emitido con errores sin relación,
                 03=No se llevó a cabo la operación,
                 04=Operación nominativa relacionada en una factura global
        """
        params = {
            "type": "issuedLite",
            "id": uuid,
            "motivo": motivo,
        }
        if uuid_sustitucion:
            params["folioSustitucion"] = uuid_sustitucion

        async with httpx.AsyncClient(timeout=60, auth=self.auth) as client:
            response = await client.delete(
                f"{self.base_url}/api-lite/cfdis/{uuid}",
                params=params,
            )

        return {"status": "cancelled" if response.status_code == 200 else "error"}
```

---

## 6. Queue-Based Processing (RabbitMQ)

### Queue Configuration

| Queue | Exchange | Routing Key |
|-------|----------|-------------|
| `cfdi.outbound` | `billing` | `cfdi.stamp` |
| `cfdi.cancel` | `billing` | `cfdi.cancel` |
| `cfdi.outbound.dlq` | `billing.dlq` | `cfdi.dead` |

### Job Payload

```python
from pydantic import BaseModel
from typing import Optional
import uuid as uuid_mod
from datetime import datetime


class CFDIJob(BaseModel):
    job_id: str = str(uuid_mod.uuid4())
    tenant_id: str
    invoice_id: str
    action: str = "stamp"          # stamp | cancel
    # For cancellation:
    cfdi_uuid: Optional[str] = None
    cancel_motivo: Optional[str] = None
    cancel_uuid_sustitucion: Optional[str] = None
    attempt: int = 0
    max_attempts: int = 3
    created_at: datetime = datetime.utcnow()
```

---

## 7. CFDI Status Tracking (Tenant Schema)

```sql
CREATE TABLE cfdi_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id          UUID NOT NULL,
    tipo_comprobante    VARCHAR(1) NOT NULL,       -- I | E
    serie               VARCHAR(25),
    folio               VARCHAR(20),
    rfc_emisor          VARCHAR(13),
    rfc_receptor        VARCHAR(13),
    uuid                VARCHAR(36),               -- UUID assigned by PAC
    xml_content         TEXT,                      -- Full stamped XML
    pdf_content         BYTEA,                     -- PDF representation
    pac_provider        VARCHAR(50),               -- facturama | edicom | etc.
    status              VARCHAR(20) DEFAULT 'pending',
    -- pending | stamped | cancelled | error
    pac_response        TEXT,                      -- Raw PAC response (errors)
    stamped_at          TIMESTAMPTZ,
    cancelled_at        TIMESTAMPTZ,
    cancellation_motivo VARCHAR(5),
    environment         VARCHAR(20),               -- sandbox | production
    created_at          TIMESTAMPTZ DEFAULT now()
);
```

---

## 8. Cancellation Flow

```python
async def cancel_cfdi(
    invoice_id: str,
    tenant_id: str,
    motivo: str,
    sustitucion_invoice_id: Optional[str] = None,
) -> None:
    """
    Cancel a CFDI. Required when:
    - Invoice was issued with errors
    - Patient returns for refund
    - Appointment cancelled after invoice issued
    """
    async with get_tenant_session(tenant_id) as session:
        # 1. Get CFDI log
        cfdi_log = await get_cfdi_log_by_invoice(session, invoice_id)
        if not cfdi_log or cfdi_log.status != "stamped":
            raise InvalidOperation("El CFDI no está en estado sellado")

        # 2. Get sustitucion UUID if applicable
        uuid_sustitucion = None
        if sustitucion_invoice_id:
            sust_log = await get_cfdi_log_by_invoice(session, sustitucion_invoice_id)
            uuid_sustitucion = sust_log.uuid

        # 3. Enqueue cancellation job
        job = CFDIJob(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            action="cancel",
            cfdi_uuid=cfdi_log.uuid,
            cancel_motivo=motivo,
            cancel_uuid_sustitucion=uuid_sustitucion,
        )
        await enqueue_cfdi_job(job)
```

---

## 9. SAT Certificate (CSD) Validation

```python
from cryptography import x509
from datetime import datetime


def validate_csd_certificate(cert_bytes: bytes) -> dict:
    """
    Validate CSD certificate before storing.
    Returns certificate metadata.
    """
    cert = x509.load_der_x509_certificate(cert_bytes)
    now = datetime.utcnow()

    if cert.not_valid_after < now:
        raise InvalidCertificateError("El certificado CSD está vencido")

    if cert.not_valid_before > now:
        raise InvalidCertificateError("El certificado CSD aún no es válido")

    days_until_expiry = (cert.not_valid_after - now).days
    if days_until_expiry < 30:
        # Alert but don't reject
        logger.warning(
            "CSD certificate expiring soon",
            extra={"days_left": days_until_expiry}
        )

    return {
        "serial_number": str(cert.serial_number),
        "valid_from": cert.not_valid_before.isoformat(),
        "valid_until": cert.not_valid_after.isoformat(),
        "subject_rfc": _extract_rfc_from_subject(cert.subject),
        "days_until_expiry": days_until_expiry,
    }
```

---

## 10. Configuration Reference

### Environment Variables

| Variable | Description |
|----------|-------------|
| `SAT_PAC_PROVIDER` | PAC to use: `facturama` |
| `FACTURAMA_USERNAME` | Facturama API username |
| `FACTURAMA_PASSWORD` | Facturama API password |
| `SAT_ENVIRONMENT` | `sandbox` or `production` |
| `SAT_XSLT_PATH` | Path to SAT cadena original XSLT file |

---

## 11. Error Handling

| PAC Error | Meaning | Action |
|----------|---------|--------|
| `CFDI33190` | RFC receiver not found in SAT | Use XAXX010101000 (public) |
| `CFDI33106` | CSD certificate expired | Alert tenant admin |
| `CFDI33115` | Fiscal date out of range | Correct invoice date |
| `CFDI33109` | Invalid product/service code | Validate ClaveProdServ |
| `PAC` network error | PAC unavailable | Retry with backoff |

---

## Out of Scope

- CFDI nómina (payroll) — not applicable for clinics
- CFDI traslado
- Mexico IMSS/ISSSTE insurance billing
- DIAN Colombia — see INT-04 and INT-10
- SII Chile — see INT-06

---

## Implementation Timeline

- **Sprint 15-16:** Mexico PAC integration, CFDI generation, stamping
- **Sprint 17:** CFDI cancellation, credit notes
- **Sprint 18:** SAT validation (XML schema verification)
- **Beta:** Selected Mexico clinics

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec — future implementation (Sprint 15-16) |
