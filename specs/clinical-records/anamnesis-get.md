# Obtener Anamnesis (CR-06)

---

## Overview

**Feature:** Obtiene la anamnesis actual del paciente con su historial de cambios resumido. Retorna la version mas reciente con metadatos de auditoria. Toda lectura de PHI es auditada.

**Domain:** clinical-records

**Priority:** High

**Dependencies:** CR-05 (anamnesis-create.md), infra/audit-logging.md, infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant, receptionist
- **Tenant context:** Required — resuelto desde JWT
- **Special rules:** La recepcionista tiene acceso de solo lectura. Toda lectura de PHI es auditada.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/anamnesis
```

**Rate Limiting:**
- 120 requests por minuto por usuario
- Redis sliding window: `tenant:{tenant_id}:rate:anamnesis_read:{user_id}`

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto desde JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| patient_id | Yes | UUID | Debe existir en el tenant | ID del paciente | 550e8400-e29b-41d4-a716-446655440000 |

### Query Parameters

N/A

### Request Body Schema

N/A (GET request)

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "id": "UUID",
  "patient_id": "UUID",
  "version": "integer — version actual de la anamnesis",
  "current_medications": [
    {
      "name": "string",
      "dose": "string | null",
      "frequency": "string | null",
      "since": "string | null"
    }
  ],
  "allergies": [
    {
      "allergen": "string",
      "type": "string | null",
      "severity": "string | null",
      "reaction": "string | null"
    }
  ],
  "chronic_conditions": [
    {
      "condition": "string",
      "cie10_code": "string | null",
      "since": "string | null",
      "controlled": "boolean | null",
      "treatment": "string | null"
    }
  ],
  "surgical_history": [
    {
      "procedure": "string",
      "year": "integer | null",
      "complications": "string | null"
    }
  ],
  "family_history": {
    "diabetes": "boolean | null",
    "hypertension": "boolean | null",
    "cancer": "boolean | null",
    "heart_disease": "boolean | null",
    "bleeding_disorders": "boolean | null",
    "notes": "string | null"
  },
  "habits": {
    "smoking": { "status": "string | null", "packs_per_day": "number | null", "years": "integer | null" },
    "alcohol": { "status": "string | null", "drinks_per_week": "integer | null" },
    "recreational_drugs": { "status": "string | null", "substances": "array<string> | null" },
    "physical_activity": "string | null"
  },
  "pregnancy_status": "string | null",
  "pregnancy_weeks": "integer | null",
  "blood_type": "string | null",
  "rh_factor": "string | null",
  "country_specific": "object",
  "notes": "string | null",
  "allergies_alert": "boolean",
  "completed_by": {
    "id": "UUID",
    "name": "string",
    "role": "string"
  },
  "change_history": [
    {
      "version": "integer",
      "updated_at": "ISO8601 datetime",
      "updated_by": {
        "id": "UUID",
        "name": "string",
        "role": "string"
      }
    }
  ],
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime"
}
```

**Example:**
```json
{
  "id": "ana_7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "version": 3,
  "current_medications": [
    {
      "name": "Losartan",
      "dose": "50mg",
      "frequency": "1 vez al dia",
      "since": "2022-03"
    },
    {
      "name": "Metformina",
      "dose": "850mg",
      "frequency": "2 veces al dia con comidas",
      "since": "2021-07"
    }
  ],
  "allergies": [
    {
      "allergen": "Penicilina",
      "type": "medicamento",
      "severity": "severa",
      "reaction": "Erupciones cutaneas y dificultad para respirar"
    }
  ],
  "chronic_conditions": [
    {
      "condition": "Diabetes mellitus tipo 2",
      "cie10_code": "E11",
      "since": "2021",
      "controlled": true,
      "treatment": "Metformina + dieta"
    }
  ],
  "surgical_history": [
    {
      "procedure": "Apendicectomia",
      "year": 2015,
      "complications": "Ninguna"
    }
  ],
  "family_history": {
    "diabetes": true,
    "hypertension": true,
    "cancer": false,
    "heart_disease": false,
    "bleeding_disorders": false,
    "notes": "Padre diabetico. Madre con hipertension."
  },
  "habits": {
    "smoking": { "status": "former", "packs_per_day": null, "years": 10 },
    "alcohol": { "status": "occasional", "drinks_per_week": 2 },
    "recreational_drugs": { "status": "never", "substances": null },
    "physical_activity": "light"
  },
  "pregnancy_status": "not_applicable",
  "pregnancy_weeks": null,
  "blood_type": "O+",
  "rh_factor": "positive",
  "country_specific": {
    "eps": "Nueva EPS",
    "ips": "Clinica del Country",
    "health_regime": "contributivo",
    "poliza_seguro": "POL-2024-123456"
  },
  "notes": "Paciente refiere alergia severa a penicilina. Verificar siempre antes de prescribir antibioticos.",
  "allergies_alert": true,
  "completed_by": {
    "id": "usr_doctor_002",
    "name": "Dr. Carlos Ramirez",
    "role": "doctor"
  },
  "change_history": [
    {
      "version": 3,
      "updated_at": "2026-02-20T14:00:00Z",
      "updated_by": { "id": "usr_doctor_002", "name": "Dr. Carlos Ramirez", "role": "doctor" }
    },
    {
      "version": 2,
      "updated_at": "2026-01-15T09:30:00Z",
      "updated_by": { "id": "usr_doctor_001", "name": "Dra. Ana Martinez", "role": "doctor" }
    },
    {
      "version": 1,
      "updated_at": "2026-01-01T10:00:00Z",
      "updated_by": { "id": "usr_doctor_001", "name": "Dra. Ana Martinez", "role": "doctor" }
    }
  ],
  "created_at": "2026-01-01T10:00:00Z",
  "updated_at": "2026-02-20T14:00:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** Token ausente, expirado o invalido.

#### 403 Forbidden
**When:** Rol sin permiso para ver la anamnesis.

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para acceder a la anamnesis del paciente."
}
```

#### 404 Not Found — paciente inexistente
**When:** `patient_id` no existe en el tenant.

```json
{
  "error": "not_found",
  "message": "El paciente especificado no existe."
}
```

#### 404 Not Found — anamnesis no registrada
**When:** El paciente existe pero aun no tiene anamnesis registrada.

```json
{
  "error": "anamnesis_not_found",
  "message": "Este paciente no tiene anamnesis registrada. Use POST /api/v1/patients/{patient_id}/anamnesis para registrarla.",
  "details": {
    "patient_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido.

#### 500 Internal Server Error
**When:** Error inesperado al recuperar la anamnesis.

---

## Business Logic

**Step-by-step process:**

1. Validar `patient_id` (UUID valido).
2. Resolver tenant desde JWT. Verificar rol (doctor, assistant, receptionist).
3. Verificar que `patient_id` existe en el schema del tenant.
4. Buscar anamnesis: `SELECT * FROM anamnesis WHERE patient_id = patient_id AND tenant_id = tenant_id`.
5. Si no encontrada: retornar 404 con error `anamnesis_not_found` (diferente al 404 de paciente inexistente).
6. Cargar el historial de cambios desde `audit_logs` (solo los campos `version`, `updated_at`, `updated_by` — sin el diff completo del contenido, que requiere permiso especial).
7. Calcular `allergies_alert = len(anamnesis.allergies) > 0`.
8. Registrar entrada de auditoria (action=read, resource=anamnesis, phi=true).
9. Retornar 200 con la anamnesis y el change_history resumido.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | UUID valido, paciente existente en tenant | "El paciente especificado no existe." |

**Business Rules:**

- El `change_history` retornado es un resumen del historial (version, fecha, usuario que actualizo). Para ver el diff del contenido de una version especifica, se debe acceder al audit log directamente (solo superadmin o via panel de admin).
- La anamnesis ausente retorna 404 con error code `anamnesis_not_found` (distinto al 404 de paciente inexistente) para que el frontend pueda distinguir y mostrar el CTA de "Registrar anamnesis".
- La recepcionista puede leer la anamnesis completa (incluyendo alergias y medicamentos) para informar al doctor en la recepcion.
- `change_history` ordenado por version descendente.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Paciente con anamnesis sin allergies | `allergies: []`, `allergies_alert: false` |
| Anamnesis de version 1 (recien creada) | `change_history` con 1 entrada |
| Anamnesis creada y modificada 20 veces | `change_history` retorna las ultimas 10 entradas (limite de historial en response) |
| Campo `country_specific` vacio | `country_specific: {}` en respuesta |
| Paciente inactivo | Retornar 404 (no revelar estado) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `audit_logs`: INSERT — entrada de auditoria de lectura PHI

**Example query (SQLAlchemy):**
```python
anamnesis = await session.scalar(
    select(Anamnesis).where(
        Anamnesis.patient_id == patient_id,
        Anamnesis.tenant_id == tenant_id,
    )
)
if not anamnesis:
    raise AnamnesisNotFoundException(patient_id=patient_id)

# Cargar change_history desde audit_logs (ultimas 10 versiones)
history_stmt = (
    select(AuditLog)
    .where(
        AuditLog.resource == "anamnesis",
        AuditLog.resource_id == str(anamnesis.id),
        AuditLog.action.in_(["create", "update"]),
    )
    .order_by(AuditLog.created_at.desc())
    .limit(10)
)
history = await session.scalars(history_stmt)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:anamnesis`: GET — lectura desde cache; SET si cache miss

**Cache TTL:** 300s (5 minutos; se invalida al actualizar via CR-05)

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| audit | anamnesis.read | { anamnesis_id, patient_id, user_id, role, tenant_id, timestamp } | Siempre al leer |

### Audit Log

**Audit entry:** Yes

- **Action:** read
- **Resource:** anamnesis
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 100ms
- **Maximum acceptable:** < 250ms

### Caching Strategy
- **Strategy:** Redis cache con TTL de 5 minutos
- **Cache key:** `tenant:{tenant_id}:patient:{patient_id}:anamnesis`
- **TTL:** 300s
- **Invalidation:** Al actualizar la anamnesis via CR-05

### Database Performance

**Queries executed:** 2-3 (1 para anamnesis, 1 para change_history desde audit_logs, 1 para audit log de lectura)

**Indexes required:**
- `anamnesis.(patient_id, tenant_id)` — UNIQUE
- `audit_logs.(resource, resource_id, action, created_at DESC)` — INDEX compuesto para historial

**N+1 prevention:** No aplica (1 anamnesis por paciente). Historial en query separado con LIMIT 10.

### Pagination

**Pagination:** No (1 anamnesis por paciente; historial limitado a 10 entradas en response)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID | Prevenir inyeccion |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM con queries parametrizadas. Sin SQL raw.

### XSS Prevention

**Output encoding:** Todos los strings escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Todo el body de respuesta — medicamentos, alergias, condiciones cronicas, habitos, estado de embarazo, tipo de sangre, datos de EPS/IPS.

**Audit requirement:** All access logged — toda lectura de anamnesis auditada incluyendo usuario, rol y timestamp.

---

## Testing

### Test Cases

#### Happy Path
1. Doctor lee anamnesis existente
   - **Given:** Doctor autenticado, paciente con anamnesis version=3
   - **When:** GET /api/v1/patients/{pid}/anamnesis
   - **Then:** 200 OK, todos los campos presentes, change_history con 3 entradas, audit log registrado

2. Recepcionista lee anamnesis
   - **Given:** Recepcionista autenticada, anamnesis con alergias
   - **When:** GET con token de recepcionista
   - **Then:** 200 OK, `allergies_alert: true`, audit log registrado

3. Anamnesis sin alergias
   - **Given:** Paciente con anamnesis donde `allergies: []`
   - **When:** GET de la anamnesis
   - **Then:** 200 OK, `allergies_alert: false`

#### Edge Cases
1. Anamnesis con historial > 10 versiones
   - **Given:** Anamnesis con version=15
   - **When:** GET de la anamnesis
   - **Then:** 200 OK, `change_history` con maximo 10 entradas

2. country_specific vacio
   - **Given:** Anamnesis sin campos especificos de pais
   - **When:** GET de la anamnesis
   - **Then:** 200 OK, `country_specific: {}`

#### Error Cases
1. Paciente sin anamnesis
   - **Given:** Paciente nuevo sin anamnesis registrada
   - **When:** GET de la anamnesis
   - **Then:** 404 con error `anamnesis_not_found` y mensaje con instruccion de registro

2. Paciente inexistente
   - **Given:** patient_id que no existe en el tenant
   - **When:** GET de la anamnesis
   - **Then:** 404 con error `not_found`

3. Token expirado
   - **Given:** Token JWT expirado
   - **When:** GET sin Authorization valido
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** Doctor activo, asistente activo, recepcionista activa

**Patients/Entities:** Paciente con anamnesis (version 3, con alergias), paciente sin anamnesis registrada, paciente inexistente (ID inventado)

### Mocking Strategy

- **Redis:** fakeredis para cache en unit tests
- **Audit service:** Mock que verifica que se registra lectura de PHI

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Anamnesis retornada correctamente con todos los campos
- [ ] change_history retornado ordenado por version descendente (max 10 entradas)
- [ ] `allergies_alert` calculado correctamente
- [ ] 404 `anamnesis_not_found` cuando el paciente no tiene anamnesis (distinto al 404 de paciente inexistente)
- [ ] Auditoria registrada en toda lectura (doctor, assistant, receptionist)
- [ ] Cache de 5min funcional; invalidado al actualizar la anamnesis
- [ ] Recepcionista puede leer anamnesis completa (incluyendo alergias y medicamentos)
- [ ] All test cases pass
- [ ] Performance targets met (< 250ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verified (PHI)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Crear o actualizar anamnesis (ver CR-05)
- Ver el diff del contenido entre versiones (solo disponible via audit log para superadmin)
- Anamnesis de pacientes del portal del paciente
- Exportar anamnesis a PDF (ver admin/export.md)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models con change_history)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated (incluyendo anamnesis_not_found vs not_found)
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
- [x] Audit trail para PHI altamente sensible

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 250ms)
- [x] Caching strategy stated (5min TTL)
- [x] DB queries optimized (UNIQUE index, LIMIT 10 en historial)
- [x] Pagination applied where needed (N/A — 1 anamnesis por paciente)

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
| 1.0 | 2026-02-24 | Initial spec |
