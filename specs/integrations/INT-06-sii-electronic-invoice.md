# SII Electronic Invoice — Chile Spec

> **Spec ID:** INT-06
> **Status:** Draft — Future (Sprint 17+, Chile Launch)
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Integration with Chile's SII (Servicio de Impuestos Internos) for generating and submitting DTE (Documento Tributario Electrónico) electronic invoices. Handles CAF (Código de Autorización de Folios) management, XML generation with digital signature, SII submission, and acknowledgment processing. Requires RUT and digital certificate per tenant.

**Domain:** integrations / compliance

**Priority:** Low — Future Sprint (Chile launch Sprint 17+)

**Dependencies:** billing domain, I-13 (compliance engine — ChileAdapter), ADR-007 (country adapter pattern)

---

## 1. Chilean Electronic Invoicing Background

### Regulatory Context

| Regulation | Description |
|-----------|------------|
| Resolución SII N°45/2003 | First DTE regulations |
| Resolución SII N°11/2014 | Current technical DTE specification |
| Resolución SII N°61/2019 | Mandatory electronic billing for all |
| Circular N°27/2019 | Mandatory from November 2020 for healthcare |
| DL 825 (Ley IVA) | 19% VAT; dental services partially exempt |

### Key Concepts

| Term | Description |
|------|-------------|
| DTE | Documento Tributario Electrónico — the electronic document |
| Folio | Sequential document number |
| CAF | Código de Autorización de Folios — block of authorized folios from SII |
| RUT | Rol Único Tributario — Chilean tax ID (e.g., 12.345.678-9) |
| MIPYME | Small/medium enterprise — simplified invoicing for small clinics |
| SET ID | Test set identifier from SII certification process |
| Timbre Electrónico | Electronic stamp = TED (Timbre Electrónico de DTE) |
| Acuse de Recibo | Acknowledgment from recipient |
| Libro de Ventas | Monthly sales book submitted to SII |

### DTE Document Types Used by DentalOS

| Code (TipoDTE) | Name | Description |
|----------------|------|-------------|
| `33` | Factura Electrónica | Standard taxable invoice (IVA) |
| `34` | Factura No Afecta o Exenta | Invoice for exempt services |
| `61` | Nota de Crédito Electrónica | Credit note (refunds, corrections) |
| `56` | Nota de Débito Electrónica | Debit note |

DentalOS uses primarily `34` (most dental services are IVA-exempt in Chile) and `33` for taxable dental prosthetics/goods.

---

## 2. Architecture

```
DentalOS Billing Service
    │
    ▼
DTE Builder (XML generation)
    │
    ▼
CAF Manager (folio allocation)
    │ assigns next folio from active CAF
    ▼
TED Generator (Timbre Electrónico de DTE)
    │ generates PDF417 barcode data
    ▼
XML Signer (X.509 certificate + SHA-1 per SII spec)
    │
    ▼
RabbitMQ: dte.outbound queue
    │
    ▼
DTE Worker
    │
    ├─► SII Certification (test set) → https://maullin.sii.cl/
    │
    └─► SII Production → https://palena.sii.cl/
         │
         ▼
    Track ID → Poll acknowledgment (up to 24h)
         │
         ▼
    Store in tenant schema
```

### Per-Tenant Configuration

```sql
CREATE TABLE public.tenant_sii_config (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES public.tenants(id),
    rut                     VARCHAR(12) NOT NULL,       -- e.g., "76543210-9"
    razon_social            VARCHAR(255) NOT NULL,
    giro                    VARCHAR(80) NOT NULL,       -- Economic activity
    address                 VARCHAR(200) NOT NULL,
    commune                 VARCHAR(100) NOT NULL,
    city                    VARCHAR(100) NOT NULL,
    certificate_p12         BYTEA NOT NULL,             -- X.509 cert (encrypted)
    certificate_password    TEXT NOT NULL,              -- Encrypted
    certificate_valid_until DATE NOT NULL,
    resolution_number       INTEGER,                    -- SII resolution number
    resolution_date         DATE,
    environment             VARCHAR(20) DEFAULT 'certification',  -- certification | production
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMPTZ DEFAULT now()
);
```

---

## 3. CAF (Código de Autorización de Folios) Management

### What is a CAF?

A CAF is a signed block of authorized folio numbers obtained from SII. Each CAF has:
- Document type (e.g., `34` for exempt invoice)
- Initial folio (`RangoDesde`)
- Final folio (`RangoHasta`)
- SII's RSA private key (for TED generation)
- SII's public key (for verification)
- Valid for 6 months from issuance

### CAF Storage

```sql
CREATE TABLE public.tenant_caf (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL,
    tipo_dte            INTEGER NOT NULL,               -- 33 | 34 | 61 | 56
    folio_desde         INTEGER NOT NULL,
    folio_hasta         INTEGER NOT NULL,
    current_folio       INTEGER NOT NULL,
    caf_xml             TEXT NOT NULL,                  -- Full CAF XML (contains private key)
    is_exhausted        BOOLEAN DEFAULT FALSE,
    expires_at          DATE NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX idx_tenant_caf_active
    ON public.tenant_caf(tenant_id, tipo_dte)
    WHERE NOT is_exhausted;
```

### Folio Allocation

```python
async def get_next_folio(
    tenant_id: str,
    tipo_dte: int,
) -> tuple[int, str]:
    """
    Atomically allocate the next folio from the active CAF.
    Returns (folio_number, caf_xml).
    Raises CAFExhaustedError if no CAF available.
    Raises CAFExpiringWarning if CAF expires in < 30 days.
    """
    async with get_public_session() as session:
        result = await session.execute(
            select(TenantCAF)
            .where(
                TenantCAF.tenant_id == tenant_id,
                TenantCAF.tipo_dte == tipo_dte,
                not TenantCAF.is_exhausted,
                TenantCAF.expires_at > date.today(),
            )
            .order_by(TenantCAF.folio_desde)
            .with_for_update()
        )
        caf = result.scalar_one_or_none()

        if not caf:
            raise CAFExhaustedError(
                f"No hay CAF disponible para TipoDTE {tipo_dte}. "
                f"Solicita un nuevo CAF al SII."
            )

        folio = caf.current_folio
        next_folio = folio + 1

        if next_folio > caf.folio_hasta:
            caf.is_exhausted = True
        else:
            caf.current_folio = next_folio

        await session.commit()

        # Check if expiring soon
        days_until_expiry = (caf.expires_at - date.today()).days
        if days_until_expiry < 30:
            logger.warning(
                "CAF expiring soon",
                extra={"tenant_id": tenant_id, "tipo_dte": tipo_dte, "days": days_until_expiry}
            )

        return folio, caf.caf_xml
```

### CAF Replenishment

When a CAF reaches 80% usage, DentalOS alerts the clinic admin to request a new CAF from SII:
- Clinic admin logs into SII portal
- Requests new CAF block (download as XML)
- Uploads CAF XML in DentalOS Settings → Billing → Chile → CAF Management

---

## 4. DTE XML Generation

### Document Structure

```xml
<?xml version="1.0" encoding="ISO-8859-1"?>
<DTE version="1.0">
  <Documento ID="F34T000001">
    <Encabezado>
      <IdDoc>
        <TipoDTE>34</TipoDTE>
        <Folio>1</Folio>
        <FchEmis>2026-04-15</FchEmis>
        <IndServicio>3</IndServicio>  <!-- 3=Services -->
        <MntBruto>1</MntBruto>
        <FmaPago>1</FmaPago>         <!-- 1=Cash, 2=Credit -->
      </IdDoc>
      <Emisor>
        <RUTEmisor>76543210-9</RUTEmisor>
        <RznSoc>Clínica Dental Del Sur SpA</RznSoc>
        <GiroEmis>Servicios dentales</GiroEmis>
        <DirOrigen>Av. Providencia 1234</DirOrigen>
        <CmnaOrigen>Providencia</CmnaOrigen>
        <CiudadOrigen>Santiago</CiudadOrigen>
      </Emisor>
      <Receptor>
        <RUTRecep>12345678-9</RUTRecep>
        <RznSocRecep>Juan González</RznSocRecep>
        <DirRecep>Calle Falsa 123</DirRecep>
        <CmnaRecep>Las Condes</CmnaRecep>
        <CiudadRecep>Santiago</CiudadRecep>
      </Receptor>
      <Totales>
        <MntExe>150000</MntExe>     <!-- Exempt amount (dental services) -->
        <MntTotal>150000</MntTotal>
      </Totales>
    </Encabezado>
    <Detalle>
      <NroLinDet>1</NroLinDet>
      <NmbItem>Consulta dental general</NmbItem>
      <QtyItem>1</QtyItem>
      <UnmdItem>UN</UnmdItem>
      <PrcItem>150000</PrcItem>
      <MontoItem>150000</MontoItem>
    </Detalle>
    <TED version="1.0">
      <DD>
        <RE>76543210-9</RE>
        <TD>34</TD>
        <F>1</F>
        <FE>2026-04-15</FE>
        <RR>12345678-9</RR>
        <RSR>Juan González</RSR>
        <MNT>150000</MNT>
        <IT1>Consulta dental general</IT1>
        <CAF version="1.0">
          <!-- Embedded CAF data -->
        </CAF>
        <TSTED>2026-04-15T10:30:00</TSTED>
      </DD>
      <FRMA algoritmo="SHA1withRSA">SIGNATURE_HERE</FRMA>
    </TED>
  </Documento>
</DTE>
```

---

## 5. TED (Timbre Electrónico de DTE)

The TED is the electronic stamp embedded in each DTE. It contains key document data and is signed with the SII's RSA key (from the CAF). The TED is also rendered as a PDF417 barcode on printed representations.

```python
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from lxml import etree
import base64


class TEDGenerator:
    def generate(
        self,
        tipo_dte: int,
        folio: int,
        fecha_emision: str,
        rut_emisor: str,
        rut_receptor: str,
        razon_social_receptor: str,
        monto_total: int,
        first_item: str,
        caf_xml: str,
        timestamp: str,
    ) -> str:
        """
        Generate TED (Timbre Electrónico) and sign with SII CAF key.
        Returns the TED XML string to embed in the DTE.
        """
        # Parse CAF to extract SII private key
        caf_root = etree.fromstring(caf_xml.encode())
        sii_private_key_pem = caf_root.find(".//RSASK").text.strip()

        # Build DD element
        dd_content = (
            f"<RE>{rut_emisor}</RE>"
            f"<TD>{tipo_dte}</TD>"
            f"<F>{folio}</F>"
            f"<FE>{fecha_emision}</FE>"
            f"<RR>{rut_receptor}</RR>"
            f"<RSR>{razon_social_receptor[:40]}</RSR>"
            f"<MNT>{monto_total}</MNT>"
            f"<IT1>{first_item[:40]}</IT1>"
            f"<CAF version=\"1.0\">{caf_xml}</CAF>"
            f"<TSTED>{timestamp}</TSTED>"
        )

        # Sign DD with SII private key from CAF
        private_key = serialization.load_pem_private_key(
            sii_private_key_pem.encode(), password=None
        )
        signature = private_key.sign(
            dd_content.encode("ISO-8859-1"),
            padding.PKCS1v15(),
            hashes.SHA1(),  # SII requires SHA1 (legacy)
        )
        frma = base64.b64encode(signature).decode()

        return f'<TED version="1.0"><DD>{dd_content}</DD><FRMA algoritmo="SHA1withRSA">{frma}</FRMA></TED>'
```

---

## 6. XML Signing

After the TED is embedded, the full DTE XML is signed with the clinic's X.509 certificate:

```python
class DTESigner:
    def sign(
        self,
        dte_xml: bytes,
        cert_p12: bytes,
        cert_password: str,
    ) -> bytes:
        """Sign DTE with clinic's certificate. Returns signed XML."""
        from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
        from signxml import XMLSigner as XMLSignerLib

        private_key, cert, chain = load_key_and_certificates(
            cert_p12, cert_password.encode()
        )

        signer = XMLSignerLib()
        signed = signer.sign(
            etree.fromstring(dte_xml),
            key=private_key,
            cert=cert,
            reference_uri="#F34T000001",
        )
        return etree.tostring(signed, encoding="ISO-8859-1")
```

---

## 7. SII Submission

### SII REST/SOAP Services

| Environment | Endpoint |
|------------|---------|
| Certification | `https://maullin.sii.cl/cgi_dte/UPL/DTEUpload` |
| Production | `https://palena.sii.cl/cgi_dte/UPL/DTEUpload` |

### Submission Process

```python
import httpx
import base64
import hashlib


class SIIService:
    def __init__(self, environment: str = "certification"):
        self.base_url = (
            "https://maullin.sii.cl"
            if environment == "certification"
            else "https://palena.sii.cl"
        )

    async def get_token(self, rut: str, cert_p12: bytes, cert_password: str) -> str:
        """Obtain SII session token via certificate auth."""
        # SII uses a token-based auth flow:
        # 1. GET /cgi_dte/wsutils/siidte?accion=GetSeed → Seed
        # 2. Sign seed with certificate
        # 3. POST signed seed → Token
        pass

    async def submit_dte(
        self,
        token: str,
        rut_emisor: str,
        signed_xml: bytes,
        filename: str,
    ) -> dict:
        """Submit DTE XML to SII. Returns trackId."""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/cgi_dte/UPL/DTEUpload",
                headers={
                    "Cookie": f"TOKEN={token}",
                    "Content-Type": "multipart/form-data",
                },
                files={"archivo": (filename, signed_xml, "application/xml")},
                data={"rutSender": rut_emisor, "dvSender": rut_emisor[-1]},
            )

        result = self._parse_response(response.text)
        return result

    async def check_status(self, token: str, track_id: str) -> dict:
        """Check processing status of submitted DTE set."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/cgi_dte/UPL/DTEUpload",
                params={"TrackID": track_id},
                headers={"Cookie": f"TOKEN={token}"},
            )
        return self._parse_status(response.text)
```

### SII Response Status Codes

| Code | Description | Action |
|------|-------------|--------|
| `EPR` | En Proceso — processing | Poll again in 30 seconds |
| `ACD` | Aceptado con discrepancias | Accepted with warnings, review |
| `RSC` | Rechazado por el SII | Rejected — parse errors, correct and resubmit |
| `DOS` | DTE OK Aceptado | Accepted — update status to accepted |

---

## 8. Monthly Libro de Ventas (Sales Book)

SII requires a monthly report of all issued DTEs (Libro de Ventas / Libro de Compras).

```python
async def generate_libro_ventas(
    tenant_id: str,
    year: int,
    month: int,
) -> bytes:
    """
    Generate monthly sales book XML for SII submission.
    Due: 22nd of the following month.
    """
    async with get_tenant_session(tenant_id) as session:
        dte_records = await get_dte_by_period(session, year, month)

    libro = LibroVentasBuilder().build(dte_records, tenant_config)
    signed_libro = DTESigner().sign(libro, cert_p12, cert_password)
    return signed_libro
```

---

## 9. Status Tracking (Tenant Schema)

```sql
CREATE TABLE dte_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id          UUID NOT NULL,
    tipo_dte            INTEGER NOT NULL,              -- 33 | 34 | 61 | 56
    folio               INTEGER NOT NULL,
    rut_emisor          VARCHAR(12),
    rut_receptor        VARCHAR(12),
    monto_total         BIGINT,                        -- CLP (no decimals)
    ted_content         TEXT,                          -- Embedded TED
    xml_content         TEXT,                          -- Full signed DTE XML
    pdf_content         BYTEA,                         -- PDF representation
    sii_track_id        VARCHAR(50),
    sii_status          VARCHAR(20) DEFAULT 'pending',
    -- pending | en_proceso | aceptado | aceptado_con_reparos | rechazado
    sii_response        TEXT,
    submitted_at        TIMESTAMPTZ,
    accepted_at         TIMESTAMPTZ,
    environment         VARCHAR(20),
    created_at          TIMESTAMPTZ DEFAULT now()
);
```

---

## 10. Error Handling

### SII Rejection Codes

| Code | Description | Action |
|------|-------------|--------|
| `REC-31` | RUT receiver invalid | Check patient RUT format |
| `REC-24` | CAF expired | Request new CAF |
| `REC-02` | Sequence error — folio already used | Investigate folio conflict |
| `REC-33` | Invalid resolution number | Update tenant SII config |
| `REC-10` | Digital signature invalid | Re-sign and resubmit |

---

## 11. Tax Treatment for Dental Services in Chile

Most dental services are **IVA-exempt** under Chilean law (DL 825, Art. 13 letter F — medical/dental services). This means:
- Use `TipoDTE = 34` (Factura No Afecta o Exenta)
- `MntExe` = full amount
- `MntNeto = 0`, `IVA = 0`

Only dental prosthetics (goods, not services) are subject to 19% IVA.

---

## 12. Configuration Reference

### Environment Variables

| Variable | Description |
|----------|-------------|
| `SII_ENVIRONMENT` | `certification` or `production` |
| `SII_CERTIFICATION_URL` | Maullin URL |
| `SII_PRODUCTION_URL` | Palena URL |

---

## Out of Scope

- Libro de Compras (purchase book) — not applicable for clinics
- RCOF (Registro de Compras y Ventas) — automatic via SII integration
- Factura de compra
- DIAN Colombia — see INT-04 and INT-10
- SAT Mexico — see INT-05

---

## Implementation Timeline

- **Sprint 17:** Chile PAC/SII integration, DTE generation
- **Sprint 18:** CAF management UI, CAF replenishment alerts
- **Sprint 19:** Libro de Ventas automation
- **Beta:** Selected Chile clinics

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec — future implementation (Sprint 17+) |
