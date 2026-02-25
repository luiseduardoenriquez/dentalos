# Obtener Registro Clinico (CR-02)

---

## Overview

**Feature:** Obtiene un registro clinico individual con todos sus detalles, incluyendo diagnosticos vinculados, dientes involucrados, informacion del doctor y archivos adjuntos. Toda lectura de PHI es auditada.

**Domain:** clinical-records

**Priority:** High

**Dependencies:** CR-01 (record-create.md), CR-07 (diagnosis-create.md), odontogram/tooth-get.md, infra/audit-logging.md, infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant, receptionist
- **Tenant context:** Required — resuelto desde JWT
- **Special rules:** La recepcionista tiene acceso de solo lectura. Toda lectura de PHI es auditada independientemente del rol.

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/clinical-records/{record_id}
```

**Rate Limiting:**
- 120 requests por minuto por usuario
- Redis sliding window: `tenant:{tenant_id}:rate:clinical_records_read:{user_id}`

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
| record_id | Yes | UUID | Debe pertenecer al patient_id | ID del registro clinico | cr_f47ac10b-58cc-4372-a567-0e02b2c3d479 |

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
  "type": "string — anamnesis | examination | evolution_note | procedure",
  "content": "object — contenido completo del registro",
  "appointment_id": "UUID | null",
  "appointment": {
    "id": "UUID",
    "date": "ISO8601 date",
    "time": "HH:MM",
    "reason": "string | null"
  },
  "tooth_numbers": "array<integer>",
  "teeth_details": [
    {
      "tooth_number": "integer",
      "notation_fdi": "string",
      "current_condition": "string | null"
    }
  ],
  "diagnoses": [
    {
      "id": "UUID",
      "cie10_code": "string",
      "cie10_description": "string",
      "tooth_number": "integer | null",
      "severity": "string",
      "status": "string"
    }
  ],
  "doctor": {
    "id": "UUID",
    "name": "string",
    "specialty": "string | null",
    "license_number": "string | null"
  },
  "template_id": "UUID | null",
  "template_name": "string | null",
  "attachments": [
    {
      "id": "UUID",
      "filename": "string",
      "content_type": "string",
      "size_bytes": "integer",
      "url": "string (presigned S3 URL, TTL 1h)",
      "uploaded_at": "ISO8601 datetime"
    }
  ],
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime",
  "is_editable": "boolean",
  "edit_deadline": "ISO8601 datetime | null",
  "audit_info": {
    "last_modified_by": "string (nombre del usuario)",
    "last_modified_at": "ISO8601 datetime | null"
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
    "subjective": "Paciente refiere dolor leve en cuadrante superior derecho.",
    "objective": "Sensibilidad a percusion en diente 16. Sin movilidad.",
    "assessment": "Probable pulpitis reversible diente 16.",
    "plan": "Radiografia periapical. Valorar endodoncia vs restauracion."
  },
  "appointment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "appointment": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "date": "2026-02-24",
    "time": "10:00",
    "reason": "Dolor cuadrante superior derecho"
  },
  "tooth_numbers": [16],
  "teeth_details": [
    {
      "tooth_number": 16,
      "notation_fdi": "16",
      "current_condition": "caries"
    }
  ],
  "diagnoses": [
    {
      "id": "d9e8f7a6-b5c4-3210-fedc-ba9876543210",
      "cie10_code": "K02.1",
      "cie10_description": "Caries de la dentina",
      "tooth_number": 16,
      "severity": "moderate",
      "status": "active"
    }
  ],
  "doctor": {
    "id": "usr_doctor_001",
    "name": "Dra. Ana Martinez",
    "specialty": "Odontologia General",
    "license_number": "CO-12345"
  },
  "template_id": null,
  "template_name": null,
  "attachments": [
    {
      "id": "att_abc123",
      "filename": "radiografia_periapical_16.jpg",
      "content_type": "image/jpeg",
      "size_bytes": 245760,
      "url": "https://storage.dentalos.com/tenants/tn_abc/records/cr_f47ac/radiografia_periapical_16.jpg?X-Amz-Expires=3600&...",
      "uploaded_at": "2026-02-24T10:35:00Z"
    }
  ],
  "created_at": "2026-02-24T10:30:00Z",
  "updated_at": "2026-02-24T10:30:00Z",
  "is_editable": true,
  "edit_deadline": "2026-02-25T10:30:00Z",
  "audit_info": {
    "last_modified_by": "Dra. Ana Martinez",
    "last_modified_at": null
  }
}
```

### Error Responses

#### 401 Unauthorized
**When:** Token ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** El usuario no tiene permiso para ver registros clinicos de este tenant.

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para acceder a registros clinicos."
}
```

#### 404 Not Found
**When:** `patient_id` no existe en el tenant, o `record_id` no existe o no pertenece al `patient_id`.

```json
{
  "error": "not_found",
  "message": "El registro clinico especificado no existe."
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido. Ver `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Error inesperado al recuperar el registro o generar URL pre-firmada de adjuntos.

---

## Business Logic

**Step-by-step process:**

1. Validar parametros de URL (UUIDs validos).
2. Resolver tenant desde JWT. Verificar que el usuario tiene rol `doctor`, `assistant` o `receptionist`.
3. Verificar que `patient_id` existe en el schema del tenant.
4. Buscar `clinical_records` por `id=record_id` AND `patient_id=patient_id` AND `tenant_id=tenant_id`. Si no encontrado: retornar 404.
5. Cargar relaciones en un JOIN: `clinical_record_diagnoses` → `diagnoses`, `clinical_record_teeth`, `users` (doctor), `appointments` (si appointment_id no es null), `clinical_record_attachments`.
6. Para cada adjunto: generar URL pre-firmada de S3 con TTL de 1 hora.
7. Calcular `is_editable`: `created_at + 24h > now()` OR `current_user.role == 'clinic_owner'`.
8. Calcular `edit_deadline`: `created_at + 24h` (solo relevante si `is_editable=true`).
9. Registrar entrada de auditoria (action=read, resource=clinical_record, phi=true).
10. Retornar 200 con el registro completo.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | UUID valido, paciente existente en tenant | "El paciente especificado no existe." |
| record_id | UUID valido, registro existente y perteneciente al patient_id | "El registro clinico especificado no existe." |

**Business Rules:**

- Las URLs de adjuntos son pre-firmadas (S3 presigned URLs) con TTL de 1 hora para evitar exposicion publica de PHI.
- La recepcionista puede leer registros pero NO puede editar ni crear (su acceso es read-only).
- El campo `is_editable` depende de si han pasado menos de 24h desde `created_at`. El `clinic_owner` siempre puede editar.
- Los campos `audit_info.last_modified_by` y `last_modified_at` se completan solo si el registro ha sido modificado despues de la creacion.
- El `record_id` debe pertenecer al `patient_id` especificado en la URL (validacion cruzada para prevenir acceso indirecto entre pacientes).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Registro sin adjuntos | `attachments: []` en la respuesta |
| Registro sin diagnosticos vinculados | `diagnoses: []` en la respuesta |
| Registro sin dientes vinculados | `tooth_numbers: []`, `teeth_details: []` |
| Registro sin cita vinculada | `appointment_id: null`, `appointment: null` |
| Adjunto con URL de S3 expirada o inaccesible | Generar nueva URL pre-firmada (siempre regenerar, no cachear) |
| Registro de mas de 24h visto por clinic_owner | `is_editable: true`, `edit_deadline: null` (sin limite para clinic_owner) |
| patient_id correcto pero record_id pertenece a otro paciente | Retornar 404 (no revelar que el record existe para otro paciente) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `audit_logs`: INSERT — entrada de auditoria de lectura PHI

**Example query (SQLAlchemy):**
```python
stmt = (
    select(ClinicalRecord)
    .options(
        selectinload(ClinicalRecord.diagnoses),
        selectinload(ClinicalRecord.teeth),
        selectinload(ClinicalRecord.attachments),
        joinedload(ClinicalRecord.doctor),
        joinedload(ClinicalRecord.appointment),
    )
    .where(
        ClinicalRecord.id == record_id,
        ClinicalRecord.patient_id == patient_id,
        ClinicalRecord.tenant_id == tenant_id,
    )
)
result = await session.execute(stmt)
record = result.scalar_one_or_none()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:clinical_record:{record_id}`: GET — lectura desde cache si disponible, SET si cache miss

**Cache TTL:** 5 minutos (registros clinicos son relativamente estables; se invalida en actualización)

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| audit | clinical_record.read | { record_id, patient_id, user_id, role, tenant_id, timestamp } | Siempre al leer PHI |

### Audit Log

**Audit entry:** Yes

- **Action:** read
- **Resource:** clinical_record
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 150ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** Redis cache con TTL corto
- **Cache key:** `tenant:{tenant_id}:clinical_record:{record_id}`
- **TTL:** 300s (5 minutos)
- **Invalidation:** Al actualizar el registro (CR-04) o al agregar adjuntos

### Database Performance

**Queries executed:** 2-3 (1 query con JOINs para registro + relaciones, 1 para audit log)

**Indexes required:**
- `clinical_records.(id, patient_id, tenant_id)` — UNIQUE compuesto
- `clinical_record_diagnoses.clinical_record_id` — INDEX
- `clinical_record_teeth.clinical_record_id` — INDEX
- `clinical_record_attachments.clinical_record_id` — INDEX

**N+1 prevention:** Todas las relaciones cargadas en un query con `selectinload` / `joinedload`.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID | Prevenir inyeccion |
| record_id | Pydantic UUID | Prevenir inyeccion |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM con queries parametrizadas. Sin SQL raw.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `content` (historia clinica completa), `diagnoses` (codigos CIE-10 y descripciones), `tooth_numbers`, `attachments` (radiografias y documentos clinicos)

**Audit requirement:** All access logged — toda lectura de PHI auditada.

---

## Testing

### Test Cases

#### Happy Path
1. Doctor lee registro propio exitosamente
   - **Given:** Doctor autenticado, registro existente con diagnoses y attachments
   - **When:** GET /api/v1/patients/{pid}/clinical-records/{rid}
   - **Then:** 200 OK, todos los campos presentes, URLs de adjuntos generadas, audit log registrado

2. Recepcionista lee registro (solo lectura)
   - **Given:** Recepcionista autenticada, registro existente
   - **When:** GET con token de recepcionista
   - **Then:** 200 OK, respuesta completa, audit log registrado

3. Registro sin adjuntos ni diagnoses
   - **Given:** Registro creado sin tooth_numbers ni diagnosis_ids
   - **When:** GET del registro
   - **Then:** 200 OK, `attachments: []`, `diagnoses: []`, `teeth_details: []`

#### Edge Cases
1. Registro de mas de 24h visto por clinic_owner
   - **Given:** Registro con created_at hace 25 horas, viewer es clinic_owner
   - **When:** GET del registro
   - **Then:** 200 OK, `is_editable: true`, `edit_deadline: null`

2. Registro de mas de 24h visto por doctor
   - **Given:** Registro con created_at hace 25 horas, viewer es doctor
   - **When:** GET del registro
   - **Then:** 200 OK, `is_editable: false`

#### Error Cases
1. record_id pertenece a otro paciente
   - **Given:** record_id valido pero de otro paciente
   - **When:** GET con patient_id incorrecto
   - **Then:** 404 Not Found

2. Paciente inexistente
   - **Given:** patient_id que no existe en el tenant
   - **When:** GET del endpoint
   - **Then:** 404 Not Found

3. Token invalido
   - **Given:** Token expirado
   - **When:** GET sin Authorization valido
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** Doctor activo, asistente activo, recepcionista activa, clinic_owner

**Patients/Entities:** Paciente activo con al menos 2 registros clinicos (uno reciente, uno de mas de 24h), diagnostico activo, adjunto de prueba en S3 mock

### Mocking Strategy

- **Redis:** fakeredis para cache en unit tests
- **S3:** moto o localstack para simular generacion de presigned URLs
- **Audit service:** Mock que verifica llamada con parametros correctos

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Registro retornado con todos los campos: diagnoses, teeth_details, doctor, appointment, attachments
- [ ] URLs de adjuntos son presigned con TTL 1h
- [ ] `is_editable` calculado correctamente segun 24h y rol
- [ ] Auditoria registrada en toda lectura (doctor, assistant, receptionist)
- [ ] 404 retornado cuando record no pertenece al patient_id especificado
- [ ] Recepcionista puede leer pero no editar (solo-lectura verificado a nivel de rol)
- [ ] Cache con TTL 5min funcional; invalidado al actualizar registro
- [ ] All test cases pass
- [ ] Performance targets met (< 400ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verified (PHI)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Edicion del registro (ver CR-04)
- Listado de registros (ver CR-03)
- Descarga directa de adjuntos (manejo via presigned URL de S3)
- Compartir registros con pacientes (ver portal/)

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
- [x] Caching strategy stated (tenant-namespaced)
- [x] DB queries optimized (indexes listed, selectinload)
- [x] Pagination applied where needed (N/A)

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
