# Actualizar Diagnostico (CR-09)

---

## Overview

**Feature:** Actualiza el estado de un diagnostico (active -> resolved) y permite agregar notas adicionales. El codigo CIE-10 es inmutable; para cambiar el diagnostico se debe crear uno nuevo y resolver el existente. Todos los cambios son auditados con diff old/new.

**Domain:** clinical-records

**Priority:** High

**Dependencies:** CR-07 (diagnosis-create.md), CR-08 (diagnosis-list.md), infra/audit-logging.md, infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor
- **Tenant context:** Required — resuelto desde JWT
- **Special rules:** Solo doctores pueden actualizar diagnosticos. Los asistentes no tienen permiso. PHI — toda escritura es auditada.

---

## Endpoint

```
PUT /api/v1/patients/{patient_id}/diagnoses/{diagnosis_id}
```

**Rate Limiting:**
- 30 requests por minuto por usuario
- Redis sliding window: `tenant:{tenant_id}:rate:diagnoses_update:{user_id}`

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
| diagnosis_id | Yes | UUID | Debe pertenecer al patient_id | ID del diagnostico a actualizar | dx_d9e8f7a6-b5c4-3210-fedc-ba9876543210 |

### Query Parameters

N/A

### Request Body Schema

```json
{
  "status": "string (optional) — active | resolved. Solo se permite cambiar de active a resolved.",
  "notes": "string (optional) — notas clinicas adicionales. Se concatenan con las notas existentes o reemplazan si se especifica reemplazar.",
  "severity": "string (optional) — mild | moderate | severe. Puede actualizarse si la condicion cambia.",
  "resolution_notes": "string (optional) — notas especificas sobre la resolucion del diagnostico (como se resolvio). Solo valido cuando status=resolved."
}
```

**Example Request (resolver diagnostico):**
```json
{
  "status": "resolved",
  "resolution_notes": "Caries tratada con restauracion compuesta resina clase II en diente 16. Procedimiento completado sin complicaciones el 2026-02-24.",
  "notes": "Seguimiento en 6 meses."
}
```

**Example Request (actualizar severidad y notas):**
```json
{
  "severity": "severe",
  "notes": "Progresion de caries. Ahora con afeccion pulpar probable. Urgente valorar endodoncia."
}
```

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "id": "UUID",
  "patient_id": "UUID",
  "cie10_code": "string",
  "cie10_description": "string",
  "custom_description": "string | null",
  "tooth_number": "integer | null",
  "tooth_notation_fdi": "string | null",
  "severity": "string",
  "status": "string",
  "notes": "string | null",
  "resolution_notes": "string | null",
  "doctor": {
    "id": "UUID",
    "name": "string"
  },
  "updated_by": {
    "id": "UUID",
    "name": "string",
    "role": "string"
  },
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime",
  "resolved_at": "ISO8601 datetime | null"
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
  "status": "resolved",
  "notes": "Seguimiento en 6 meses.",
  "resolution_notes": "Caries tratada con restauracion compuesta resina clase II en diente 16. Procedimiento completado sin complicaciones el 2026-02-24.",
  "doctor": {
    "id": "usr_doctor_001",
    "name": "Dra. Ana Martinez"
  },
  "updated_by": {
    "id": "usr_doctor_001",
    "name": "Dra. Ana Martinez",
    "role": "doctor"
  },
  "created_at": "2026-02-10T09:00:00Z",
  "updated_at": "2026-02-24T14:00:00Z",
  "resolved_at": "2026-02-24T14:00:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Se intenta cambiar el codigo CIE-10 o status invalido.

```json
{
  "error": "invalid_input",
  "message": "Los datos del diagnostico no son validos.",
  "details": {
    "cie10_code": ["El codigo CIE-10 no puede modificarse. Cree un nuevo diagnostico si necesita un codigo diferente."]
  }
}
```

#### 400 Bad Request — transicion de estado invalida
**When:** Intento de cambiar status de resolved a active (no permitido), o de active a active.

```json
{
  "error": "invalid_status_transition",
  "message": "La transicion de estado no es valida.",
  "details": {
    "status": ["Un diagnostico resuelto no puede volver a estado activo. Cree un nuevo diagnostico si la condicion reaparece."]
  }
}
```

#### 401 Unauthorized
**When:** Token ausente, expirado o invalido.

#### 403 Forbidden
**When:** Usuario no es doctor (assistant, receptionist).

```json
{
  "error": "forbidden",
  "message": "Solo los doctores pueden actualizar diagnosticos clinicos."
}
```

#### 404 Not Found
**When:** `patient_id` o `diagnosis_id` no existen, o el diagnostico no pertenece al paciente.

```json
{
  "error": "not_found",
  "message": "El diagnostico especificado no existe."
}
```

#### 422 Unprocessable Entity
**When:** `resolution_notes` provisto sin `status=resolved`.

```json
{
  "error": "validation_failed",
  "message": "Las notas de resolucion solo aplican cuando se cambia el estado a 'resolved'.",
  "details": {
    "resolution_notes": ["Este campo solo es valido cuando status='resolved'."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido.

#### 500 Internal Server Error
**When:** Error inesperado al actualizar el diagnostico.

---

## Business Logic

**Step-by-step process:**

1. Validar input contra schema Pydantic (`DiagnosisUpdateSchema`).
2. Resolver tenant desde JWT. Verificar que el usuario tiene rol `doctor`. Si no: retornar 403.
3. Verificar que `patient_id` existe en el tenant.
4. Buscar diagnostico: `SELECT * FROM diagnoses WHERE id=diagnosis_id AND patient_id=patient_id AND tenant_id=tenant_id`. Si no encontrado: 404.
5. Si el body incluye `cie10_code`: retornar 400 indicando que el codigo CIE-10 es inmutable.
6. Si `status` provisto:
   - Verificar transicion valida: `active -> resolved` es la unica permitida.
   - Si `status == 'active'` y `diagnosis.status == 'active'`: ignorar (sin error, sin cambio).
   - Si `status == 'active'` y `diagnosis.status == 'resolved'`: retornar 400 `invalid_status_transition`.
7. Si `resolution_notes` provisto y `status != 'resolved'` (ni en el body ni en el estado actual del diagnostico): retornar 422.
8. Capturar valores anteriores para el diff de auditoria.
9. Actualizar los campos modificados: `status`, `severity`, `notes`, `resolution_notes`, `updated_at`.
10. Si `status == 'resolved'`: establecer `resolved_at = now()`.
11. Registrar entrada de auditoria con diff completo.
12. Invalidar cache del listado de diagnosticos del paciente.
13. Retornar 200 con el diagnostico actualizado.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| status | Enum: active, resolved. Transicion solo active->resolved. | "La transicion de estado no es valida." |
| severity | Enum: mild, moderate, severe si provisto | "Severidad invalida. Opciones: mild, moderate, severe." |
| cie10_code | Inmutable — si provisto en body, retornar 400 | "El codigo CIE-10 no puede modificarse." |
| resolution_notes | Solo si status=resolved (nuevo o ya resuelto) | "Las notas de resolucion solo aplican cuando status='resolved'." |

**Business Rules:**

- El codigo CIE-10 es absolutamente inmutable. Si se necesita cambiar el diagnostico, se crea uno nuevo y se resuelve el existente.
- La transicion de estado es unidireccional: `active -> resolved`. No se puede reactivar un diagnostico resuelto. Si la condicion reaparece, se crea un nuevo diagnostico.
- El campo `notes` es un campo libre que puede actualizarse sin restriccion de estado.
- El campo `severity` puede actualizarse si la condicion del paciente cambia (progresa o mejora).
- `resolved_at` se establece automaticamente al momento de resolver el diagnostico.
- El `updated_by` en la respuesta refleja quien realizo la ultima actualizacion (puede ser distinto al doctor que creo el diagnostico, si otro doctor del mismo tenant lo resuelve).
- Un doctor puede resolver diagnosticos de otro doctor (dentro del mismo tenant). No hay restriccion de ownership en actualizaciones.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Body con status=active sobre diagnostico ya activo | Aceptar sin error; updated_at se actualiza; audit log sin cambio de status |
| Body vacio `{}` | Retornar 200 sin cambios; updated_at NO se actualiza (operacion inocua) |
| resolution_notes sobre diagnostico ya resuelto (sin cambio de status) | Aceptar; actualizar resolution_notes |
| severity actualizada a mismo valor | Aceptar; updated_at se actualiza |
| Doctor B resuelve diagnostico creado por Doctor A | Permitido; updated_by refleja Doctor B, doctor original preservado en campo doctor |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `diagnoses`: UPDATE — `status`, `severity`, `notes`, `resolution_notes`, `resolved_at`, `updated_at`
- `audit_logs`: INSERT — entrada con diff old/new

**Example query (SQLAlchemy):**
```python
# Capturar valores anteriores
old_status = diagnosis.status
old_severity = diagnosis.severity
old_notes = diagnosis.notes

# Aplicar cambios
if body.status is not None:
    diagnosis.status = body.status
    if body.status == "resolved":
        diagnosis.resolved_at = datetime.utcnow()

if body.severity is not None:
    diagnosis.severity = body.severity

if body.notes is not None:
    diagnosis.notes = body.notes

if body.resolution_notes is not None:
    diagnosis.resolution_notes = body.resolution_notes

diagnosis.updated_at = datetime.utcnow()
await session.commit()

# Audit log con diff
audit_diff = {}
if old_status != diagnosis.status:
    audit_diff["status"] = {"old": old_status, "new": diagnosis.status}
if old_severity != diagnosis.severity:
    audit_diff["severity"] = {"old": old_severity, "new": diagnosis.severity}
if old_notes != diagnosis.notes:
    audit_diff["notes"] = {"old": old_notes, "new": diagnosis.notes}
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:diagnoses:list:{any}`: DELETE — invalidar todos los caches de listados del paciente (patron wildcard o lista de claves conocidas)

**Cache TTL:** N/A (invalidacion)

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| audit | diagnosis.updated | { diagnosis_id, patient_id, doctor_id, updated_by_id, tenant_id, diff, timestamp } | Siempre al actualizar |
| analytics | diagnosis.resolved | { diagnosis_id, cie10_code, tooth_number, tenant_id, days_active, timestamp } | Cuando status cambia a resolved |

### Audit Log

**Audit entry:** Yes

- **Action:** update
- **Resource:** diagnosis
- **PHI involved:** Yes

Diff almacenado:
```json
{
  "action": "update",
  "resource": "diagnosis",
  "resource_id": "dx_d9e8f7a6-...",
  "user_id": "usr_doctor_001",
  "tenant_id": "tn_abc123",
  "phi": true,
  "diff": {
    "status": { "old": "active", "new": "resolved" },
    "notes": { "old": null, "new": "Seguimiento en 6 meses." }
  },
  "timestamp": "2026-02-24T14:00:00Z"
}
```

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 150ms
- **Maximum acceptable:** < 350ms

### Caching Strategy
- **Strategy:** Invalidacion de cache al actualizar
- **Cache key:** `tenant:{tenant_id}:patient:{patient_id}:diagnoses:list:*`
- **TTL:** N/A (solo invalidacion)
- **Invalidation:** Inmediata al actualizar el diagnostico

### Database Performance

**Queries executed:** 3 (buscar diagnostico, update, audit log)

**Indexes required:**
- `diagnoses.(id, patient_id, tenant_id)` — INDEX compuesto
- `diagnoses.doctor_id` — INDEX
- `diagnoses.status` — INDEX para filtros de listado

**N+1 prevention:** No aplica (actualizacion de un solo registro).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID | Prevenir inyeccion |
| diagnosis_id | Pydantic UUID | Prevenir inyeccion |
| status | Pydantic Literal enum | Prevenir valores arbitrarios |
| severity | Pydantic Literal enum | Prevenir valores arbitrarios |
| notes | Pydantic str + bleach strip_tags | Prevenir XSS |
| resolution_notes | Pydantic str + bleach strip_tags | Prevenir XSS |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM con queries parametrizadas. Sin SQL raw.

### XSS Prevention

**Output encoding:** Todos los strings escapados via serializacion Pydantic. Campos de texto sanitizados con bleach.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `status` (revela estado de salud del paciente), `notes`, `resolution_notes`, `severity`

**Audit requirement:** All access logged — diff completo almacenado en audit log.

---

## Testing

### Test Cases

#### Happy Path
1. Resolver diagnostico activo
   - **Given:** Doctor autenticado, diagnostico activo
   - **When:** PUT con status=resolved, resolution_notes
   - **Then:** 200 OK, status=resolved, resolved_at establecido, audit log con diff

2. Actualizar severidad
   - **Given:** Doctor autenticado, diagnostico activo con severity=mild
   - **When:** PUT con severity=severe
   - **Then:** 200 OK, severity actualizada, audit log registra cambio

3. Agregar notas sin cambiar estado
   - **Given:** Doctor autenticado, diagnostico activo sin notas
   - **When:** PUT solo con notes="Nueva observacion clinica"
   - **Then:** 200 OK, notes actualizadas

#### Edge Cases
1. Body vacio
   - **Given:** Doctor autenticado
   - **When:** PUT con body={}
   - **Then:** 200 OK sin cambios, updated_at NO cambia

2. status=active sobre diagnostico ya activo
   - **Given:** Diagnostico con status=active
   - **When:** PUT con status=active
   - **Then:** 200 OK, sin cambio de estado, audit log registra (sin diff de status)

3. resolution_notes sobre diagnostico ya resuelto
   - **Given:** Diagnostico con status=resolved
   - **When:** PUT solo con resolution_notes actualizadas
   - **Then:** 200 OK, resolution_notes actualizado

4. Doctor B actualiza diagnostico de Doctor A
   - **Given:** Diagnostico creado por Doctor A, Doctor B autenticado
   - **When:** PUT con status=resolved
   - **Then:** 200 OK, `updated_by` es Doctor B, campo `doctor` preserva Doctor A

#### Error Cases
1. Intento de cambiar CIE-10
   - **Given:** Doctor autenticado
   - **When:** PUT con cie10_code=K05.1
   - **Then:** 400 con mensaje de inmutabilidad del codigo CIE-10

2. status=resolved -> active (reversion)
   - **Given:** Diagnostico con status=resolved
   - **When:** PUT con status=active
   - **Then:** 400 con error invalid_status_transition

3. resolution_notes sin status=resolved
   - **Given:** Diagnostico activo
   - **When:** PUT con resolution_notes pero sin status=resolved
   - **Then:** 422 con mensaje de validacion

4. Rol sin permiso (assistant)
   - **Given:** Usuario con rol assistant
   - **When:** PUT al endpoint
   - **Then:** 403 Forbidden

5. diagnosis_id de otro paciente
   - **Given:** diagnosis_id valido pero pertenece a otro paciente
   - **When:** PUT con patient_id incorrecto
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** Doctor A activo, Doctor B activo, asistente (para probar 403)

**Patients/Entities:** Paciente con diagnostico activo K02.1 en diente 16 (severidad moderate), diagnostico ya resuelto K05.1

### Mocking Strategy

- **Redis:** fakeredis para rate limiting y cache en unit tests
- **Audit service:** Mock que verifica diff correcto en audit log
- **Tiempo:** Mockear `datetime.utcnow()` para verificar `resolved_at`

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Estado del diagnostico cambia de active a resolved correctamente
- [ ] `resolved_at` establecido automaticamente al resolver
- [ ] `cie10_code` es inmutable (400 si se intenta cambiar)
- [ ] Transicion resolved->active bloqueada (400 invalid_status_transition)
- [ ] `resolution_notes` solo acepta si status es (o sera) resolved
- [ ] Severity actualizable independientemente del estado
- [ ] Audit log con diff old/new generado en cada actualizacion
- [ ] Cache de listados invalidado al actualizar
- [ ] Solo doctores pueden actualizar (403 para assistant y receptionist)
- [ ] `updated_by` refleja quien hizo la actualizacion, no quien creo el diagnostico
- [ ] All test cases pass
- [ ] Performance targets met (< 350ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verified (PHI con diff)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Eliminar diagnosticos (los diagnosticos no se eliminan; solo se resuelven)
- Cambiar el codigo CIE-10 de un diagnostico existente (crear nuevo + resolver existente)
- Reactivar diagnosticos resueltos (crear nuevo diagnostico si la condicion reaparece)
- Crear diagnosticos (ver CR-07)
- Listado de diagnosticos (ver CR-08)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated (incluyendo transicion de estado)
- [x] Error cases enumerated (incluyendo invalid_status_transition)
- [x] Auth requirements explicit (doctor only)
- [x] Side effects listed (incluyendo analytics job al resolver)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (domain separation)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (doctor only + tenant context)
- [x] Input sanitization defined (Pydantic + bleach)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail con diff completo

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidacion)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined con diff
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (analytics al resolver)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy para datetime
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
