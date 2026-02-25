# Crear Diagnostico (CR-07)

---

## Overview

**Feature:** Crea un diagnostico clinico para un paciente con codigo CIE-10 validado contra el catalogo. Vincula opcionalmente al diente especifico en el odontograma. Solo doctores pueden crear diagnosticos. Toda escritura es auditada (PHI).

**Domain:** clinical-records

**Priority:** High

**Dependencies:** CR-10 (cie10-search.md), odontogram/tooth-get.md, infra/audit-logging.md, infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor
- **Tenant context:** Required — resuelto desde JWT
- **Special rules:** Exclusivamente para doctores. Los asistentes NO pueden crear diagnosticos. PHI — toda escritura es auditada.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/diagnoses
```

**Rate Limiting:**
- 60 requests por minuto por usuario
- Redis sliding window: `tenant:{tenant_id}:rate:diagnoses_write:{user_id}`

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Formato de request | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto desde JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | Yes | UUID | Debe existir en el tenant | ID del paciente | 550e8400-e29b-41d4-a716-446655440000 |

### Query Parameters

N/A

### Request Body Schema

```json
{
  "cie10_code": "string (required) — codigo CIE-10 valido (ej: K02.1)",
  "description": "string (optional) — descripcion adicional del diagnostico. Si no se provee, se usa la descripcion oficial del catalogo CIE-10",
  "tooth_number": "integer (optional) — numero de diente FDI afectado (11-48)",
  "severity": "string (required) — mild | moderate | severe",
  "status": "string (optional, default: active) — active",
  "notes": "string (optional) — notas clinicas adicionales del doctor"
}
```

**Example Request:**
```json
{
  "cie10_code": "K02.1",
  "description": "Caries de la dentina en diente 16 con cavidad oclusal",
  "tooth_number": 16,
  "severity": "moderate",
  "status": "active",
  "notes": "Caries oclusal profunda. Requiere radiografia periapical previa al tratamiento."
}
```

---

## Response

### Success Response

**Status:** 201 Created

**Schema:**
```json
{
  "id": "UUID",
  "patient_id": "UUID",
  "cie10_code": "string",
  "cie10_description": "string — descripcion oficial del codigo CIE-10 del catalogo (espanol)",
  "custom_description": "string | null — descripcion adicional del doctor si fue provista",
  "tooth_number": "integer | null",
  "tooth_notation_fdi": "string | null — ej: '16'",
  "severity": "string",
  "status": "string",
  "notes": "string | null",
  "doctor": {
    "id": "UUID",
    "name": "string",
    "specialty": "string | null"
  },
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime"
}
```

**Example:**
```json
{
  "id": "dx_d9e8f7a6-b5c4-3210-fedc-ba9876543210",
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "cie10_code": "K02.1",
  "cie10_description": "Caries de la dentina",
  "custom_description": "Caries de la dentina en diente 16 con cavidad oclusal",
  "tooth_number": 16,
  "tooth_notation_fdi": "16",
  "severity": "moderate",
  "status": "active",
  "notes": "Caries oclusal profunda. Requiere radiografia periapical previa al tratamiento.",
  "doctor": {
    "id": "usr_doctor_001",
    "name": "Dra. Ana Martinez",
    "specialty": "Odontologia General"
  },
  "created_at": "2026-02-24T10:30:00Z",
  "updated_at": "2026-02-24T10:30:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Campos requeridos faltantes o codigo CIE-10 invalido (no existe en catalogo).

```json
{
  "error": "invalid_input",
  "message": "Los datos del diagnostico no son validos.",
  "details": {
    "cie10_code": ["El codigo CIE-10 'K99.9' no existe en el catalogo."],
    "severity": ["La severidad es obligatoria. Opciones: mild, moderate, severe."]
  }
}
```

#### 401 Unauthorized
**When:** Token ausente, expirado o invalido.

#### 403 Forbidden
**When:** El usuario no es doctor (assistant, receptionist, etc.).

```json
{
  "error": "forbidden",
  "message": "Solo los doctores pueden crear diagnosticos clinicos."
}
```

#### 404 Not Found
**When:** `patient_id` no existe, o `tooth_number` no corresponde a un diente registrado en el odontograma (validacion opcional).

```json
{
  "error": "not_found",
  "message": "El paciente especificado no existe."
}
```

#### 422 Unprocessable Entity
**When:** Numero de diente fuera del rango FDI valido.

```json
{
  "error": "validation_failed",
  "message": "El numero de diente especificado no es valido.",
  "details": {
    "tooth_number": ["El numero de diente debe estar entre 11 y 48 (numeracion FDI)."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido.

#### 500 Internal Server Error
**When:** Error inesperado al persistir el diagnostico.

---

## Business Logic

**Step-by-step process:**

1. Validar input contra schema Pydantic (`DiagnosisCreateSchema`).
2. Resolver tenant desde JWT. Verificar que el usuario tiene rol `doctor`. Si no: retornar 403.
3. Verificar que `patient_id` existe en el schema del tenant.
4. Si `tooth_number` provisto: verificar que esta en rango FDI (11-48).
5. Validar `cie10_code` contra el catalogo CIE-10 en `public.cie10_catalog` (o via Redis cache). Si no existe: retornar 400 con detalle del codigo invalido.
6. Obtener `cie10_description` oficial del catalogo para el codigo provisto.
7. Si `tooth_number` provisto: verificar si el diente existe en el odontograma del paciente. Si no existe en el odontograma, el diagnostico se crea igualmente (el diente puede no estar aun en el odontograma).
8. Crear el diagnostico en `tenant_{id}.diagnoses` con `doctor_id = current_user.id` y `status = 'active'`.
9. Si `tooth_number` provisto y el diente existe en el odontograma: vincular el diagnostico al diente via `odontogram_diagnoses` (tabla relacional).
10. Registrar entrada de auditoria (action=create, resource=diagnosis, phi=true).
11. Invalidar cache del listado de diagnosticos del paciente.
12. Retornar 201 con el diagnostico creado.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| cie10_code | Requerido. Debe existir en `public.cie10_catalog`. | "El codigo CIE-10 '{code}' no existe en el catalogo." |
| severity | Requerido. Enum: mild, moderate, severe | "La severidad es obligatoria. Opciones: mild, moderate, severe." |
| tooth_number | Opcional. Entero entre 11 y 48 si provisto. | "El numero de diente debe estar entre 11 y 48 (numeracion FDI)." |
| status | Opcional. Solo `active` al crear. | "El estado al crear un diagnostico solo puede ser 'active'." |

**Business Rules:**

- Solo doctores pueden crear diagnosticos. Los asistentes pueden leer diagnosticos pero no crearlos.
- Un mismo paciente puede tener multiples diagnosticos activos del mismo tipo CIE-10 (en dientes diferentes u observaciones distintas).
- El codigo CIE-10 es inmutable despues de la creacion. Si se necesita un codigo diferente, se crea un nuevo diagnostico y se resuelve el anterior (ver CR-09).
- El campo `cie10_description` siempre se obtiene del catalogo oficial, no del usuario. El usuario puede agregar `custom_description` adicional.
- Si el doctor provee `description` en el body, se almacena como `custom_description` (complementa, no reemplaza, la descripcion oficial del catalogo).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| tooth_number provisto pero diente no en odontograma | Crear diagnostico igualmente; no vincular al odontograma; retornar tooth_number pero sin odontogram_id |
| Mismo cie10_code en mismo tooth_number del mismo paciente | Permitido (el doctor puede tener razon clinica para duplicar; no hay restriccion de unicidad) |
| cie10_code en mayusculas vs minusculas | Normalizar a mayusculas antes de validar (K02.1 == k02.1) |
| description provista identica a cie10_description del catalogo | Almacenar en custom_description igualmente sin error |
| status enviado como 'resolved' al crear | Retornar 400 — el status al crear solo puede ser 'active' |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `diagnoses`: INSERT — nuevo diagnostico
- `odontogram_diagnoses`: INSERT (condicional) — vinculo con diente si tooth_number existe en odontograma
- `audit_logs`: INSERT — entrada de auditoria

**Example query (SQLAlchemy):**
```python
# Validar CIE-10 en schema publico
cie10 = await session.scalar(
    select(Cie10Catalog).where(Cie10Catalog.code == body.cie10_code.upper())
)
if not cie10:
    raise Cie10NotFoundException(code=body.cie10_code)

# Crear diagnostico
diagnosis = Diagnosis(
    patient_id=patient_id,
    doctor_id=current_user.id,
    tenant_id=tenant_id,
    cie10_code=cie10.code,
    cie10_description=cie10.description,
    custom_description=body.description,
    tooth_number=body.tooth_number,
    severity=body.severity,
    status="active",
    notes=body.notes,
)
session.add(diagnosis)
await session.flush()

# Vincular al odontograma si el diente existe
if body.tooth_number:
    tooth = await session.scalar(
        select(OdontogramTooth).where(
            OdontogramTooth.patient_id == patient_id,
            OdontogramTooth.tooth_number == body.tooth_number,
        )
    )
    if tooth:
        session.add(OdontogramDiagnosis(
            odontogram_tooth_id=tooth.id,
            diagnosis_id=diagnosis.id,
        ))

await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:diagnoses:list`: DELETE — invalidar listado de diagnosticos del paciente
- `public:cie10:{code}`: GET — lectura desde cache del catalogo CIE-10

**Cache TTL:** N/A para escritura (solo invalidacion del listado)

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| audit | diagnosis.created | { diagnosis_id, patient_id, doctor_id, cie10_code, tooth_number, tenant_id, timestamp } | Siempre al crear |

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** diagnosis
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** Validacion de CIE-10 via Redis cache (catalogo publico compartido entre tenants)
- **Cache key:** `public:cie10:catalog:{code}` (schema publico, no por tenant)
- **TTL:** 3600s (1 hora — catalogo cambia raramente)
- **Invalidation:** Al actualizar el catalogo CIE-10 (operacion de admin)

### Database Performance

**Queries executed:** 3-4 (validar paciente, validar CIE-10, insertar diagnostico, verificar diente en odontograma)

**Indexes required:**
- `diagnoses.(patient_id, tenant_id)` — INDEX compuesto
- `diagnoses.cie10_code` — INDEX
- `diagnoses.tooth_number` — INDEX
- `diagnoses.status` — INDEX
- `public.cie10_catalog.code` — UNIQUE INDEX
- `odontogram_diagnoses.diagnosis_id` — INDEX

**N+1 prevention:** No aplica (creacion de un solo diagnostico).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| cie10_code | Pydantic str + uppercase + strip | Normalizar formato |
| description | Pydantic str + bleach strip_tags | Prevenir XSS en descripciones |
| notes | Pydantic str + bleach strip_tags | Prevenir XSS |
| tooth_number | Pydantic int, rango 11-48 | Prevenir valores fuera de rango |
| severity | Pydantic Literal enum | Prevenir valores arbitrarios |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM con queries parametrizadas. Sin SQL raw.

### XSS Prevention

**Output encoding:** Todos los strings escapados via serializacion Pydantic. Campos de texto sanitizados con bleach al escribir.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `cie10_code` + `cie10_description` (revela condicion medica del paciente), `tooth_number`, `notes`, `severity`

**Audit requirement:** All access logged — toda escritura de diagnostico auditada.

---

## Testing

### Test Cases

#### Happy Path
1. Crear diagnostico con codigo CIE-10 valido
   - **Given:** Doctor autenticado, paciente activo
   - **When:** POST con cie10_code=K02.1, severity=moderate, tooth_number=16
   - **Then:** 201 Created, diagnostico persistido con cie10_description del catalogo, audit log generado

2. Crear diagnostico sin tooth_number
   - **Given:** Doctor autenticado, paciente activo
   - **When:** POST con cie10_code=K05.1 (gingivitis), sin tooth_number
   - **Then:** 201 Created, diagnostico sin diente vinculado

3. Vinculo a odontograma cuando diente existe
   - **Given:** Diente 16 existe en odontograma del paciente
   - **When:** POST con tooth_number=16
   - **Then:** 201 Created, fila creada en odontogram_diagnoses

#### Edge Cases
1. tooth_number no en odontograma
   - **Given:** Diente 48 no en odontograma del paciente
   - **When:** POST con tooth_number=48
   - **Then:** 201 Created, diagnostico creado, sin fila en odontogram_diagnoses

2. cie10_code en minusculas
   - **Given:** Doctor envia cie10_code=k02.1
   - **When:** POST con code en minusculas
   - **Then:** 201 Created, almacenado como K02.1 (normalizado)

3. Mismo diagnostico duplicado en mismo diente
   - **Given:** Diagnostico K02.1 en diente 16 ya existe para el paciente
   - **When:** POST con mismo cie10_code y tooth_number
   - **Then:** 201 Created (se permite duplicar)

#### Error Cases
1. Codigo CIE-10 inexistente
   - **Given:** Doctor autenticado
   - **When:** POST con cie10_code=K99.9 (no existe)
   - **Then:** 400 con detalle del codigo invalido

2. Rol sin permiso (assistant)
   - **Given:** Usuario con rol assistant
   - **When:** POST al endpoint
   - **Then:** 403 Forbidden

3. Severity faltante
   - **Given:** Doctor autenticado
   - **When:** POST sin campo severity
   - **Then:** 400 con detalle de campo requerido

4. tooth_number fuera de rango
   - **Given:** Doctor autenticado
   - **When:** POST con tooth_number=99
   - **Then:** 422 con mensaje de validacion FDI

### Test Data Requirements

**Users:** Doctor activo, asistente activo (para probar 403)

**Patients/Entities:** Paciente activo con odontograma inicializado (diente 16 existente, diente 48 NO existente), catalogo CIE-10 con al menos K02.1 y K05.1

**Catalog:** CIE-10 codes cargados en `public.cie10_catalog` en entorno de test

### Mocking Strategy

- **Redis:** fakeredis para cache del catalogo CIE-10
- **Audit service:** Mock que verifica llamada con PHI=true y cie10_code
- **Odontogram service:** No mockear — acceder directamente a DB de test

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Diagnostico creado con codigo CIE-10 validado contra el catalogo
- [ ] `cie10_description` tomado del catalogo oficial (espanol)
- [ ] Vinculo a odontograma creado cuando diente existe en odontograma
- [ ] Diagnostico creado sin vinculo cuando diente no esta en odontograma
- [ ] Solo doctores pueden crear diagnosticos (403 para otros roles)
- [ ] Audit log generado en cada creacion
- [ ] Cache del listado invalidado
- [ ] Validacion de CIE-10 via Redis cache del catalogo publico
- [ ] All test cases pass
- [ ] Performance targets met (< 400ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verified (PHI)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Busqueda de codigos CIE-10 (ver CR-10)
- Actualizacion de diagnosticos (ver CR-09)
- Listado de diagnosticos (ver CR-08)
- Crear diagnosticos desde el portal del paciente
- Codigos CIAP-2 u otros sistemas de clasificacion

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (doctor only)
- [x] Side effects listed (incluyendo odontogram_diagnoses)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (domain separation)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (doctor only + tenant context)
- [x] Input sanitization defined (Pydantic + bleach + uppercase normalizer)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail para diagnosticos clinicos

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (catalogo publico en Redis)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified (CIE-10 catalog data)
- [x] Mocking strategy for Redis catalog cache
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
