# DIAN Electronic Invoice (Direct) Spec

> **Spec ID:** INT-04
> **Status:** Draft — Superseded by INT-10 (MATIAS API) for production use
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Direct integration with Colombia's DIAN (Dirección de Impuestos y Aduanas Nacionales) electronic invoicing system via the UBL 2.1 standard. Generates XML invoices with digital signatures (X.509), computes CUFE codes, and submits to DIAN web services. This spec documents the direct approach; however, **INT-10 (MATIAS API) is the recommended production implementation** as it abstracts DIAN complexity for the "Casa de Software" model.

**Domain:** integrations / compliance

**Priority:** High (Colombia, required by Resolución 1888 by April 2026)

**Dependencies:** INT-10 (MATIAS API, preferred approach), billing domain, I-13 (compliance engine), ADR-007 (country adapter pattern)

---

## 1. Colombian Electronic Invoicing Background

### Regulatory Context

| Regulation | Requirement |
|-----------|------------|
| Resolución DIAN 000042/2020 | Technical specification for electronic invoicing (UBL 2.1) |
| Resolución DIAN 000012/2021 | CUFE computation |
| Resolución 1888/2021 (MinSalud) | Healthcare billing requirements |
| Decreto 2364/2012 (Ley 527/1999) | Legal validity of digital signatures |

### Document Types

| Code | Name | Description |
|------|------|-------------|
| `01` | Factura de Venta | Standard sale invoice |
| `02` | Factura de Exportación | Export invoice (not used by clinics) |
| `03` | Documento Equivalente | Equivalent document (POS) |
| `91` | Nota Crédito | Credit note (refunds, corrections) |
| `92` | Nota Débito | Debit note (additional charges) |

DentalOS uses: `01` (Factura de Venta) and `91` (Nota Crédito).

---

## 2. Architecture

### Components

```
Billing Service
    │
    ▼
DIAN Invoice Builder
    │ generates UBL 2.1 XML
    ▼
XML Signer (X.509 certificate)
    │ signs XML (XAdES-BES)
    ▼
CUFE Calculator
    │ computes unique invoice code
    ▼
RabbitMQ: dian.outbound queue
    │
    ▼
DIAN Worker (consumer)
    │
    ├─► DIAN Habilitación (test) → https://vpfe-hab.dian.gov.co/
    │
    └─► DIAN Producción → https://vpfe.dian.gov.co/
         │
         ▼
    Status Poller (async, 5s interval up to 60s)
         │
         ▼
    Update invoice status in tenant schema
```

### Per-Tenant Configuration

```sql
CREATE TABLE public.tenant_dian_config (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES public.tenants(id),
    nit                     VARCHAR(15) NOT NULL,      -- RUT/NIT without check digit
    nit_check_digit         VARCHAR(1) NOT NULL,
    razon_social            VARCHAR(255) NOT NULL,
    resolution_number       VARCHAR(50) NOT NULL,      -- DIAN resolution number
    resolution_date         DATE NOT NULL,
    resolution_prefix       VARCHAR(10),               -- e.g., "FV"
    resolution_range_from   INTEGER NOT NULL,
    resolution_range_to     INTEGER NOT NULL,
    certificate_p12         BYTEA NOT NULL,            -- PKCS#12 cert (encrypted)
    certificate_password    TEXT NOT NULL,             -- Encrypted password
    certificate_valid_until DATE NOT NULL,
    test_set_id             VARCHAR(100),              -- DIAN test set UUID
    environment             VARCHAR(20) DEFAULT 'habilitacion',  -- habilitacion | produccion
    current_invoice_number  INTEGER DEFAULT 0,
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMPTZ DEFAULT now()
);
```

---

## 3. CUFE Computation

The CUFE (Código Único de Factura Electrónica) uniquely identifies each invoice. It is a SHA-384 hash of concatenated invoice fields.

### CUFE Formula

```
CUFE = SHA384(
    NumFac + FecFac + HorFac +
    ValFac + CodImp1 + ValImp1 + CodImp2 + ValImp2 + CodImp3 + ValImp3 +
    ValTot + NitOFE + NumAdq + ClTec
)
```

Where:
- `NumFac` = Invoice number (e.g., `FV000001`)
- `FecFac` = Invoice date (YYYY-MM-DD)
- `HorFac` = Invoice time (HH:MM:SS-05:00 for Colombia)
- `ValFac` = Total value (18 decimal places: `1500000.00`)
- `CodImp1` = Tax code 01 (IVA) = `01`
- `ValImp1` = IVA value
- `CodImp2` = Tax code 04 (INC) = `04`
- `ValImp2` = INC value
- `CodImp3` = Tax code 03 (ICA) = `03`
- `ValImp3` = ICA value
- `ValTot` = Grand total (ValFac + taxes)
- `NitOFE` = Seller NIT
- `NumAdq` = Buyer document number
- `ClTec` = Technical key from DIAN resolution

```python
import hashlib


def compute_cufe(
    invoice_number: str,
    invoice_date: str,     # YYYY-MM-DD
    invoice_time: str,     # HH:MM:SS-05:00
    subtotal: str,         # 2 decimal places
    iva_amount: str,
    inc_amount: str,
    ica_amount: str,
    total: str,
    nit_emisor: str,
    doc_adquirente: str,
    clave_tecnica: str,
) -> str:
    """
    Compute CUFE per DIAN Resolución 000012/2021.
    All numeric values must be formatted to 2 decimal places.
    """
    concat = (
        invoice_number
        + invoice_date
        + invoice_time
        + subtotal
        + "01"  # IVA
        + iva_amount
        + "04"  # INC
        + inc_amount
        + "03"  # ICA
        + ica_amount
        + total
        + nit_emisor
        + doc_adquirente
        + clave_tecnica
    )
    return hashlib.sha384(concat.encode("utf-8")).hexdigest()
```

---

## 4. UBL 2.1 XML Generation

### XML Structure

Colombian electronic invoices use the UBL 2.1 standard with DIAN-specific extensions.

```python
from lxml import etree
from datetime import datetime
from decimal import Decimal


NAMESPACES = {
    None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "sts": "dian:gov:co:facturaelectronica:Structures-2-1",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "xades": "http://uri.etsi.org/01903/v1.3.2#",
}


class UBLInvoiceBuilder:
    def build(self, invoice_data: dict) -> bytes:
        """Build a DIAN-compliant UBL 2.1 Invoice XML."""
        root = etree.Element("Invoice", nsmap=NAMESPACES)

        # Extensions (for digital signature)
        ext_content = etree.SubElement(root, "{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}UBLExtensions")

        # UBL Version
        etree.SubElement(root, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}UBLVersionID").text = "UBL 2.1"

        # Custom Version
        etree.SubElement(root, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}CustomizationID").text = "10"

        # Invoice number
        etree.SubElement(root, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID").text = invoice_data["invoice_number"]

        # CUFE
        etree.SubElement(root, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}UUID", schemeName="CUFE-SHA384").text = invoice_data["cufe"]

        # Issue date and time
        etree.SubElement(root, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IssueDate").text = invoice_data["issue_date"]
        etree.SubElement(root, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IssueTime").text = invoice_data["issue_time"]

        # Invoice type code
        etree.SubElement(root, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoiceTypeCode").text = "01"

        # Note (optional)
        if invoice_data.get("note"):
            etree.SubElement(root, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Note").text = invoice_data["note"]

        # Document currency
        etree.SubElement(root, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}DocumentCurrencyCode").text = "COP"

        self._add_accounting_supplier(root, invoice_data["issuer"])
        self._add_accounting_customer(root, invoice_data["customer"])
        self._add_tax_total(root, invoice_data["taxes"])
        self._add_legal_monetary_total(root, invoice_data["totals"])
        self._add_invoice_lines(root, invoice_data["lines"])

        return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)

    def _add_accounting_supplier(self, parent, issuer: dict) -> None:
        """Add AccountingSupplierParty element."""
        # ... supplier NIT, name, address, tax regime
        pass

    def _add_accounting_customer(self, parent, customer: dict) -> None:
        """Add AccountingCustomerParty element."""
        # ... customer document, name, address
        pass

    def _add_tax_total(self, parent, taxes: list) -> None:
        """Add TaxTotal elements for IVA, INC, ICA."""
        pass

    def _add_legal_monetary_total(self, parent, totals: dict) -> None:
        """Add LegalMonetaryTotal with subtotal, taxes, total."""
        pass

    def _add_invoice_lines(self, parent, lines: list) -> None:
        """Add InvoiceLine elements for each service."""
        pass
```

---

## 5. Digital Signature (XAdES-BES)

DIAN requires electronic invoices to be signed with an X.509 certificate using XAdES-BES (XML Advanced Electronic Signatures — Basic Electronic Signature).

```python
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography import x509
from lxml import etree
import base64
import datetime


class XMLSigner:
    def sign(self, xml_bytes: bytes, cert_p12: bytes, cert_password: str) -> bytes:
        """
        Sign UBL XML with X.509 certificate using XAdES-BES.
        Returns the signed XML bytes.
        """
        from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates

        private_key, certificate, chain = load_key_and_certificates(
            cert_p12,
            cert_password.encode(),
        )

        # Parse XML
        root = etree.fromstring(xml_bytes)

        # Build signature elements (XAdES-BES structure)
        # 1. Calculate digest of SignedInfo
        # 2. Sign digest with private key
        # 3. Embed certificate in KeyInfo
        # 4. Embed XAdES qualifying properties
        # (Full XAdES-BES implementation details omitted for brevity —
        #  use signxml or lxml-xades library in implementation)

        signed_xml = self._build_xades_signature(root, private_key, certificate)
        return etree.tostring(signed_xml, xml_declaration=True, encoding="UTF-8")

    def _extract_cert_info(self, certificate) -> dict:
        """Extract certificate metadata for XML embedding."""
        return {
            "subject": certificate.subject.rfc4514_string(),
            "issuer": certificate.issuer.rfc4514_string(),
            "serial": str(certificate.serial_number),
            "valid_from": certificate.not_valid_before.isoformat(),
            "valid_until": certificate.not_valid_after.isoformat(),
            "fingerprint_sha256": certificate.fingerprint(hashes.SHA256()).hex(),
        }
```

---

## 6. DIAN Web Services

### Endpoints

| Environment | Endpoint |
|------------|---------|
| Habilitación (test) | `https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc` |
| Producción | `https://vpfe.dian.gov.co/WcfDianCustomerServices.svc` |

### SOAP Operations Used

| Operation | Description |
|-----------|------------|
| `SendBillSync` | Send invoice and get immediate response |
| `SendBillAsync` | Send invoice, get tracking ID (TrackId) |
| `GetStatus` | Poll status by TrackId |
| `GetStatusZip` | Get full response for a set of documents |
| `GetNumberingRange` | Verify resolution range is valid |

### DIAN Worker

```python
import zeep
import base64
import zipfile
import io
import logging

logger = logging.getLogger(__name__)


class DIANService:
    def __init__(self, wsdl_url: str, nit: str, cert_p12: bytes, cert_password: str):
        self.client = zeep.Client(wsdl=wsdl_url)
        self.nit = nit
        self.cert_p12 = cert_p12
        self.cert_password = cert_password

    async def submit_invoice(self, signed_xml: bytes, invoice_number: str) -> dict:
        """
        Submit signed invoice to DIAN.
        Compresses XML to ZIP, encodes as base64, calls SendBillAsync.
        """
        # 1. Compress XML to ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            filename = f"{self.nit}{invoice_number}.xml"
            zf.writestr(filename, signed_xml)
        zip_content = zip_buffer.getvalue()

        # 2. Encode as base64
        encoded = base64.b64encode(zip_content).decode()

        # 3. Build ZIP filename
        zip_filename = f"{self.nit}{invoice_number}.zip"

        # 4. Call DIAN SOAP service
        try:
            response = self.client.service.SendBillAsync(
                fileName=zip_filename,
                contentFile=encoded,
                testSetId=None,  # None for production
            )
            return {
                "track_id": response.TrackId,
                "status": response.ErrorMessageList,
            }
        except Exception as exc:
            logger.error("DIAN submission error", extra={"error": str(exc)})
            raise

    async def poll_status(self, track_id: str) -> dict:
        """Poll DIAN for invoice processing status."""
        response = self.client.service.GetStatus(trackId=track_id)
        return {
            "status_code": response.StatusCode,
            "status_description": response.StatusDescription,
            "is_valid": response.IsValid,
            "cufe": response.XmlDocumentKey,
            "errors": [e.ErrorMessage for e in (response.ErrorMessageList or [])],
        }
```

---

## 7. Invoice Number Sequence

Invoice numbers must be sequential within the DIAN-assigned resolution range.

```python
import asyncpg
from app.db.public import get_public_session


async def get_next_invoice_number(tenant_id: str, prefix: str) -> str:
    """
    Atomically get and increment the next invoice number for a tenant.
    Uses SELECT FOR UPDATE to prevent race conditions.
    """
    async with get_public_session() as session:
        result = await session.execute(
            select(TenantDIANConfig)
            .where(TenantDIANConfig.tenant_id == tenant_id)
            .with_for_update()
        )
        config = result.scalar_one()

        if config.current_invoice_number >= config.resolution_range_to:
            raise InvoiceRangeExhaustedError(
                "Rango de numeración DIAN agotado. "
                "Solicita una nueva resolución."
            )

        next_number = config.current_invoice_number + 1
        await session.execute(
            update(TenantDIANConfig)
            .where(TenantDIANConfig.tenant_id == tenant_id)
            .values(current_invoice_number=next_number)
        )
        await session.commit()

        # Format: prefix + zero-padded number
        return f"{prefix}{str(next_number).zfill(8)}"
```

---

## 8. Status Tracking (Tenant Schema)

```sql
CREATE TABLE electronic_invoice_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id          UUID NOT NULL,              -- FK to invoices table
    document_type       VARCHAR(5) NOT NULL,        -- 01 | 91 | 92
    invoice_number      VARCHAR(20) NOT NULL,
    cufe                VARCHAR(96),                -- SHA-384 = 96 hex chars
    xml_content         TEXT,                       -- Stored signed XML
    pdf_content         BYTEA,                      -- Generated invoice PDF
    dian_track_id       VARCHAR(100),
    dian_status         VARCHAR(30) DEFAULT 'pending',
    -- pending | accepted | rejected | contingency
    dian_status_message TEXT,
    submitted_at        TIMESTAMPTZ,
    accepted_at         TIMESTAMPTZ,
    rejected_at         TIMESTAMPTZ,
    attempt_count       INTEGER DEFAULT 0,
    environment         VARCHAR(20),                -- habilitacion | produccion
    created_at          TIMESTAMPTZ DEFAULT now()
);
```

---

## 9. Test Mode (Habilitación)

DIAN provides a test environment (`vpfe-hab.dian.gov.co`) where clinics must pass a set of test cases before going live.

**Habilitación process:**
1. Tenant creates account on DIAN portal as "Obligado a Facturar Electrónicamente"
2. Obtains test set ID from DIAN
3. DentalOS submits 57 mandatory test invoices (DIAN's standard test set) via habilitación endpoint
4. DIAN reviews and approves
5. Tenant switches `environment` to `produccion`
6. DentalOS validates resolution range and goes live

---

## 10. Credit Notes (Nota Crédito — Document Type 91)

When an invoice is partially or fully refunded:

```python
class CreditNoteBuilder(UBLInvoiceBuilder):
    def build_credit_note(self, original_invoice: dict, refund_data: dict) -> bytes:
        """
        Build a DIAN-compliant Nota Crédito (type 91).
        Must reference the original invoice CUFE.
        """
        # Similar structure to invoice but with:
        # - InvoiceTypeCode = "91"
        # - DiscrepancyResponse: reason code + description
        # - BillingReference: original invoice number + CUFE
        pass
```

---

## 11. Error Handling

### DIAN Error Codes

| Code | Description | Action |
|------|-------------|--------|
| `ZD01` | Invoice accepted | Mark as accepted |
| `ZD02` | Document rejected | Parse rejection reason, alert clinic admin |
| `ZD04` | Document in process | Retry GetStatus in 10 seconds |
| `ZD06` | NIT not authorized | Tenant NIT not registered on DIAN |
| `99` | System error | Retry after 60 seconds |

---

## 12. Note on MATIAS API (INT-10)

**IMPORTANT:** DentalOS should use INT-10 (MATIAS API) for production Colombian electronic invoicing. MATIAS abstracts:
- XML generation
- Digital signature
- DIAN submission
- Status polling
- Test mode management

This spec (INT-04) documents the direct integration for reference, for understanding the underlying standard, and as a fallback if MATIAS is unavailable.

---

## Out of Scope

- SAT CFDI (Mexico) — see INT-05
- SII DTE (Chile) — see INT-06
- RIPS (health claims reporting) — see compliance domain specs
- DIAN payroll electronic documents (nómina electrónica) — not applicable
- DIAN income tax returns

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec — direct DIAN integration (superseded by INT-10 for production) |
