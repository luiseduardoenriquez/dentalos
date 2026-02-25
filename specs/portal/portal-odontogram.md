# PP-13 Portal Odontogram Spec

---

## Overview

**Feature:** Patient views their own odontogram from the portal in a simplified, read-only format. Color-coded by condition with an educational legend explaining each condition in plain Spanish. Each tooth includes educational tooltips describing its condition and what it means for the patient. Does not expose clinical codes (ICD/CIE-10) or internal procedure notes.

**Domain:** portal

**Priority:** Medium

**Dependencies:** PP-01 (portal-login.md), odontogram domain (OD-01 through OD-12), infra/multi-tenancy.md

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** patient (portal scope only)
- **Tenant context:** Required — resolved from JWT
- **Special rules:** Portal-scoped JWT required (scope=portal). Patient sees only their own odontogram — query enforced by patient_id = jwt.sub.

---

## Endpoint

```
GET /api/v1/portal/odontogram
```

**Rate Limiting:**
- 30 requests per minute per patient

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer portal JWT token (scope=portal) | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

None.

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| locale | No | string | enum: es, es-CO; default: es-CO | Language for educational content | es-CO |

### Request Body Schema

None. GET request.

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "dentition_type": "string — enum: adult, pediatric, mixed",
  "last_updated_at": "string (ISO 8601 datetime) | null",
  "summary": {
    "teeth_with_conditions": "integer — count of teeth with at least one condition",
    "total_teeth": "integer — total teeth in this dentition type (32 adult, 20 pediatric)",
    "healthy_teeth": "integer",
    "conditions_found": "string[] — distinct condition types present, human-readable"
  },
  "teeth": [
    {
      "number": "string — FDI notation, e.g. '11', '21', '38'",
      "label": "string — friendly name, e.g. 'Incisivo central superior derecho'",
      "quadrant": "integer — 1, 2, 3, or 4",
      "status": "string — enum: healthy, has_conditions, missing, extracted, implant",
      "display_color": "string — hex color for UI rendering, e.g. '#22C55E' (green=healthy)",
      "conditions": [
        {
          "code": "string — simplified condition code, e.g. 'CAVITY', 'CROWN', 'ROOT_CANAL'",
          "label": "string — friendly label, e.g. 'Caries'",
          "surface": "string | null — tooth surface affected: mesial, distal, occlusal, buccal, lingual, or null if whole tooth",
          "surface_label": "string | null — friendly surface name in Spanish",
          "color": "string — hex color for this condition on the tooth",
          "tooltip": "string — educational explanation in plain Spanish (max 300 chars)"
        }
      ]
    }
  ],
  "legend": [
    {
      "code": "string — condition code",
      "label": "string — condition name",
      "color": "string — hex color",
      "description": "string — plain-language educational description (max 400 chars)",
      "icon": "string | null — optional icon name from design system"
    }
  ],
  "educational_note": "string — general message from clinic about the odontogram view"
}
```

**Example:**
```json
{
  "dentition_type": "adult",
  "last_updated_at": "2026-02-15T10:30:00-05:00",
  "summary": {
    "teeth_with_conditions": 3,
    "total_teeth": 32,
    "healthy_teeth": 29,
    "conditions_found": ["Caries", "Corona", "Diente ausente"]
  },
  "teeth": [
    {
      "number": "11",
      "label": "Incisivo central superior derecho",
      "quadrant": 1,
      "status": "healthy",
      "display_color": "#22C55E",
      "conditions": []
    },
    {
      "number": "21",
      "label": "Incisivo central superior izquierdo",
      "quadrant": 2,
      "status": "has_conditions",
      "display_color": "#F59E0B",
      "conditions": [
        {
          "code": "ROOT_CANAL",
          "label": "Tratamiento de conducto",
          "surface": null,
          "surface_label": null,
          "color": "#8B5CF6",
          "tooltip": "Este diente ha recibido un tratamiento de conducto (endodoncia). El nervio fue removido y el diente fue sellado. El diente puede seguir funcionando normalmente despues del tratamiento."
        }
      ]
    },
    {
      "number": "46",
      "label": "Primer molar inferior derecho",
      "quadrant": 4,
      "status": "has_conditions",
      "display_color": "#EF4444",
      "conditions": [
        {
          "code": "CAVITY",
          "label": "Caries",
          "surface": "occlusal",
          "surface_label": "Superficie oclusal (cara masticadora)",
          "color": "#EF4444",
          "tooltip": "Se ha detectado una caries en la superficie oclusal de este diente. Una caries es una infeccion bacteriana que destruye el esmalte del diente. Requiere tratamiento oportuno para evitar que progrese."
        }
      ]
    },
    {
      "number": "38",
      "label": "Tercer molar inferior izquierdo (muela del juicio)",
      "quadrant": 3,
      "status": "extracted",
      "display_color": "#6B7280",
      "conditions": [
        {
          "code": "EXTRACTED",
          "label": "Diente extraido",
          "surface": null,
          "surface_label": null,
          "color": "#6B7280",
          "tooltip": "Este diente fue extraido. La extraccion dental es un procedimiento comun, especialmente para las muelas del juicio que causan problemas."
        }
      ]
    }
  ],
  "legend": [
    {
      "code": "HEALTHY",
      "label": "Sano",
      "color": "#22C55E",
      "description": "El diente no presenta condiciones reportadas en este momento.",
      "icon": "tooth-healthy"
    },
    {
      "code": "CAVITY",
      "label": "Caries",
      "color": "#EF4444",
      "description": "Una caries es una lesion causada por bacterias que descomponen el esmalte dental. Puede tratarse con una limpieza y obturacion (empaste).",
      "icon": "tooth-cavity"
    },
    {
      "code": "CROWN",
      "label": "Corona",
      "color": "#F59E0B",
      "description": "Una corona es una funda que cubre y protege un diente danade o debilitado. Restaura su forma, tamano y funcion.",
      "icon": "tooth-crown"
    },
    {
      "code": "ROOT_CANAL",
      "label": "Tratamiento de conducto",
      "color": "#8B5CF6",
      "description": "El tratamiento de conducto (endodoncia) elimina la pulpa infectada del interior del diente. Permite conservar el diente natural y aliviar el dolor.",
      "icon": "tooth-root-canal"
    },
    {
      "code": "EXTRACTED",
      "label": "Diente extraido",
      "color": "#6B7280",
      "description": "El diente fue removido. Su odontologo puede recomendarle una protesis, implante o puente para reemplazar el diente perdido.",
      "icon": "tooth-extracted"
    },
    {
      "code": "IMPLANT",
      "label": "Implante",
      "color": "#3B82F6",
      "description": "Un implante dental es una raiz artificial de titanio sobre la que se coloca una corona. Es la opcion mas parecida a un diente natural.",
      "icon": "tooth-implant"
    },
    {
      "code": "FILLING",
      "label": "Obturacion (empaste)",
      "color": "#10B981",
      "description": "Una obturacion o empaste rellena el espacio dejado por una caries u otro dano. El material usado puede ser composite (blanco) o amalgama.",
      "icon": "tooth-filling"
    }
  ],
  "educational_note": "Este odontograma es una representacion simplificada del estado de su boca segun la ultima revision de su odontologo. Para mayor informacion sobre cualquier condicion, consulte directamente con su clinica."
}
```

### Error Responses

#### 400 Bad Request
**When:** Invalid locale parameter.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Parametros de consulta no validos.",
  "details": {
    "locale": ["Idioma no valido. Opciones: es, es-CO."]
  }
}
```

#### 401 Unauthorized
**When:** Missing, expired, or invalid portal JWT.

#### 403 Forbidden
**When:** JWT scope is not "portal" or role is not "patient".

#### 404 Not Found
**When:** Patient does not have an odontogram initialized (should not occur in normal flow; odontogram is auto-created with patient record).

**Example:**
```json
{
  "error": "odontogram_not_found",
  "message": "No se encontro el odontograma. Por favor contacte a su clinica."
}
```

#### 429 Too Many Requests
**When:** Rate limit exceeded. See `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Unexpected database failure.

---

## Business Logic

**Step-by-step process:**

1. Validate portal JWT (scope=portal, role=patient). Extract patient_id, tenant_id.
2. Validate locale parameter (optional; default es-CO).
3. Resolve tenant schema; set `search_path`.
4. Fetch odontogram state: `SELECT * FROM odontogram_states WHERE patient_id = :patient_id`. If not found → 404.
5. Fetch all tooth conditions: `SELECT * FROM odontogram_tooth_conditions WHERE odontogram_id = :odontogram_id AND is_deleted = false ORDER BY tooth_number, created_at DESC`.
6. Build tooth map for all teeth in dentition (32 for adult, 20 for pediatric, 28 for mixed — excluding wisdom teeth in mixed):
   - For each tooth: determine status based on conditions.
   - Map conditions to simplified portal codes (see Condition Code Mapping below).
   - Assign display_color based on worst condition (priority: extracted > cavity > root_canal > crown > filling > healthy).
7. Generate educational tooltip for each condition using locale-specific text (static mapping, no DB lookup needed).
8. Build legend: all possible condition types in this dentition's context (always include all standard types regardless of what patient has).
9. Compute summary:
   - `teeth_with_conditions`: COUNT(teeth WHERE conditions.length > 0)
   - `healthy_teeth`: total_teeth - teeth_with_conditions - missing/extracted
   - `conditions_found`: distinct condition labels from all teeth
10. Fetch `tenant_settings.portal_odontogram_note` for `educational_note` (or use default if not configured).
11. Cache result.
12. Return 200.

**Condition Code Mapping (Internal → Portal):**

| Internal Code | Portal Code | Portal Label | Display Color |
|---------------|-------------|--------------|---------------|
| CARIES | CAVITY | Caries | #EF4444 |
| OBTURACION | FILLING | Obturacion (empaste) | #10B981 |
| CORONA | CROWN | Corona | #F59E0B |
| ENDODONCIA | ROOT_CANAL | Tratamiento de conducto | #8B5CF6 |
| EXTRACCION | EXTRACTED | Diente extraido | #6B7280 |
| IMPLANTE | IMPLANT | Implante | #3B82F6 |
| PROTESIS_FIJA | BRIDGE | Puente dental | #F97316 |
| FRACTURA | FRACTURE | Fractura | #DC2626 |
| FUSION | FUSION | Fusion dental | #7C3AED |
| SANO | HEALTHY | Sano | #22C55E |

**Excluded from portal view (internal codes NOT shown to patient):**
- Internal procedure planning notes
- ICD-10 / CIE-10 diagnostic codes
- Staff annotations and observations
- Mobility scores, furcation, and periodontal charting details (future clinical data)
- Cost or billing codes associated with conditions

**Business Rules:**

- All 32 adult teeth are always included in the response (empty conditions array for healthy/unreported teeth).
- FDI numbering used consistently (11-18, 21-28, 31-38, 41-48 for adult).
- `display_color` represents the most clinically significant condition on the tooth (red=cavity priority over green=healthy).
- Educational tooltips are static, locale-aware strings (no DB lookup; baked into service code).
- The portal odontogram is read-only — patients cannot annotate or modify.
- Pediatric dentition uses letters (A-T, FDI 51-55, 61-65, 71-75, 81-85) with friendly names.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| No conditions recorded (brand new patient) | All 32 teeth show as healthy, conditions=[] per tooth |
| Mixed dentition patient (age 6-11) | Mixed tooth set; deciduous and permanent teeth shown |
| Tooth with multiple conditions | All conditions listed; display_color from highest-priority condition |
| Odontogram never updated (last_updated_at=null) | Show all teeth healthy; last_updated_at=null in response |
| Extracted tooth | status='extracted', display_color='#6B7280', condition=[EXTRACTED] |

---

## Side Effects

### Database Changes

None. Read-only endpoint.

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:portal:patient:{patient_id}:odontogram`: SET — cached odontogram response, TTL 10 minutes

**Cache TTL:** 10 minutes (odontogram changes only when clinician records a procedure; infrequent enough for longer cache)

**Cache invalidation triggers:**
- Odontogram condition recorded or updated by clinic staff
- Odontogram state reset or dentition type changed

### Queue Jobs (RabbitMQ)

None.

### Audit Log

**Audit entry:** Yes — see infra/audit-logging.md

**If Yes:**
- **Action:** read
- **Resource:** portal_odontogram
- **PHI involved:** Yes (dental health conditions are clinical PHI)

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 100ms (with cache hit — tooth data is static between visits)
- **Maximum acceptable:** < 250ms (cache miss, full tooth map computation)

### Caching Strategy
- **Strategy:** Redis cache, patient-namespaced, 10-minute TTL
- **Cache key:** `tenant:{tenant_id}:portal:patient:{patient_id}:odontogram`
- **TTL:** 10 minutes
- **Invalidation:** On any change to patient's odontogram conditions

### Database Performance

**Queries executed:** 2 (odontogram_states fetch; tooth_conditions fetch with ORDER BY)

**Indexes required:**
- `odontogram_states.patient_id` — UNIQUE INDEX (one per patient)
- `odontogram_tooth_conditions.(odontogram_id, tooth_number)` — COMPOSITE INDEX
- `odontogram_tooth_conditions.is_deleted` — INDEX (filter soft-deleted)

**N+1 prevention:** Single query fetches all conditions; tooth map built in-memory.

### Pagination

**Pagination:** No (all teeth always returned in one response; max 32 teeth, manageable payload)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| locale | Pydantic Literal enum ('es', 'es-CO') | Strict allowlist |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. patient_id from validated JWT sub claim.

### XSS Prevention

**Output encoding:** All string outputs escaped by Pydantic serialization. Educational tooltip strings are static server-side content (not user-supplied).

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF not applicable for API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Dental conditions per tooth (health status is clinical PHI)

**Audit requirement:** Access logged (PHI read — Resolución 1888 compliance for clinical record patient access)

---

## Testing

### Test Cases

#### Happy Path
1. Adult patient with conditions on 3 teeth
   - **Given:** Patient with adult dentition, 3 teeth with conditions (cavity, crown, extraction)
   - **When:** GET /api/v1/portal/odontogram
   - **Then:** 200 OK, 32 teeth returned, 3 with conditions, legend complete, educational tooltips populated

2. Brand new patient (no conditions)
   - **Given:** Patient just created, odontogram initialized but no conditions recorded
   - **When:** GET /api/v1/portal/odontogram
   - **Then:** 200 OK, all 32 teeth healthy, summary.healthy_teeth=32, conditions_found=[]

3. Pediatric patient
   - **Given:** Patient age 4, dentition_type=pediatric
   - **When:** GET /api/v1/portal/odontogram
   - **Then:** 20 teeth with deciduous FDI numbering; pediatric-appropriate labels

4. Cached response on second request
   - **Given:** Patient fetches odontogram twice within 10 minutes
   - **When:** Second GET
   - **Then:** Served from Redis cache; no DB query

5. Tooth with multiple conditions
   - **Given:** Tooth 21 has both ROOT_CANAL and CROWN
   - **When:** GET /api/v1/portal/odontogram
   - **Then:** Tooth 21 shows both conditions in conditions array; display_color from highest-priority (CROWN)

#### Edge Cases
1. Extracted wisdom tooth
   - **Given:** Tooth 38 has EXTRACCION condition
   - **When:** GET /api/v1/portal/odontogram
   - **Then:** Tooth 38 status='extracted', display_color='#6B7280', tooltip about extraction

2. Internal diagnostic codes not exposed
   - **Given:** Tooth condition has ICD-10 code K02.1 stored internally
   - **When:** GET /api/v1/portal/odontogram
   - **Then:** Response shows portal label "Caries" only; no ICD code in response

3. locale parameter
   - **Given:** Patient requests locale=es
   - **When:** GET /api/v1/portal/odontogram?locale=es
   - **Then:** 200 OK with es locale content (currently same as es-CO for MVP)

#### Error Cases
1. Staff JWT on portal endpoint
   - **Given:** Doctor JWT (scope=staff)
   - **When:** GET /api/v1/portal/odontogram
   - **Then:** 403 Forbidden

2. Odontogram not initialized
   - **Given:** Patient record exists but odontogram_states row missing (data integrity issue)
   - **When:** GET /api/v1/portal/odontogram
   - **Then:** 404 odontogram_not_found; alert logged to Sentry

3. Invalid locale
   - **Given:** Patient authenticated
   - **When:** GET /api/v1/portal/odontogram?locale=fr
   - **Then:** 400 Bad Request

### Test Data Requirements

**Users:** Patient with portal_access=true; adult dentition with 3 teeth with various conditions; pediatric patient for dentition test.

**Patients/Entities:** Odontogram states and tooth conditions; conditions with internal ICD codes to verify they are excluded.

### Mocking Strategy

- Redis: fakeredis (verify 10-minute TTL is set)
- Educational tooltip strings: static content; verify correct locale selection
- Condition mapping: fixture with all 10 condition types

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Patient sees simplified odontogram with all teeth in their dentition type
- [ ] Each tooth shows status, display_color, and conditions array
- [ ] Conditions mapped to portal-friendly codes and labels (not internal clinical codes)
- [ ] ICD/CIE-10 codes never exposed in response
- [ ] Educational tooltip for each condition in plain Spanish
- [ ] Full legend always included (all condition types)
- [ ] Summary block (counts) accurate
- [ ] educational_note from tenant settings or default shown
- [ ] Pediatric (20 teeth) and adult (32 teeth) dentition handled correctly
- [ ] Response cached for 10 minutes; invalidated on odontogram update
- [ ] PHI access audited
- [ ] Staff JWT returns 403
- [ ] All test cases pass
- [ ] Performance targets met (< 100ms cache hit, < 250ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Interactive odontogram (clicking to add/modify conditions — clinic staff only)
- Periodontal charting view (clinical detail not suitable for patient portal MVP)
- Historical odontogram snapshots (timeline view — future enhancement)
- 3D or animated tooth views (future enhancement)
- DICOM integration for X-rays in odontogram (see PP-07 for X-ray documents)
- Automated condition detection from X-ray AI (AI add-on, separate spec)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined
- [x] All outputs defined (full tooth + legend schema)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit
- [x] Side effects listed
- [x] Examples provided (complete with legend)

### Hook 2: Architecture Compliance
- [x] Follows service boundaries
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (patient portal scope)
- [x] Input sanitization defined (locale enum only)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Internal codes excluded from response
- [x] Audit trail for clinical PHI access

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 100ms cache hit)
- [x] Caching strategy stated (10-minute TTL, patient-namespaced)
- [x] DB queries optimized (in-memory tooth map; single conditions query)
- [x] Pagination N/A (all 32 teeth always returned)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry for missing odontogram)
- [x] Queue job monitoring (N/A)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy (fakeredis, static tooltip fixtures)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
