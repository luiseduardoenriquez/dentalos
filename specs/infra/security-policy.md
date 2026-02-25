# Security Policy Spec

> **Spec ID:** I-10
> **Status:** Draft
> **Last Updated:** 2026-02-24

---

## Overview

**Feature:** Comprehensive security policy for DentalOS covering transport security, input validation, injection prevention, PHI (Protected Health Information) handling, file upload security, and dependency management. This spec defines the security posture for a healthcare SaaS platform handling sensitive clinical data in LATAM.

**Domain:** infra

**Priority:** Critical

**Dependencies:** I-01 (multi-tenancy), I-02 (authentication-rules), I-11 (audit-logging)

---

## 1. Transport Security

### HTTPS Enforcement

All DentalOS traffic MUST use HTTPS. No exceptions.

**Implementation:**

| Layer | Mechanism | Details |
|-------|-----------|---------|
| Load balancer (Hetzner LB) | TLS termination | TLS 1.3 preferred, TLS 1.2 minimum. TLS 1.0/1.1 rejected. |
| FastAPI backend | Redirect middleware | HTTP requests return `301 Moved Permanently` to HTTPS equivalent |
| HSTS header | `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` |
| Internal services | mTLS or private network | RabbitMQ, Redis, PostgreSQL communicate over Hetzner private network (no public exposure) |

**FastAPI HTTPS redirect middleware:**

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("X-Forwarded-Proto") == "http":
            url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(url), status_code=301)
        return await call_next(request)
```

### TLS Configuration

| Parameter | Value |
|-----------|-------|
| Minimum TLS version | 1.2 |
| Preferred TLS version | 1.3 |
| Cipher suites (TLS 1.3) | TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256, TLS_AES_128_GCM_SHA256 |
| Cipher suites (TLS 1.2) | ECDHE-RSA-AES256-GCM-SHA384, ECDHE-RSA-AES128-GCM-SHA256 |
| Certificate provider | Let's Encrypt (auto-renewal via certbot) |
| Certificate type | RSA 2048-bit (upgrade to ECDSA P-256 when Hetzner LB supports it) |
| OCSP stapling | Enabled |

---

## 2. CORS Configuration

### Policy

DentalOS API uses a strict CORS policy. The frontend (Next.js) and API are served from different origins in production.

```python
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,  # Explicit list, never "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Tenant-ID",
        "X-Request-ID",
        "Accept",
        "Accept-Language",
    ],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-Request-ID",
    ],
    max_age=600,  # Preflight cache: 10 minutes
)
```

### Allowed Origins by Environment

| Environment | Origins |
|-------------|---------|
| Development | `http://localhost:3000`, `http://localhost:3001` |
| Staging | `https://staging.dentalos.app` |
| Production | `https://app.dentalos.app`, `https://portal.dentalos.app` |

### Future: Custom Domains per Tenant

When custom domain support is added (e.g., `app.clinicadental.co`), CORS origins will be dynamically resolved per tenant. The CORS middleware will query a Redis cache of tenant custom domains.

```python
# Future implementation sketch (not for v1):
# allowed_origins = await redis.smembers(f"cors:origins:{tenant_id}")
# Fallback to default origins if no custom domain configured
```

---

## 3. Content Security Policy (CSP)

CSP headers are set by the Next.js frontend (via `next.config.js` headers) and enforced by the browser.

### CSP Header Value

```
default-src 'self';
script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
img-src 'self' data: blob: https://*.hetzner.cloud https://storage.dentalos.app;
font-src 'self' https://fonts.gstatic.com;
connect-src 'self' https://api.dentalos.app wss://api.dentalos.app https://sentry.io;
frame-ancestors 'none';
base-uri 'self';
form-action 'self';
object-src 'none';
upgrade-insecure-requests;
```

**Notes:**
- `unsafe-inline` for scripts is required by Next.js (inline scripts for hydration). Consider using nonce-based CSP when Next.js supports it cleanly.
- `unsafe-eval` is required by some React dev tooling; remove in production if possible.
- `frame-ancestors 'none'` prevents clickjacking.
- `object-src 'none'` blocks Flash/Java plugins.
- `img-src blob:` is needed for odontogram SVG rendering and canvas export.

### Additional Security Headers

Set on all responses from the Next.js frontend and the FastAPI API.

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME type sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking (legacy; CSP frame-ancestors is preferred) |
| `X-XSS-Protection` | `0` | Disabled; modern CSP is preferred. This header can cause issues. |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer information leakage |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=()` | Disable unnecessary browser APIs |

**FastAPI security headers middleware:**

```python
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        # Remove server version header
        response.headers.pop("server", None)
        return response
```

---

## 4. Input Sanitization

### Pydantic Validators

All API input is validated via Pydantic v2 models. No endpoint accepts raw `dict` or unvalidated input.

**Standard validators applied to all string fields:**

```python
from pydantic import BaseModel, field_validator, ConfigDict
import re

# Maximum lengths per field type
MAX_NAME_LENGTH = 150
MAX_EMAIL_LENGTH = 254
MAX_PHONE_LENGTH = 20
MAX_TEXT_LENGTH = 5000
MAX_NOTES_LENGTH = 10000
MAX_ADDRESS_LENGTH = 500


class StrictStringMixin:
    """Mixin for string sanitization applied to all models."""

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if isinstance(v, str):
            # Strip leading/trailing whitespace
            v = v.strip()
            # Reject null bytes
            if "\x00" in v:
                raise ValueError("Input contains invalid characters")
        return v
```

### Rich Text Sanitization (Bleach)

Clinical notes and free-text fields that support basic formatting use `bleach` for HTML sanitization.

```python
import bleach

ALLOWED_TAGS = ["b", "i", "u", "br", "p", "ul", "ol", "li", "strong", "em"]
ALLOWED_ATTRIBUTES = {}  # No attributes allowed on any tag


def sanitize_rich_text(html: str) -> str:
    """Sanitize rich text input, allowing only basic formatting tags."""
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )
```

**Fields that use rich text sanitization:**
- Clinical notes (`clinical_records.notes`)
- Treatment plan descriptions (`treatment_plans.description`)
- Prescription instructions (`prescriptions.instructions`)
- Consent form content (`consents.content`)

### Regex Validation for Structured Fields

| Field Type | Regex Pattern | Example |
|------------|---------------|---------|
| Colombian cedula | `^[0-9]{6,12}$` | `1234567890` |
| Mexican CURP | `^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[A-Z0-9][0-9]$` | `GARC850101HDFRRR09` |
| Chilean RUT | `^[0-9]{7,8}-[0-9Kk]$` | `12345678-9` |
| Phone (LATAM) | `^\+?[0-9]{7,15}$` | `+573001234567` |
| FDI tooth number | `^[1-8][1-8]$` | `18` (upper right third molar) |
| CIE-10 code | `^[A-Z][0-9]{2}(\.[0-9]{1,4})?$` | `K02.1` |
| CUPS code | `^[0-9]{6}$` | `237101` |

---

## 5. SQL Injection Prevention

### Mandatory: SQLAlchemy ORM

All database queries MUST use SQLAlchemy ORM with parameterized queries. **Raw SQL is prohibited** unless explicitly approved in a code review with documented justification.

**Allowed patterns:**

```python
# ORM query (preferred)
patient = await session.execute(
    select(Patient).where(Patient.id == patient_id)
)

# Text query with bound parameters (acceptable when ORM is insufficient)
result = await session.execute(
    text("SELECT * FROM patients WHERE document_number = :doc"),
    {"doc": document_number},
)
```

**Prohibited patterns:**

```python
# NEVER: String formatting in queries
await session.execute(f"SELECT * FROM patients WHERE id = '{patient_id}'")

# NEVER: String concatenation
await session.execute("SELECT * FROM patients WHERE name LIKE '%" + search + "%'")
```

### Schema Isolation as Defense in Depth

The schema-per-tenant architecture (see `infra/multi-tenancy.md`) provides an additional SQL injection defense layer. Even if an injection occurs, the attacker is confined to the current tenant's schema because `search_path` is set at the connection level.

### Linting Enforcement

A custom ruff/pylint rule flags any use of `session.execute()` with f-strings or string concatenation. This is enforced in CI.

---

## 6. XSS Prevention

### Backend (FastAPI)

- All Pydantic response models serialize data as JSON with automatic escaping
- Rich text fields are sanitized on input (bleach) AND escaped on output
- No HTML rendering on the backend; the API is JSON-only
- Error messages never include user-supplied input verbatim

### Frontend (Next.js / React)

- React escapes all interpolated values by default (`{variable}` in JSX)
- `dangerouslySetInnerHTML` is prohibited except in the clinical notes viewer component, which uses DOMPurify client-side
- CSP headers provide defense in depth (see Section 3)
- SVG odontogram rendering uses React components, not innerHTML

### Stored XSS Prevention

- All user-generated content is sanitized on write (bleach) and escaped on read
- Clinical notes are stored as sanitized HTML (limited tags) in the database
- Patient names, addresses, and other text fields are stored as plain text (no HTML allowed)

---

## 7. CSRF Protection

### JWT API (No CSRF Required)

The primary API uses JWT Bearer tokens in the `Authorization` header. Since cookies are not used for authentication on the main API, CSRF protection is not needed.

**Rationale:** CSRF attacks exploit automatic cookie inclusion by browsers. JWT tokens in the `Authorization` header are not automatically included and require explicit JavaScript to attach.

### Patient Portal (Cookie-Based Auth -- CSRF Required)

The patient portal (`portal.dentalos.app`) uses HTTP-only cookies for session management (patients cannot be expected to manage JWT tokens).

**CSRF implementation for portal:**

```python
from starlette.middleware import Middleware
from starlette_csrf import CSRFMiddleware

# Applied only to the portal sub-application
portal_app.add_middleware(
    CSRFMiddleware,
    secret=settings.CSRF_SECRET,
    cookie_name="dentalos_csrf",
    cookie_secure=True,
    cookie_samesite="strict",
    header_name="X-CSRF-Token",
)
```

**Portal CSRF flow:**
1. On page load, the server sets a `dentalos_csrf` cookie (HTTP-only=False so JS can read it)
2. The Next.js frontend reads the cookie and includes it as `X-CSRF-Token` header on state-changing requests (POST, PUT, DELETE)
3. The CSRF middleware validates that the header matches the cookie

---

## 8. PHI (Protected Health Information) Handling

DentalOS handles healthcare data subject to Colombian data protection law (Ley 1581 de 2012), Colombian health records regulation (Resolucion 1995 de 1999, Resolucion 839 de 2017), and privacy frameworks of each target LATAM country.

### Classification of PHI Fields

| Category | Fields | Storage |
|----------|--------|---------|
| **Direct identifiers** | patient name, cedula/CURP/RUT, email, phone, address | Encrypted at application level |
| **Clinical data** | diagnoses (CIE-10), treatments (CUPS), odontogram conditions, clinical notes, prescriptions | Stored in tenant schema; encrypted at rest via PostgreSQL TDE |
| **Billing data** | invoice amounts, payment methods, insurance details | Stored in tenant schema; encrypted at rest |
| **Metadata** | appointment timestamps, login history, audit logs | Stored in tenant schema; encrypted at rest |

### Encryption at Rest

**Layer 1: PostgreSQL Transparent Data Encryption (TDE)**

All tenant schemas are encrypted at the database level using PostgreSQL TDE (available in PostgreSQL 16+). This encrypts the data files on disk, protecting against physical disk theft or unauthorized server access.

**Layer 2: Application-Level Encryption for Sensitive Fields**

Direct identifiers (cedula, name, phone, email, address) are additionally encrypted at the application level using AES-256-GCM before storage. This protects against database administrator access and SQL injection exfiltration.

```python
"""
Application-level field encryption for PHI direct identifiers.
Uses AES-256-GCM with per-tenant encryption keys.
"""
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class PHIEncryptor:
    def __init__(self, master_key: bytes):
        self._master_key = master_key

    def encrypt(self, plaintext: str, tenant_id: str) -> bytes:
        """Encrypt a PHI field. Returns nonce + ciphertext."""
        nonce = os.urandom(12)
        aad = tenant_id.encode()  # Additional authenticated data
        aesgcm = AESGCM(self._master_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), aad)
        return nonce + ciphertext

    def decrypt(self, data: bytes, tenant_id: str) -> str:
        """Decrypt a PHI field."""
        nonce = data[:12]
        ciphertext = data[12:]
        aad = tenant_id.encode()
        aesgcm = AESGCM(self._master_key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
        return plaintext.decode()
```

**Key management:**
- Master encryption key stored in environment variable (`DENTALOS_PHI_MASTER_KEY`)
- Key rotation: annual, with re-encryption migration script
- Future: migrate to HashiCorp Vault or Hetzner Secrets Manager when available

### Encryption in Transit

- All client-to-server communication over TLS 1.3 (see Section 1)
- Database connections over Hetzner private network (encrypted)
- Redis connections over private network (encrypted or TLS if exposed)
- RabbitMQ connections over private network (AMQPS if exposed)

### Minimum Necessary Principle

API endpoints MUST return only the fields required for the specific use case.

| Endpoint | Fields Returned | Fields Excluded |
|----------|----------------|-----------------|
| `GET /patients` (list) | id, name, phone, last_visit, status | full address, medical history, insurance |
| `GET /patients/search` | id, name, document_number, phone | everything else |
| `GET /patients/{id}` (detail) | all patient fields | audit history, internal IDs |
| `GET /patients/{id}/odontogram` | clinical conditions | billing info, personal contact |

### No PHI in Logs, Errors, or URLs

**Logging rules:**
- Log `patient_id` (UUID), never patient name, cedula, or phone
- Log `tenant_id`, never tenant name or admin email
- Log `user_id`, never user email or name
- Clinical data (diagnoses, conditions) MUST NOT appear in application logs
- Exception messages sent to Sentry are scrubbed of PHI before transmission

**Error response rules:**
- Validation errors reference field names, not field values: `"cedula": ["Invalid format"]` not `"cedula": ["1234567890 is invalid"]`
- 404 errors do not distinguish between "does not exist" and "access denied" for patient resources

**URL rules:**
- Patient identifiers in URLs use UUIDs, never document numbers or names
- Query parameters must not contain PHI
- Search queries are sent as POST body (not query string) to avoid logging in server access logs

---

## 9. File Upload Security

### Allowed File Types

| Context | Allowed MIME Types | Max Size | Extensions |
|---------|-------------------|----------|------------|
| X-ray images | `image/jpeg`, `image/png`, `image/dicom` | 25 MB | .jpg, .jpeg, .png, .dcm |
| Intraoral photos | `image/jpeg`, `image/png` | 15 MB | .jpg, .jpeg, .png |
| Documents (consent, lab results) | `application/pdf`, `image/jpeg`, `image/png` | 10 MB | .pdf, .jpg, .jpeg, .png |
| Patient import | `text/csv`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | 5 MB | .csv, .xlsx |
| Profile photos | `image/jpeg`, `image/png` | 2 MB | .jpg, .jpeg, .png |

### Validation Pipeline

```python
"""
File upload validation pipeline.
Every upload passes through these checks in order.
"""
import magic  # python-magic for MIME detection
from pathlib import Path


ALLOWED_MIMES = {
    "xray": {"image/jpeg", "image/png", "application/dicom"},
    "photo": {"image/jpeg", "image/png"},
    "document": {"application/pdf", "image/jpeg", "image/png"},
    "import": {"text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    "avatar": {"image/jpeg", "image/png"},
}

MAX_SIZES = {
    "xray": 25 * 1024 * 1024,       # 25 MB
    "photo": 15 * 1024 * 1024,       # 15 MB
    "document": 10 * 1024 * 1024,    # 10 MB
    "import": 5 * 1024 * 1024,       # 5 MB
    "avatar": 2 * 1024 * 1024,       # 2 MB
}


async def validate_upload(file_bytes: bytes, filename: str, upload_type: str) -> None:
    """
    Validate an uploaded file. Raises ValueError on any check failure.
    """
    # 1. Size check
    max_size = MAX_SIZES.get(upload_type)
    if max_size and len(file_bytes) > max_size:
        raise ValueError(
            f"File exceeds maximum size of {max_size // (1024*1024)} MB"
        )

    # 2. Extension check
    ext = Path(filename).suffix.lower()
    allowed_exts = {".jpg", ".jpeg", ".png", ".pdf", ".csv", ".xlsx", ".dcm"}
    if ext not in allowed_exts:
        raise ValueError(f"File extension {ext} is not allowed")

    # 3. MIME type detection (magic bytes, not extension)
    detected_mime = magic.from_buffer(file_bytes[:2048], mime=True)
    allowed_mimes = ALLOWED_MIMES.get(upload_type, set())
    if detected_mime not in allowed_mimes:
        raise ValueError(
            f"Detected file type {detected_mime} does not match allowed types"
        )

    # 4. Extension-MIME consistency check
    mime_ext_map = {
        "image/jpeg": {".jpg", ".jpeg"},
        "image/png": {".png"},
        "application/pdf": {".pdf"},
        "text/csv": {".csv"},
    }
    expected_exts = mime_ext_map.get(detected_mime, set())
    if expected_exts and ext not in expected_exts:
        raise ValueError("File extension does not match detected file type")

    # 5. Image-specific checks
    if detected_mime.startswith("image/"):
        await _validate_image(file_bytes)


async def _validate_image(file_bytes: bytes) -> None:
    """Additional validation for image files."""
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(file_bytes))

    # Reject images with embedded scripts (e.g., SVG with JS)
    if img.format not in ("JPEG", "PNG"):
        raise ValueError("Only JPEG and PNG images are accepted")

    # Max dimensions (prevent decompression bombs)
    max_pixels = 50_000_000  # 50 megapixels
    if img.size[0] * img.size[1] > max_pixels:
        raise ValueError("Image dimensions exceed maximum allowed")
```

### Virus Scanning

All uploaded files are scanned for malware before storage.

**Implementation:** ClamAV running as a daemon on the application server. Files are scanned via the `clamd` socket before being persisted to S3-compatible storage.

```python
import clamd

async def scan_file(file_bytes: bytes) -> None:
    """Scan file for viruses using ClamAV."""
    cd = clamd.ClamdUnixSocket()
    result = cd.instream(io.BytesIO(file_bytes))
    status = result.get("stream", ("OK",))[0]
    if status != "OK":
        raise ValueError("File failed virus scan")
```

### Storage Security

- Files are stored in S3-compatible storage (Hetzner Object Storage) with tenant-isolated prefixes: `{tenant_id}/{upload_type}/{year}/{month}/{uuid}.{ext}`
- Access via signed URLs with 15-minute expiration (never direct public URLs)
- Bucket policy denies public access
- See `infra/file-storage.md` for full details

---

## 10. Dependency Security

### Automated Vulnerability Scanning

| Tool | Target | Frequency | Enforcement |
|------|--------|-----------|-------------|
| `pip-audit` | Python dependencies | Every CI build + weekly scheduled | Block merge on HIGH/CRITICAL |
| `npm audit` | Node.js dependencies | Every CI build + weekly scheduled | Block merge on HIGH/CRITICAL |
| `safety` | Python dependencies (additional scanner) | Weekly scheduled | Alert on findings |
| `trivy` | Docker images | Every image build | Block deploy on HIGH/CRITICAL |
| Dependabot / Renovate | All dependencies | Continuous | Auto-create PRs for security updates |

### CI Pipeline Integration

```yaml
# .github/workflows/security.yml (excerpt)
security-scan:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Python vulnerability scan
      run: |
        pip install pip-audit
        pip-audit -r requirements.txt --severity HIGH
    - name: Node vulnerability scan
      run: |
        cd frontend
        npm audit --audit-level=high
    - name: Docker image scan
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: dentalos-api:${{ github.sha }}
        severity: HIGH,CRITICAL
        exit-code: 1
```

### Dependency Pinning

- All Python dependencies are pinned with exact versions in `requirements.txt` (generated from `requirements.in` via `pip-compile`)
- All Node.js dependencies use `package-lock.json` with exact versions
- Docker base images use SHA256 digests, not mutable tags

---

## 11. Secrets Management

### Principles

- No secrets in source code, ever
- No secrets in Docker images
- No secrets in logs or error messages
- Secrets rotate on a defined schedule

### Secret Storage

| Environment | Storage Mechanism |
|-------------|-------------------|
| Local development | `.env` file (in `.gitignore`) |
| CI/CD (GitHub Actions) | GitHub Secrets (encrypted) |
| Production (Hetzner) | Environment variables via systemd unit files (mode 0600) |
| Future | HashiCorp Vault or Hetzner Secrets Manager |

### Secrets Inventory

| Secret | Rotation Schedule | Notes |
|--------|-------------------|-------|
| `DATABASE_URL` | On credential change | Contains password |
| `REDIS_URL` | On credential change | Contains password if auth enabled |
| `RABBITMQ_URL` | On credential change | Contains password |
| `JWT_SECRET_KEY` | Quarterly | All active sessions invalidated on rotation |
| `JWT_REFRESH_SECRET_KEY` | Quarterly | Forces re-login on rotation |
| `DENTALOS_PHI_MASTER_KEY` | Annually | Requires re-encryption migration |
| `SENDGRID_API_KEY` | Annually | Email provider key |
| `WHATSAPP_API_TOKEN` | Per Meta policy | Meta Business API token |
| `SENTRY_DSN` | Rarely | Error tracking |
| `CSRF_SECRET` | Quarterly | Patient portal CSRF |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | Semi-annually | Object storage credentials |

### Pre-Commit Hook

A pre-commit hook scans for accidental secret commits.

```yaml
# .pre-commit-config.yaml (excerpt)
- repo: https://github.com/Yelp/detect-secrets
  rev: v1.4.0
  hooks:
    - id: detect-secrets
      args: ['--baseline', '.secrets.baseline']
```

---

## Security Incident Response

### Detection

- Sentry alerts for unusual error patterns (e.g., spike in 401/403 errors)
- Rate limit alerts for brute force patterns (see `infra/rate-limiting.md`)
- Audit log alerts for unusual access patterns (bulk data exports, off-hours access)
- Database query logs for suspicious queries (enabled on staging, sampled in production)

### Response Procedure

1. **Detect:** Automated alerts or manual discovery
2. **Contain:** Suspend affected tenant/user, rotate compromised credentials
3. **Assess:** Review audit logs, determine scope of exposure
4. **Notify:** Notify affected tenants within 72 hours (per Colombian Ley 1581)
5. **Remediate:** Patch vulnerability, deploy fix
6. **Review:** Post-incident review, update security policy if needed

---

## Out of Scope

This spec explicitly does NOT cover:

- Authentication/authorization logic (see `infra/authentication-rules.md`)
- Audit logging implementation (see `infra/audit-logging.md`)
- Network firewall rules and Hetzner security groups (see `infra/deployment-architecture.md`)
- Penetration testing schedule and methodology (operational procedure, not spec)
- SOC 2 or ISO 27001 certification process (future business decision)
- End-to-end encryption for messaging features (see `messages/` spec domain)
- Patient consent management for data processing (see `consents/` spec domain)
- GDPR compliance for EU users (not in scope for LATAM-only launch)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec: transport security, CORS, CSP, input sanitization, injection prevention, PHI handling, file uploads, dependency security, secrets management |
