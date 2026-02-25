# Actualizar Registro Clinico (CR-04)

---

## Overview

**Feature:** Actualiza el contenido de un registro clinico existente. Solo permite edicion dentro de 24 horas desde la creacion (el clinic_owner puede anular este limite). No permite cambiar el tipo del registro. Todos los cambios son auditados con diff old_value/new_value.

**Domain:** clinical-records

**Priority:** High

**Dependencies:** CR-01 (record-create.md), CR-02 (record-get.md), infra/audit-logging.md, infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor (solo registros propios), clinic_owner (cualquier registro)
- **Tenant context:** Required — resuelto desde JWT
- **Special rules:** Doctor solo puede editar sus propios registros (`doctor_id == current_user.id`). clinic_owner puede editar cualquier registro del tenant, incluso despues de 24h. PHI — toda escritura es auditada.

---

## Endpoint

```
PUT /api/v1/patients/{patient_id}/clinical-records/{record_id}
```

**Rate Limiting:**
- 30 requests por minuto por usuario
- Redis sliding window: `tenant:{tenant_id}:rate:clinical_records_update:{user_id}`

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
| record_id | Yes | UUID | Debe pertenecer al patient_id | ID del registro a actualizar | cr_f47ac10b-58cc-4372-a567-0e02b2c3d479 |

### Query Parameters

N/A

### Request Body Schema

```json
{
  "content": "object (required) — nuevo contenido del registro. Debe mantener la estructura del tipo original.",
  "tooth_numbers": "array<integer> (optional) — actualizar dientes vinculados",
  "diagnosis_ids": "array<UUID> (optional) — actualizar diagnosticos vinculados",
  "appointment_id": "UUID | null (optional) — actualizar o desvincular cita"
}
```

**Nota:** El campo `type` NO puede cambiarse. Si se incluye en el body, sera ignorado con advertencia.

**Example Request:**
```json
{
  "content": {
    "subjective": "Paciente refiere dolor moderado en cuadrante superior derecho, especialmente al masticar.",
    "objective": "Sensibilidad a percusion en diente 16. Caries oclusal visible. Sin movilidad.",
    "assessment": "Caries profunda diente 16 con probable compromiso pulpar.",
    "plan": "Radiografia periapical urgente. Valorar endodoncia. Prescripcion de analgesicos."
  },
  "tooth_numbers": [16],
  "diagnosis_ids": ["d9e8f7a6-b5c4-3210-fedc-ba9876543210"]
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
  "type": "string",
  "content": "object — contenido actualizado",
  "appointment_id": "UUID | null",
  "tooth_numbers": "array<integer>",
  "diagnosis_ids": "array<UUID>",
  "doctor": {
    "id": "UUID",
    "name": "string"
  },
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime — timestamp de esta actualizacion",
  "is_editable": "boolean",
  "edit_deadline": "ISO8601 datetime | null",
  "updated_by": {
    "id": "UUID",
    "name": "string",
    "role": "string"
  }
}
```

**Example:**
```json
{
  "id": "cr_f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "evolution_note",
  "content": {
    "subjective": "Paciente refiere dolor moderado en cuadrante superior derecho, especialmente al masticar.",
    "objective": "Sensibilidad a percusion en diente 16. Caries oclusal visible. Sin movilidad.",
    "assessment": "Caries profunda diente 16 con probable compromiso pulpar.",
    "plan": "Radiografia periapical urgente. Valorar endodoncia. Prescripcion de analgesicos."
  },
  "appointment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "tooth_numbers": [16],
  "diagnosis_ids": ["d9e8f7a6-b5c4-3210-fedc-ba9876543210"],
  "doctor": {
    "id": "usr_doctor_001",
    "name": "Dra. Ana Martinez"
  },
  "created_at": "2026-02-24T10:30:00Z",
  "updated_at": "2026-02-24T11:45:00Z",
  "is_editable": true,
  "edit_deadline": "2026-02-25T10:30:00Z",
  "updated_by": {
    "id": "usr_doctor_001",
    "name": "Dra. Ana Martinez",
    "role": "doctor"
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Body invalido o campos mal formateados.

```json
{
  "error": "invalid_input",
  "message": "Los datos proporcionados no son validos.",
  "details": {
    "content": ["El contenido del registro es obligatorio."]
  }
}
```

#### 401 Unauthorized
**When:** Token ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden — registro de otro doctor
**When:** Doctor intenta editar registro de otro doctor.

```json
{
  "error": "forbidden",
  "message": "Solo puede editar sus propios registros clinicos."
}
```

#### 403 Forbidden — fuera del limite de 24h
**When:** Han pasado mas de 24h desde la creacion y el usuario no es clinic_owner.

```json
{
  "error": "edit_window_expired",
  "message": "El periodo de edicion de 24 horas ha vencido. Solo el propietario de la clinica puede modificar este registro.",
  "details": {
    "created_at": "2026-02-23T10:30:00Z",
    "edit_deadline": "2026-02-24T10:30:00Z"
  }
}
```

#### 403 Forbidden — rol sin permisos
**When:** assistant o receptionist intentan editar.

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para editar registros clinicos."
}
```

#### 404 Not Found
**When:** `patient_id` o `record_id` no existen en el tenant.

```json
{
  "error": "not_found",
  "message": "El registro clinico especificado no existe."
}
```

#### 422 Unprocessable Entity
**When:** Se intenta cambiar el tipo del registro, o diagnosis_ids/tooth_numbers invalidos.

```json
{
  "error": "validation_failed",
  "message": "No es posible cambiar el tipo de un registro clinico existente.",
  "details": {
    "type": ["El tipo del registro no puede modificarse despues de la creacion."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido. Ver `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Error inesperado al actualizar el registro o registrar el audit log.

---

## Business Logic

**Step-by-step process:**

1. Validar input contra schema Pydantic.
2. Resolver tenant desde JWT. Verificar que el usuario tiene rol `doctor` o `clinic_owner`.
3. Verificar que `patient_id` existe en el tenant.
4. Buscar el registro `clinical_records` por `id=record_id`, `patient_id`, `tenant_id`. Si no encontrado: retornar 404.
5. Verificar permisos de escritura:
   - Si `current_user.role == 'doctor'` y `record.doctor_id != current_user.id`: retornar 403 "solo sus propios registros".
   - Si `current_user.role == 'assistant'` o `'receptionist'`: retornar 403.
6. Verificar ventana de edicion:
   - Si `now() > record.created_at + 24h` y `current_user.role != 'clinic_owner'`: retornar 403 con `edit_window_expired`.
7. Si el body incluye campo `type`: ignorarlo (no cambiar el tipo). Loguear advertencia en logs estructurados.
8. Capturar `old_content`, `old_tooth_numbers`, `old_diagnosis_ids` para el diff de auditoria.
9. Actualizar `clinical_records.content` con el nuevo contenido.
10. Si `tooth_numbers` provisto: actualizar tabla `clinical_record_teeth` (DELETE registros actuales + INSERT nuevos).
11. Si `diagnosis_ids` provisto: actualizar tabla `clinical_record_diagnoses` (DELETE actuales + INSERT nuevos, verificando que los diagnosis_ids existen y pertenecen al paciente).
12. Actualizar `updated_at = now()`.
13. Registrar entrada de auditoria con diff completo (`old_value` vs `new_value` para `content`, `tooth_numbers`, `diagnosis_ids`).
14. Invalidar cache del registro individual y del listado del paciente.
15. Retornar 200 con el registro actualizado.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| content | Requerido. Objeto no vacio. | "El contenido del registro es obligatorio." |
| tooth_numbers | Cada elemento entre 11 y 48 (FDI) si provisto | "Numero de diente invalido. Use numeracion FDI (11-48)." |
| diagnosis_ids | Cada UUID debe existir y pertenecer al paciente | "El diagnostico especificado no existe o no pertenece a este paciente." |
| type | Campo ignorado si provisto (no error, solo warning en logs) | — |

**Business Rules:**

- El `type` del registro es inmutable despues de la creacion. Intentar cambiarlo no produce error pero el campo es ignorado.
- Solo el doctor que creo el registro puede editarlo (a menos que sea clinic_owner).
- La ventana de edicion es estrictamente 24 horas desde `created_at`. Despues de ese plazo, solo `clinic_owner` puede editar.
- El audit log almacena el diff completo: `old_value` y `new_value` del campo `content` (JSON completo), mas cambios en `tooth_numbers` y `diagnosis_ids`.
- `appointment_id` puede ser actualizado (para vincular a otra cita) o desvinculado (enviando `null`), pero solo dentro de la ventana de 24h o por clinic_owner.
- Las actualizaciones de `tooth_numbers` y `diagnosis_ids` son reemplazos completos (no merge parcial).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| clinic_owner edita registro de hace 30 dias | Permitido; `is_editable: true`, `edit_deadline: null` |
| Doctor edita registro exactamente a las 24h | Verificar con `>=` (strictamente despues de 24h = bloqueado) |
| tooth_numbers enviado como lista vacia [] | Eliminar todos los dientes vinculados al registro |
| diagnosis_ids enviado como lista vacia [] | Eliminar todos los diagnosticos vinculados al registro |
| appointment_id enviado como null | Desvincular la cita del registro |
| Content identico al actual (sin cambios reales) | Permitir la actualizacion; updated_at se actualiza igualmente; audit log registra diff vacio |
| Multiples actualizaciones al mismo registro dentro de 24h | Cada actualizacion sobrescribe la anterior; audit log guarda historial de cada cambio |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `clinical_records`: UPDATE — `content`, `appointment_id`, `updated_at`
- `clinical_record_teeth`: DELETE + INSERT — reemplazo de dientes vinculados si `tooth_numbers` cambia
- `clinical_record_diagnoses`: DELETE + INSERT — reemplazo de diagnosticos si `diagnosis_ids` cambia
- `audit_logs`: INSERT — entrada de auditoria con diff

**Example query (SQLAlchemy):**
```python
# Capturar valores anteriores
old_content = record.content
old_tooth_numbers = [t.tooth_number for t in record.teeth]
old_diagnosis_ids = [d.diagnosis_id for d in record.diagnoses]

# Actualizar registro
record.content = body.content
if body.appointment_id is not _UNSET:
    record.appointment_id = body.appointment_id
record.updated_at = datetime.utcnow()

# Reemplazar dientes
if body.tooth_numbers is not None:
    await session.execute(
        delete(ClinicalRecordTooth).where(
            ClinicalRecordTooth.clinical_record_id == record_id
        )
    )
    session.add_all([
        ClinicalRecordTooth(clinical_record_id=record_id, tooth_number=n)
        for n in body.tooth_numbers
    ])

# Reemplazar diagnosticos
if body.diagnosis_ids is not None:
    await session.execute(
        delete(ClinicalRecordDiagnosis).where(
            ClinicalRecordDiagnosis.clinical_record_id == record_id
        )
    )
    session.add_all([
        ClinicalRecordDiagnosis(clinical_record_id=record_id, diagnosis_id=did)
        for did in body.diagnosis_ids
    ])

await session.commit()

# Registrar audit log con diff
audit_log = AuditLog(
    action="update",
    resource="clinical_record",
    resource_id=record_id,
    user_id=current_user.id,
    tenant_id=tenant_id,
    phi=True,
    diff={
        "content": {"old": old_content, "new": body.content},
        "tooth_numbers": {"old": old_tooth_numbers, "new": body.tooth_numbers},
        "diagnosis_ids": {"old": old_diagnosis_ids, "new": body.diagnosis_ids},
    },
)
session.add(audit_log)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:clinical_record:{record_id}`: DELETE — invalidar cache del registro individual
- `tenant:{tenant_id}:patient:{patient_id}:clinical_records:list`: DELETE — invalidar listado del paciente

**Cache TTL:** N/A (invalidacion)

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| audit | clinical_record.updated | { record_id, patient_id, doctor_id, updated_by_id, tenant_id, timestamp, diff_summary } | Siempre al actualizar |

### Audit Log

**Audit entry:** Yes

- **Action:** update
- **Resource:** clinical_record
- **PHI involved:** Yes

El audit log incluye el diff completo:
```json
{
  "action": "update",
  "resource": "clinical_record",
  "resource_id": "cr_f47ac10b-...",
  "user_id": "usr_doctor_001",
  "tenant_id": "tn_abc123",
  "phi": true,
  "diff": {
    "content": {
      "old": { "subjective": "Dolor leve..." },
      "new": { "subjective": "Dolor moderado..." }
    },
    "tooth_numbers": { "old": [16], "new": [16] },
    "diagnosis_ids": { "old": ["d9e8..."], "new": ["d9e8..."] }
  },
  "clinic_owner_override": false,
  "timestamp": "2026-02-24T11:45:00Z"
}
```

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** Invalidacion de cache al actualizar
- **Cache key:** `tenant:{tenant_id}:clinical_record:{record_id}`
- **TTL:** N/A (solo invalidacion)
- **Invalidation:** Inmediata al actualizar el registro

### Database Performance

**Queries executed:** 4-6 (buscar registro, verificar diagnoses, update registro, delete+insert relaciones, audit log)

**Indexes required:**
- `clinical_records.(id, patient_id, tenant_id)` — UNIQUE compuesto
- `clinical_records.doctor_id` — INDEX (para verificar ownership)
- `clinical_record_teeth.clinical_record_id` — INDEX
- `clinical_record_diagnoses.clinical_record_id` — INDEX

**N+1 prevention:** Relaciones actualizadas en bulk con DELETE + bulk INSERT.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| content | Pydantic validator + bleach para campos rich text | Prevenir XSS |
| tooth_numbers | Pydantic list[int], rango 11-48 | Prevenir valores fuera de rango |
| patient_id | Pydantic UUID | Prevenir inyeccion |
| record_id | Pydantic UUID | Prevenir inyeccion |
| diagnosis_ids | Pydantic list[UUID] | Prevenir inyeccion |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM con queries parametrizadas. Sin SQL raw.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic. Campos rich text sanitizados con bleach.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `content` (historia clinica del paciente — OLD y NEW valores almacenados en audit log), `tooth_numbers`, `diagnosis_ids`

**Audit requirement:** All access logged — diff completo almacenado en audit log para trazabilidad clinica y legal.

---

## Testing

### Test Cases

#### Happy Path
1. Doctor actualiza su propio registro dentro de 24h
   - **Given:** Doctor autenticado, registro propio creado hace 1 hora
   - **When:** PUT con content actualizado
   - **Then:** 200 OK, content actualizado, audit log con diff, cache invalidado

2. clinic_owner actualiza registro de otro doctor fuera de 24h
   - **Given:** clinic_owner autenticado, registro de doctor creado hace 30 dias
   - **When:** PUT con content actualizado
   - **Then:** 200 OK, actualizacion exitosa, `updated_by` refleja clinic_owner

3. Actualizar tooth_numbers (reemplazo completo)
   - **Given:** Registro con tooth_numbers=[16], doctor autenticado dentro de 24h
   - **When:** PUT con tooth_numbers=[16, 17]
   - **Then:** 200 OK, clinical_record_teeth actualizado con 2 dientes

#### Edge Cases
1. content identico al actual
   - **Given:** Doctor envia el mismo content sin cambios
   - **When:** PUT con content identico
   - **Then:** 200 OK, updated_at actualizado, audit log con diff vacio registrado

2. tooth_numbers enviado como lista vacia
   - **Given:** Registro con 2 dientes vinculados
   - **When:** PUT con tooth_numbers=[]
   - **Then:** 200 OK, todos los dientes desvinculados del registro

3. Body incluye campo type
   - **Given:** Doctor envia type=examination en registro de tipo evolution_note
   - **When:** PUT con type=examination
   - **Then:** 200 OK, tipo NO cambiado, warning en logs

#### Error Cases
1. Doctor intenta editar registro de otro doctor
   - **Given:** Doctor A autenticado, registro creado por Doctor B
   - **When:** PUT del registro de Doctor B
   - **Then:** 403 con "Solo puede editar sus propios registros clinicos."

2. Registro de mas de 24h editado por doctor
   - **Given:** Doctor autenticado, registro creado hace 25 horas
   - **When:** PUT del registro
   - **Then:** 403 con edit_window_expired y detalle de edit_deadline

3. record_id inexistente
   - **Given:** record_id que no existe
   - **When:** PUT del registro
   - **Then:** 404 Not Found

4. assistant intenta editar
   - **Given:** Usuario con rol assistant
   - **When:** PUT del registro
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** Doctor A, Doctor B, clinic_owner, asistente

**Patients/Entities:** Paciente con registros: uno reciente (< 24h) de Doctor A, uno antiguo (> 24h) de Doctor A, uno de Doctor B

### Mocking Strategy

- **Redis:** fakeredis para rate limiting y cache en unit tests
- **Audit service:** Mock que verifica que se llama con diff correcto
- **Tiempo:** Mockear `datetime.utcnow()` para simular escenarios de 24h

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Doctor puede editar su propio registro dentro de 24h
- [ ] Doctor NO puede editar registro de otro doctor (403)
- [ ] Doctor NO puede editar su propio registro despues de 24h (403 con edit_window_expired)
- [ ] clinic_owner puede editar cualquier registro sin limite de tiempo
- [ ] Tipo del registro no puede cambiarse (ignorado silenciosamente)
- [ ] Audit log registra diff completo (old_value/new_value)
- [ ] tooth_numbers y diagnosis_ids son reemplazados completamente
- [ ] Cache invalidado al actualizar
- [ ] All test cases pass
- [ ] Performance targets met (< 500ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verified (PHI con diff)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Eliminacion de registros clinicos (registros son inmutables; no se borran)
- Cambio de tipo de registro (no permitido por diseno)
- Adjuntar/remover archivos de un registro (endpoint separado)
- Firma digital de actualizaciones (post-MVP)
- Restauracion de versiones anteriores (ver audit log — informacion esta disponible pero no hay endpoint de restauracion en MVP)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (role + tenant + ownership)
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (domain separation)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role + ownership + 24h window)
- [x] Input sanitization defined (Pydantic + bleach)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail con diff completo para PHI

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidacion)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined con diff
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy para datetime (24h window)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
