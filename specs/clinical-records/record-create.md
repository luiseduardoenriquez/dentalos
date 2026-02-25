# Crear Registro Clinico (CR-01)

---

## Overview

**Feature:** Crea una nueva entrada de registro clinico para un paciente. Soporta multiples tipos (anamnesis, examen, nota de evolucion, procedimiento), vincula opcionalmente a cita en curso, diente y diagnostico, y permite pre-llenado desde plantilla de evolucion.

**Domain:** clinical-records

**Priority:** High

**Dependencies:** patients/patient-get.md, appointments/appointment-get.md (opcional), odontogram/tooth-get.md (opcional), CR-15 (evolution-template-get.md), infra/audit-logging.md, infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant
- **Tenant context:** Required — resuelto desde JWT
- **Special rules:** El doctor solo puede crear registros dentro de su tenant. El asistente puede crear registros pero no diagnosticos independientes. PHI — toda escritura es auditada.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/clinical-records
```

**Rate Limiting:**
- 60 requests por minuto por usuario
- Redis sliding window: `tenant:{tenant_id}:rate:clinical_records_write:{user_id}`

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
  "type": "string (required) — anamnesis | examination | evolution_note | procedure",
  "content": "object | string (required) — contenido del registro (rich text o JSON estructurado segun tipo)",
  "appointment_id": "UUID (optional) — cita a la que se vincula el registro",
  "tooth_numbers": "array<integer> (optional) — numeros de dientes FDI involucrados [11, 12, 21]",
  "diagnosis_ids": "array<UUID> (optional) — diagnosticos vinculados a este registro",
  "template_id": "UUID (optional) — solo para type=evolution_note; ID de plantilla para pre-llenado (CR-15)",
  "template_variables": "object (optional) — valores para variables de la plantilla si se usa template_id"
}
```

**Estructura de `content` por tipo:**

Para `type=examination`:
```json
{
  "chief_complaint": "string",
  "extraoral": { "observations": "string", "lymph_nodes": "string" },
  "intraoral": { "soft_tissues": "string", "hard_tissues": "string", "periodontium": "string" },
  "radiographic_findings": "string"
}
```

Para `type=evolution_note`:
```json
{
  "subjective": "string (queja del paciente)",
  "objective": "string (hallazgos clinicos)",
  "assessment": "string (evaluacion del doctor)",
  "plan": "string (plan de tratamiento)"
}
```

Para `type=procedure`:
```json
{
  "description": "string",
  "cups_code": "string (optional)",
  "materials_used": [],
  "notes": "string"
}
```

Para `type=anamnesis`: usar CR-05 (`POST /api/v1/patients/{patient_id}/anamnesis`) en su lugar.

**Example Request (evolution_note con template):**
```json
{
  "type": "evolution_note",
  "content": {
    "subjective": "Paciente refiere dolor leve en cuadrante superior derecho.",
    "objective": "Sensibilidad a percusion en diente 16. Sin movilidad.",
    "assessment": "Probable pulpitis reversible diente 16.",
    "plan": "Radiografia periapical. Valorar endodoncia vs restauracion."
  },
  "appointment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "tooth_numbers": [16],
  "diagnosis_ids": ["d9e8f7a6-b5c4-3210-fedc-ba9876543210"],
  "template_id": null,
  "template_variables": null
}
```

**Example Request (examination):**
```json
{
  "type": "examination",
  "content": {
    "chief_complaint": "Dolor en muela del juicio inferior izquierda.",
    "extraoral": {
      "observations": "Sin alteraciones visibles.",
      "lymph_nodes": "Sin linfadenopatia."
    },
    "intraoral": {
      "soft_tissues": "Encias con leve inflamacion en zona del 38.",
      "hard_tissues": "Diente 38 semierupcionado.",
      "periodontium": "Normal en resto de la cavidad oral."
    },
    "radiographic_findings": "Panoramica: diente 38 impactado mesioangulado."
  },
  "appointment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "tooth_numbers": [38],
  "diagnosis_ids": []
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
  "type": "string",
  "content": "object",
  "appointment_id": "UUID | null",
  "tooth_numbers": "array<integer>",
  "diagnosis_ids": "array<UUID>",
  "template_id": "UUID | null",
  "doctor": {
    "id": "UUID",
    "name": "string",
    "specialty": "string | null"
  },
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime",
  "is_editable": "boolean — false si han pasado mas de 24h desde creacion",
  "edit_deadline": "ISO8601 datetime — momento hasta el cual el registro puede editarse"
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
  "tooth_numbers": [16],
  "diagnosis_ids": ["d9e8f7a6-b5c4-3210-fedc-ba9876543210"],
  "template_id": null,
  "doctor": {
    "id": "usr_doctor_001",
    "name": "Dra. Ana Martinez",
    "specialty": "Odontologia General"
  },
  "created_at": "2026-02-24T10:30:00Z",
  "updated_at": "2026-02-24T10:30:00Z",
  "is_editable": true,
  "edit_deadline": "2026-02-25T10:30:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Campos faltantes, tipo invalido, o combinacion invalida de campos.

```json
{
  "error": "invalid_input",
  "message": "Los datos proporcionados no son validos.",
  "details": {
    "type": ["El tipo de registro es obligatorio."],
    "content": ["El contenido del registro es obligatorio."]
  }
}
```

#### 400 Bad Request — tipo anamnesis via este endpoint
```json
{
  "error": "use_anamnesis_endpoint",
  "message": "Para crear o actualizar la anamnesis del paciente use POST /api/v1/patients/{patient_id}/anamnesis."
}
```

#### 401 Unauthorized
**When:** Token ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Rol no tiene permiso para crear registros clinicos (ej. receptionist).

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para crear registros clinicos."
}
```

#### 404 Not Found
**When:** `patient_id` no existe en el tenant, `appointment_id` no existe, `tooth_numbers` contienen diente no registrado, o `diagnosis_ids` contienen diagnostico inexistente.

```json
{
  "error": "not_found",
  "message": "El paciente especificado no existe.",
  "details": { "patient_id": "550e8400-e29b-41d4-a716-446655440000" }
}
```

#### 422 Unprocessable Entity
**When:** Fallo de validacion de negocio (ej. template_id con type != evolution_note).

```json
{
  "error": "validation_failed",
  "message": "Error de validacion en los datos del registro.",
  "details": {
    "template_id": ["El uso de plantilla solo es valido para registros de tipo 'evolution_note'."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido. Ver `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Error inesperado al persistir el registro o emitir el evento de auditoria.

---

## Business Logic

**Step-by-step process:**

1. Validar input contra schema Pydantic (`ClinicalRecordCreateSchema`).
2. Resolver tenant desde JWT. Verificar que el usuario tiene rol `doctor` o `assistant`.
3. Verificar que `patient_id` existe en el schema del tenant (`tenant_{id}.patients`).
4. Si `appointment_id` provisto: verificar que existe y pertenece al mismo `patient_id` y tenant.
5. Si `tooth_numbers` provistos: verificar que cada numero es un diente FDI valido (11-48). Opcional: verificar que el diente existe en el odontograma del paciente.
6. Si `diagnosis_ids` provistos: verificar que cada diagnostico existe y pertenece al paciente.
7. Si `type == 'anamnesis'`: retornar 400 indicando usar endpoint dedicado (CR-05).
8. Si `template_id` provisto y `type != 'evolution_note'`: retornar 422.
9. Si `template_id` provisto: cargar la plantilla (CR-15), aplicar `template_variables` y pre-llenar `content` con los valores interpolados. Los campos en `content` del body override los del template.
10. Si `appointment_id` es `null` y hay una cita en estado `in_progress` para el paciente en la cita actual del doctor: auto-vincular a esa cita.
11. Persistir registro en `tenant_{id}.clinical_records` con `doctor_id = current_user.id`.
12. Si `diagnosis_ids` provistos: insertar filas en `clinical_record_diagnoses` (tabla relacional).
13. Si `tooth_numbers` provistos: insertar filas en `clinical_record_teeth` (tabla relacional).
14. Registrar entrada de auditoria (action=create, resource=clinical_record, phi=true).
15. Invalidar cache del listado de registros del paciente.
16. Retornar 201 con el registro creado.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| type | Requerido. Enum: anamnesis, examination, evolution_note, procedure | "El tipo de registro es obligatorio." / "Tipo de registro invalido." |
| content | Requerido. Objeto no vacio. | "El contenido del registro es obligatorio." |
| tooth_numbers | Opcional. Cada elemento entre 11 y 48 (numeracion FDI). | "Numero de diente invalido: {n}. Use numeracion FDI (11-48)." |
| template_id | Solo valido si type=evolution_note. | "El uso de plantilla solo es valido para notas de evolucion." |
| appointment_id | Debe pertenecer al mismo patient_id. | "La cita especificada no corresponde a este paciente." |

**Business Rules:**

- Los registros de tipo `anamnesis` creados via este endpoint son rechazados con redirección al endpoint dedicado (CR-05).
- Un registro clinico no puede ser editado despues de 24 horas de su creacion, salvo por `clinic_owner` (ver CR-04).
- El `doctor_id` del registro siempre es el usuario autenticado (no puede impersonarse otro doctor).
- Si el asistente crea el registro, `doctor_id` se asigna al doctor de la cita en curso si existe; si no, se usa el id del asistente y queda pendiente de firma.
- El campo `edit_deadline` se calcula como `created_at + 24h` y se retorna para que el frontend muestre el tiempo restante de edicion.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| `appointment_id` no provisto pero hay cita en progreso | Auto-vincular a la cita activa del doctor |
| `tooth_numbers` contiene dientes no en el odontograma | Crear registro igualmente; los dientes nuevos NO se agregan automaticamente al odontograma |
| `template_variables` tiene claves no existentes en el template | Ignorar claves desconocidas; interpolar solo las validas |
| `diagnosis_ids` lista vacia `[]` | Crear registro sin vinculos de diagnostico (valido) |
| Paciente inactivo (dado de baja) | Retornar 404 (no revelar estado) |
| Content con campos extra no definidos en el schema del tipo | Aceptar y almacenar tal cual (schema flexible para compatibilidad futura) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `clinical_records`: INSERT — nuevo registro clinico
- `clinical_record_diagnoses`: INSERT (bulk) — filas de relacion registro-diagnostico si `diagnosis_ids` no es vacio
- `clinical_record_teeth`: INSERT (bulk) — filas de relacion registro-diente si `tooth_numbers` no es vacio
- `audit_logs`: INSERT — entrada de auditoria PHI

**Example query (SQLAlchemy):**
```python
new_record = ClinicalRecord(
    patient_id=patient_id,
    doctor_id=current_user.id,
    type=body.type,
    content=body.content,
    appointment_id=body.appointment_id,
    template_id=body.template_id,
    tenant_id=tenant_id,
)
session.add(new_record)
await session.flush()

if body.tooth_numbers:
    teeth_rows = [
        ClinicalRecordTooth(clinical_record_id=new_record.id, tooth_number=n)
        for n in body.tooth_numbers
    ]
    session.add_all(teeth_rows)

if body.diagnosis_ids:
    diag_rows = [
        ClinicalRecordDiagnosis(clinical_record_id=new_record.id, diagnosis_id=did)
        for did in body.diagnosis_ids
    ]
    session.add_all(diag_rows)

await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:clinical_records:list`: DELETE — invalidar listado paginado del paciente

**Cache TTL:** N/A (invalidacion, no SET)

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| audit | clinical_record.created | { record_id, patient_id, doctor_id, type, tenant_id, timestamp } | Siempre al crear |
| analytics | clinical_record.created | { tenant_id, type, has_template, tooth_count, timestamp } | Siempre al crear |

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** clinical_record
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 500ms

### Caching Strategy
- **Strategy:** No caching de escritura. Invalidacion de cache del listado.
- **Cache key:** `tenant:{tenant_id}:patient:{patient_id}:clinical_records:list`
- **TTL:** N/A
- **Invalidation:** Al crear, actualizar o eliminar cualquier registro del paciente

### Database Performance

**Queries executed:** 4-6 (verificar paciente, verificar cita, insertar registro, insertar relaciones, audit log)

**Indexes required:**
- `clinical_records.patient_id` — INDEX
- `clinical_records.doctor_id` — INDEX
- `clinical_records.appointment_id` — INDEX
- `clinical_records.type` — INDEX
- `clinical_records.created_at` — INDEX (para ordenamiento en listado)
- `clinical_record_diagnoses.(clinical_record_id, diagnosis_id)` — UNIQUE
- `clinical_record_teeth.(clinical_record_id, tooth_number)` — UNIQUE

**N+1 prevention:** Relaciones insertadas en bulk con `session.add_all()`.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| content | Pydantic validator + bleach para campos rich text | Prevenir XSS en contenido HTML |
| tooth_numbers | Pydantic list[int], rango 11-48 | Prevenir valores fuera de rango |
| type | Pydantic Literal enum | Prevenir valores arbitrarios |
| patient_id | Pydantic UUID | Prevenir inyeccion |
| appointment_id | Pydantic UUID, optional | Prevenir inyeccion |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM con queries parametrizadas. Sin SQL raw.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic. Campos rich text sanitizados con bleach al escribir.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `content` (contiene informacion clinica del paciente), `tooth_numbers`, `diagnosis_ids`

**Audit requirement:** All access logged — toda escritura de PHI auditada con user_id, tenant_id, patient_id, timestamp y accion.

---

## Testing

### Test Cases

#### Happy Path
1. Crear nota de evolucion exitosamente
   - **Given:** Doctor autenticado, paciente activo, cita en curso
   - **When:** POST con type=evolution_note, content valido, appointment_id valido
   - **Then:** 201 Created, registro persistido, audit log generado, cache invalidado

2. Crear examen clinico con vinculos a dientes
   - **Given:** Doctor autenticado, paciente activo
   - **When:** POST con type=examination, tooth_numbers=[16, 17]
   - **Then:** 201 Created, clinical_record_teeth con 2 filas insertadas

3. Nota de evolucion con template
   - **Given:** Doctor autenticado, template_id valido tipo evolution_note
   - **When:** POST con type=evolution_note, template_id, template_variables
   - **Then:** 201 Created, content pre-llenado con valores del template

4. Auto-vinculo a cita en progreso
   - **Given:** Doctor con cita `in_progress` para el paciente
   - **When:** POST sin appointment_id
   - **Then:** 201 Created, appointment_id auto-asignado a la cita activa

#### Edge Cases
1. Content con campos extra
   - **Given:** Body con campos no definidos en el schema del tipo
   - **When:** POST con type=examination, content con campo extra `foo: "bar"`
   - **Then:** 201 Created, campo extra almacenado sin error

2. tooth_numbers con dientes no en odontograma
   - **Given:** Paciente sin diente 48 registrado en odontograma
   - **When:** POST con tooth_numbers=[48]
   - **Then:** 201 Created, relacion clinical_record_teeth creada, odontograma no modificado

#### Error Cases
1. Tipo anamnesis enviado a este endpoint
   - **Given:** Doctor autenticado
   - **When:** POST con type=anamnesis
   - **Then:** 400 con error use_anamnesis_endpoint

2. template_id con type != evolution_note
   - **Given:** Doctor autenticado
   - **When:** POST con type=examination, template_id valido
   - **Then:** 422 con mensaje de validacion

3. patient_id inexistente
   - **Given:** Doctor autenticado
   - **When:** POST con patient_id que no existe en el tenant
   - **Then:** 404 con error not_found

4. Rol sin permiso (receptionist)
   - **Given:** Usuario con rol receptionist
   - **When:** POST a este endpoint
   - **Then:** 403 Forbidden

### Test Data Requirements

**Users:** Doctor activo, asistente activo, recepcionista activo (para probar 403)

**Patients/Entities:** Paciente activo con odontograma inicializado, cita en estado `in_progress`, diagnostico activo vinculado al paciente, plantilla de evolucion tipo CR-15

### Mocking Strategy

- **Redis:** fakeredis para rate limiting en unit tests
- **Audit service:** Mock que verifica que se llama con los parametros correctos
- **RabbitMQ:** Mock de publisher; verificar que jobs son encolados con payload correcto

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Registro clinico creado exitosamente para todos los tipos validos (examination, evolution_note, procedure)
- [ ] type=anamnesis es rechazado con redirección al endpoint correcto
- [ ] Auto-vinculo a cita en progreso funciona cuando appointment_id no se provee
- [ ] template_id pre-llena content correctamente (CR-15)
- [ ] Relaciones con dientes y diagnosticos se persisten en tablas relacionales
- [ ] Audit log generado en cada escritura exitosa con PHI
- [ ] Cache del listado invalidado tras creacion
- [ ] edit_deadline retornado correctamente (created_at + 24h)
- [ ] All test cases pass
- [ ] Performance targets met (< 500ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creacion de anamnesis (ver CR-05)
- Creacion de procedimientos con CUPS codes (ver CR-12)
- Creacion de diagnosticos independientes (ver CR-07)
- Adjuntar archivos a registros clinicos (endpoint separado de attachments)
- Firma digital de registros clinicos (post-MVP)

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
- [x] Input sanitization defined (Pydantic + bleach)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail for clinical data access

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (tenant-namespaced invalidation)
- [x] DB queries optimized (indexes listed)
- [x] Pagination applied where needed (N/A — creacion)

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
