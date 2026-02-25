# CO-08 — Country Compliance Config Spec

## Overview

**Feature:** Return the compliance configuration for the tenant's country. Provides all country-specific requirements that the frontend and other backend services need to enforce: required form fields, accepted document types, medical code systems (CIE-10 version, CUPS, CUMS), data retention rules, invoice system details, regulatory references, and feature availability per country. This is the central registry for the country adapter pattern (ADR-007). Cached 1 hour.

**Domain:** compliance

**Priority:** High (Sprint 1-2 — needed by frontend from day one to enforce country-specific validations)

**Dependencies:** infra/caching.md, ADR-007 (country adapter pattern), tenants/T-01 (tenant creation sets country)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** clinic_owner, doctor, assistant, receptionist (all authenticated roles within a tenant)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Returns config for the tenant's registered country only. superadmin can query any country by passing `?country=CO` override (for admin tooling). Public (unauthenticated) access not allowed — country config is tenant-specific.

---

## Endpoint

```
GET /api/v1/compliance/config
```

**Rate Limiting:**
- Inherits global rate limit (100/min per user) — effectively unlimited in practice since response is heavily cached

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | No | string | Auto-resolved from JWT | tn_abc123 |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| country | No | string | 2-letter ISO 3166-1 alpha-2; only valid for superadmin | Override country (superadmin only) | CO |
| lang | No | string | es | Response language for display labels | es |

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "country": "string — ISO 3166-1 alpha-2",
  "country_name": "string — full country name in Spanish",
  "config_version": "string — semver of this config schema",
  "last_updated": "string (ISO 8601) — when this config was last updated",
  "cached": "boolean — was this response served from cache",

  "required_fields": [
    {
      "field_id": "string — dot-notation path e.g. patient.tipo_documento",
      "module": "string — patients | odontogram | clinical_records | treatment_plans | billing | appointments",
      "label": "string — display label in Spanish",
      "description": "string — why this field is required",
      "is_required": "boolean",
      "is_recommended": "boolean",
      "regulatory_source": "string — e.g. Resolución 1888 Art. 5",
      "validation_rules": [
        {
          "rule": "string — rule type: min_length | max_length | regex | enum | required_if",
          "value": "string | number | array",
          "error_message": "string — user-facing error in Spanish"
        }
      ]
    }
  ],

  "document_types": [
    {
      "code": "string — internal code e.g. CC",
      "label": "string — display name in Spanish",
      "country_code": "string — RIPS/DIAN code for this document type",
      "is_primary": "boolean — primary ID type for this country",
      "validation_regex": "string | null — format validation pattern",
      "min_length": "integer | null",
      "max_length": "integer | null",
      "example": "string"
    }
  ],

  "code_systems": {
    "diagnosis": {
      "system": "string — cie10",
      "version": "string — e.g. CIE-10-ES-2023",
      "label": "string — CIE-10 Modificación Clínica",
      "lookup_endpoint": "string — /api/v1/lookup/cie10",
      "reference_url": "string — MinSalud official source URL"
    },
    "procedures": {
      "system": "string — cups",
      "version": "string — e.g. CUPS-2024",
      "label": "string — Clasificación Única de Procedimientos en Salud",
      "lookup_endpoint": "string — /api/v1/lookup/cups",
      "reference_url": "string"
    },
    "medications": {
      "system": "string — cums",
      "version": "string — e.g. CUMS-2025",
      "label": "string — Código Único de Medicamentos",
      "lookup_endpoint": "string — /api/v1/lookup/cums",
      "reference_url": "string"
    },
    "dental_codes": {
      "system": "string — soc_col_odontologia | fdi | iso3950",
      "version": "string",
      "label": "string",
      "tooth_numbering": "string — FDI | Universal | Palmer",
      "reference_url": "string"
    }
  },

  "retention_rules": {
    "clinical_records_years": "integer — mandatory retention period",
    "images_years": "integer — radiographs, photos",
    "invoices_years": "integer — billing documents",
    "consents_years": "integer — signed consent forms",
    "prescriptions_years": "integer — drug prescriptions",
    "regulatory_source": "string"
  },

  "invoice_system": {
    "system": "string — dian_matias | sat_cfdi | none",
    "is_mandatory": "boolean — false in early rollout phases",
    "provider": "string — MATIAS | SAT | none",
    "document_types": [
      {
        "code": "string — 01",
        "label": "string — Factura de Venta",
        "description": "string"
      }
    ],
    "tax_rates": [
      {
        "tax_code": "string — IVA | ICA | RET_ICA",
        "label": "string",
        "rate": "number — 0.0 to 100.0 (percentage)",
        "applies_to": "string — all | health_services | non_health",
        "note": "string | null"
      }
    ],
    "currency": "string — COP | MXN | USD",
    "currency_symbol": "string — $ | MX$",
    "decimal_places": "integer — 0 for COP, 2 for MXN",
    "thousand_separator": "string — . for COP, , for MXN/USD",
    "setup_required": "boolean — true if clinic must complete setup before use"
  },

  "regulatory_references": [
    {
      "code": "string — short identifier",
      "title": "string — full name of the regulation",
      "authority": "string — issuing authority",
      "effective_date": "string (ISO 8601 date)",
      "deadline": "string (ISO 8601 date) | null",
      "summary": "string — 1-2 sentence summary in Spanish",
      "url": "string | null — official text URL"
    }
  ],

  "feature_availability": {
    "rips_reporting": "boolean",
    "rda_compliance": "boolean",
    "electronic_invoicing": "boolean",
    "digital_prescriptions": "boolean",
    "eps_integration": "boolean — insurers integration",
    "telemedicine_rules": "string | null — special requirements for telemedicine"
  },

  "locale_settings": {
    "default_language": "string — es-CO | es-MX",
    "date_format": "string — DD/MM/YYYY",
    "time_format": "string — 24h | 12h",
    "phone_format": "string — +57 (3XX) XXX-XXXX",
    "phone_prefix": "string — +57",
    "timezone": "string — America/Bogota",
    "address_format": {
      "fields_order": "array[string]",
      "state_label": "string — Departamento | Estado | Provincia",
      "city_label": "string — Municipio | Ciudad",
      "postal_code_label": "string | null",
      "postal_code_required": "boolean"
    }
  }
}
```

**Example (Colombia):**
```json
{
  "country": "CO",
  "country_name": "Colombia",
  "config_version": "1.3.0",
  "last_updated": "2026-01-15T00:00:00Z",
  "cached": true,

  "required_fields": [
    {
      "field_id": "patient.tipo_documento",
      "module": "patients",
      "label": "Tipo de documento de identidad",
      "description": "Requerido por Resolución 1888 para el Registro Dental Automatizado",
      "is_required": true,
      "is_recommended": true,
      "regulatory_source": "Resolución 1888 de 2021, Art. 5, Parágrafo 1",
      "validation_rules": [
        {
          "rule": "enum",
          "value": ["CC", "CE", "TI", "RC", "PA", "AS", "MS", "CD", "SC", "PE", "DE"],
          "error_message": "Seleccione un tipo de documento válido"
        }
      ]
    },
    {
      "field_id": "clinical_record.diagnostico_principal",
      "module": "clinical_records",
      "label": "Diagnóstico principal (CIE-10)",
      "description": "Código CIE-10 del diagnóstico principal de la consulta",
      "is_required": true,
      "is_recommended": true,
      "regulatory_source": "Resolución 1888 de 2021, Art. 9, Numeral 3",
      "validation_rules": [
        {
          "rule": "regex",
          "value": "^[A-Z]\\d{2}(\\.\\d{1,2})?$",
          "error_message": "Ingrese un código CIE-10 válido (e.g. K02.1)"
        }
      ]
    }
  ],

  "document_types": [
    { "code": "CC", "label": "Cédula de Ciudadanía", "country_code": "CC", "is_primary": true, "validation_regex": "^\\d{5,10}$", "min_length": 5, "max_length": 10, "example": "1020304050" },
    { "code": "CE", "label": "Cédula de Extranjería", "country_code": "CE", "is_primary": false, "validation_regex": null, "min_length": 4, "max_length": 12, "example": "123456789" },
    { "code": "TI", "label": "Tarjeta de Identidad", "country_code": "TI", "is_primary": false, "validation_regex": "^\\d{7,11}$", "min_length": 7, "max_length": 11, "example": "10203040506" },
    { "code": "RC", "label": "Registro Civil", "country_code": "RC", "is_primary": false, "validation_regex": null, "min_length": 8, "max_length": 11, "example": "1020304050" },
    { "code": "PA", "label": "Pasaporte", "country_code": "PA", "is_primary": false, "validation_regex": null, "min_length": 5, "max_length": 20, "example": "AB123456" }
  ],

  "code_systems": {
    "diagnosis": {
      "system": "cie10",
      "version": "CIE-10-ES-2023",
      "label": "Clasificación Internacional de Enfermedades 10ª Revisión",
      "lookup_endpoint": "/api/v1/lookup/cie10",
      "reference_url": "https://www.minsalud.gov.co/salud/POS/Paginas/cie-10.aspx"
    },
    "procedures": {
      "system": "cups",
      "version": "CUPS-2024",
      "label": "Clasificación Única de Procedimientos en Salud",
      "lookup_endpoint": "/api/v1/lookup/cups",
      "reference_url": "https://www.minsalud.gov.co/salud/POS/Paginas/cups.aspx"
    },
    "medications": {
      "system": "cums",
      "version": "CUMS-2025",
      "label": "Código Único de Medicamentos",
      "lookup_endpoint": "/api/v1/lookup/cums",
      "reference_url": "https://www.invima.gov.co"
    },
    "dental_codes": {
      "system": "soc_col_odontologia",
      "version": "2022",
      "label": "Sistema de codificación dental - Sociedad Colombiana de Odontología",
      "tooth_numbering": "FDI",
      "reference_url": "https://www.sco.org.co"
    }
  },

  "retention_rules": {
    "clinical_records_years": 10,
    "images_years": 5,
    "invoices_years": 10,
    "consents_years": 10,
    "prescriptions_years": 5,
    "regulatory_source": "Ley 23 de 1981, Art. 34; Resolución 1995 de 1999"
  },

  "invoice_system": {
    "system": "dian_matias",
    "is_mandatory": true,
    "provider": "MATIAS",
    "document_types": [
      { "code": "01", "label": "Factura de Venta", "description": "Factura electrónica de venta estándar" },
      { "code": "02", "label": "Nota Débito", "description": "Documento de ajuste al alza" },
      { "code": "03", "label": "Nota Crédito", "description": "Documento de ajuste a la baja / devolución" }
    ],
    "tax_rates": [
      { "tax_code": "IVA", "label": "Impuesto al Valor Agregado", "rate": 0.0, "applies_to": "health_services", "note": "Servicios de salud exentos de IVA per DIAN Concepto 022894/2010" },
      { "tax_code": "IVA", "label": "Impuesto al Valor Agregado", "rate": 19.0, "applies_to": "non_health", "note": "Aplica a productos no médicos (cosméticos, artículos dentales no terapéuticos)" },
      { "tax_code": "RET_ICA", "label": "Retención de ICA", "rate": 0.966, "applies_to": "all", "note": "Varía por municipio; tasa de Bogotá: 9.66 por mil" }
    ],
    "currency": "COP",
    "currency_symbol": "$",
    "decimal_places": 0,
    "thousand_separator": ".",
    "setup_required": true
  },

  "regulatory_references": [
    {
      "code": "RES1888",
      "title": "Resolución 1888 de 2021 — Registro Dental Automatizado",
      "authority": "Ministerio de Salud y Protección Social de Colombia",
      "effective_date": "2021-06-15",
      "deadline": "2026-04-01",
      "summary": "Establece el Registro Dental Automatizado (RDA) y los requisitos de historia clínica odontológica digital. Plazo de implementación: 1 de abril de 2026.",
      "url": "https://www.minsalud.gov.co/Normatividad_Nuevo/Resolucion%201888%20de%202021.pdf"
    },
    {
      "code": "RIPS2023",
      "title": "Resolución MSPS 256 de 2016 (actualizada) — RIPS",
      "authority": "Ministerio de Salud",
      "effective_date": "2016-07-05",
      "deadline": null,
      "summary": "Define el Registro Individual de Prestación de Servicios (RIPS). Reporte mensual obligatorio para IPS habilitadas.",
      "url": "https://www.minsalud.gov.co"
    },
    {
      "code": "LEY527",
      "title": "Ley 527 de 1999 — Firmas Digitales",
      "authority": "Congreso de Colombia",
      "effective_date": "1999-08-18",
      "deadline": null,
      "summary": "Marco legal para el comercio electrónico y las firmas digitales en Colombia. Otorga validez legal a las firmas electrónicas.",
      "url": "https://www.secretariasenado.gov.co/senado/basedoc/ley_0527_1999.html"
    }
  ],

  "feature_availability": {
    "rips_reporting": true,
    "rda_compliance": true,
    "electronic_invoicing": true,
    "digital_prescriptions": true,
    "eps_integration": false,
    "telemedicine_rules": "Resolución 2654 de 2019 aplica para teleconsultas; requiere consentimiento informado específico"
  },

  "locale_settings": {
    "default_language": "es-CO",
    "date_format": "DD/MM/YYYY",
    "time_format": "12h",
    "phone_format": "+57 (3XX) XXX-XXXX",
    "phone_prefix": "+57",
    "timezone": "America/Bogota",
    "address_format": {
      "fields_order": ["street", "neighborhood", "city", "state", "postal_code"],
      "state_label": "Departamento",
      "city_label": "Municipio",
      "postal_code_label": "Código Postal",
      "postal_code_required": false
    }
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** `country` query param provided by a non-superadmin caller.

**Example:**
```json
{
  "error": "forbidden_override",
  "message": "Country override is only available for superadmin",
  "details": {}
}
```

#### 401 Unauthorized
**When:** Missing or expired JWT token — see `infra/authentication-rules.md`.

#### 404 Not Found
**When:** Country configuration does not exist for tenant's country (unsupported country).

**Example:**
```json
{
  "error": "country_not_supported",
  "message": "No compliance configuration found for country: AR",
  "details": {
    "country": "AR",
    "supported_countries": ["CO", "MX"]
  }
}
```

#### 422 Unprocessable Entity
**When:** Invalid `country` or `lang` query parameter format.

#### 429 Too Many Requests
**When:** Rate limit exceeded (extremely rare given heavy caching). See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Country config file corrupted or missing; Redis failure.

---

## Business Logic

**Step-by-step process:**

1. Resolve tenant_id and JWT claims (including role).
2. Determine target country:
   - For non-superadmin: use `tenant.country` from JWT claims.
   - For superadmin with `?country=CO` override: use provided country code.
   - If `country` provided by non-superadmin: return 400.
3. Check cache: `global:compliance_config:{country}:{lang}` — if hit, return cached (set `cached=true`).
4. On cache miss, load config via `CountryComplianceConfigLoader.load(country, lang)`:
   - Reads from `compliance_configs` table (country-specific config rows managed by superadmin).
   - Alternatively, loads from versioned config YAML files bundled with the application.
5. Validate config completeness (schema check).
6. Set cache: `global:compliance_config:{country}:{lang}` TTL 3600s.
7. Add `cached: false` to response (first call after cache miss).
8. Return 200 OK.

**Country Adapter Pattern (ADR-007):**
- Each country has a `CountryComplianceConfig` Python class that implements `ICountryConfig` interface.
- Currently implemented: `ColombiaComplianceConfig`, `MexicoComplianceConfig` (stub).
- New countries added by creating a new class + DB config rows; no code changes required for config-only changes.
- The config returned by this endpoint is the same config used internally by CO-01 through CO-07 workers.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| country (query) | 2-letter ISO 3166-1 alpha-2 if provided | "country must be a 2-letter ISO country code" |
| lang | Must be 'es' (only language supported in v1) | "Only 'es' language is supported" |

**Business Rules:**

- This endpoint is the single source of truth for country compliance requirements consumed by all frontend forms and validation logic.
- Frontend should request this config on app load and cache it locally in the session (or local storage with a 1h TTL to match server cache).
- `required_fields` drives dynamic form validation: if a field is listed as `is_required=true`, the frontend must enforce it at form submission.
- `document_types` drives the document type dropdown in patient registration.
- `code_systems.tooth_numbering` determines whether the odontogram uses FDI (Colombia) or Universal (US) notation.
- Config version (`config_version`) allows the frontend to detect when the config has changed and invalidate its local cache.
- The `regulatory_references` array is used to populate the compliance help section of the app.
- Tax rates in `invoice_system.tax_rates` are informational; actual tax calculation is done server-side in the billing module.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Tenant is on a plan that does not include electronic invoicing | invoice_system.is_mandatory=true still applies (legal, not plan-based); but the setup_required flag guides the UI |
| Country with no regulatory deadline | regulatory_references entry shows deadline=null; no urgency banners shown in UI |
| Superadmin queries non-existent country | 404 with supported_countries list |
| Mexico (partial implementation) | Returns full Mexico config structure with some feature_availability fields set to false |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- None — read-only

**Public schema tables affected:**
- `compliance_configs`: SELECT (read config rows by country)

### Cache Operations

**Cache keys affected:**
- `global:compliance_config:{country}:{lang}`: SET on cache miss

**Cache TTL:** 3600 seconds (1 hour)
- Cache is global (not tenant-namespaced) since config is country-level, not tenant-level
- Cache invalidated by superadmin when config is updated via admin endpoint

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None — pure read endpoint.

### Audit Log

**Audit entry:** No — this is a config/reference endpoint with no PHI, logged at DEBUG level only.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 30ms (cache hit — the dominant case)
- **Maximum acceptable:** < 200ms (cache miss requiring DB read)

### Caching Strategy
- **Strategy:** Global Redis cache (not tenant-namespaced, since config is country-level)
- **Cache key:** `global:compliance_config:{country}:{lang}` (e.g., `global:compliance_config:CO:es`)
- **TTL:** 3600 seconds
- **Invalidation:** Superadmin triggers cache invalidation via `DELETE global:compliance_config:{country}:*` when config is updated

### Database Performance

**Queries executed:** 1 (fetch config rows by country) or 0 (cache hit)

**Indexes required:**
- `compliance_configs.(country, lang)` — UNIQUE INDEX

**N+1 prevention:** Full config loaded in one query (denormalized JSON column or ORM with eager loading).

### Pagination

**Pagination:** No (single config object per country)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| country | Pydantic Literal from supported countries list; uppercase enforced | Prevents injection |
| lang | Pydantic Literal from supported languages | Prevents injection |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** All string outputs escaped via Pydantic serialization.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — country configuration contains no patient data.

**Audit requirement:** Not required (not PHI, not write operation).

---

## Testing

### Test Cases

#### Happy Path
1. Colombian tenant gets Colombia config
   - **Given:** Any authenticated role JWT, tenant.country=CO
   - **When:** GET /api/v1/compliance/config
   - **Then:** 200 OK, country=CO, all 41 required_fields present, document_types includes CC/CE/TI/RC/PA, code_systems includes cie10/cups/cums

2. Cache hit
   - **Given:** Config already cached
   - **When:** GET /api/v1/compliance/config (second call)
   - **Then:** 200 OK, cached=true, response time < 30ms

3. Superadmin country override
   - **Given:** superadmin JWT
   - **When:** GET /api/v1/compliance/config?country=MX
   - **Then:** 200 OK, country=MX config returned

4. Doctor can access config
   - **Given:** doctor JWT
   - **When:** GET /api/v1/compliance/config
   - **Then:** 200 OK (all roles can read config)

#### Edge Cases
1. Unsupported country (superadmin query)
   - **Given:** superadmin JWT
   - **When:** GET ?country=AR
   - **Then:** 404 Not Found, supported_countries listed

2. Config cache miss after cache invalidation
   - **Given:** Cache key deleted by superadmin
   - **When:** GET /api/v1/compliance/config
   - **Then:** 200 OK, cached=false, config reloaded from DB

#### Error Cases
1. Non-superadmin uses country override
   - **Given:** doctor JWT
   - **When:** GET ?country=MX
   - **Then:** 400 Bad Request, "Country override is only available for superadmin"

2. Unauthenticated request
   - **Given:** No Authorization header
   - **When:** GET /api/v1/compliance/config
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** clinic_owner, doctor, receptionist, superadmin

**Patients/Entities:** Colombia config in `compliance_configs` table; Mexico config stub

### Mocking Strategy

- Redis: Use fakeredis; test both cache-hit and miss paths
- Config loader: Use fixture YAML files in test environment

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns correct country config for tenant's country
- [ ] All sections populated: required_fields, document_types, code_systems, retention_rules, invoice_system, regulatory_references, feature_availability, locale_settings
- [ ] Colombia config has all 41 RDA required fields listed
- [ ] Tooth numbering system = FDI for Colombia
- [ ] Redis cache used (1h TTL)
- [ ] Superadmin can override country with ?country= param
- [ ] Non-superadmin using ?country= returns 400
- [ ] Unsupported country returns 404 with supported_countries
- [ ] All authenticated roles can access (not just clinic_owner)
- [ ] All test cases pass
- [ ] Performance target: < 30ms cached
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Updating country config (superadmin admin panel operation)
- Lookup endpoints for CIE-10/CUPS/CUMS code search (separate lookup specs)
- Country-specific UI themes or translations (i18n module)
- Patient-facing country config (portal uses simplified subset)
- Multi-country tenants (a single tenant belongs to one country)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (role + tenant)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (domain separation)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (global 1h TTL)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy for external services
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
