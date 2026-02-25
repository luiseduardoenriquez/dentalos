# Obtener Detalle de Procedimiento (CR-14)

---

## Overview

**Feature:** Obtiene el detalle completo de un procedimiento dental, incluyendo descripcion completa, materiales usados con numeros de lote, item de plan de tratamiento vinculado, plantilla de evolucion con variables interpoladas, diagnosticos relacionados y trazabilidad completa. Toda lectura de PHI es auditada.

**Domain:** clinical-records

**Priority:** High

**Dependencies:** CR-12 (procedure-create.md), CR-13 (procedure-list.md), CR-15 (evolution-template-get.md), CR-07 (diagnosis-create.md), infra/audit-logging.md, infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant
- **Tenant context:** Required — resuelto desde JWT
- **Special rules:** La recepcionista NO tiene acceso al detalle de procedimientos. Toda lectura es auditada (PHI).

---

## Endpoint

```
GET /api/v1/patients/{patient_id}/procedures/{procedure_id}
```

**Rate Limiting:**
- 120 requests por minuto por usuario
- Redis sliding window: `tenant:{tenant_id}:rate:procedures_read:{user_id}`

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
| procedure_id | Yes | UUID | Debe pertenecer al patient_id | ID del procedimiento | proc_e1f2a3b4-c5d6-7890-ef12-345678901234 |

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
  "cups_code": "string",
  "cups_description": "string — descripcion oficial del catalogo CUPS",
  "custom_description": "string | null",
  "tooth_number": "integer | null",
  "tooth_notation_fdi": "string | null",
  "zones": "array<string>",
  "materials_used": [
    {
      "name": "string",
      "brand": "string | null",
      "lot_number": "string | null — numero de lote para trazabilidad",
      "quantity": "number | null",
      "unit": "string | null"
    }
  ],
  "doctor": {
    "id": "UUID",
    "name": "string",
    "specialty": "string | null",
    "license_number": "string | null"
  },
  "duration_minutes": "integer | null",
  "notes": "string | null",
  "appointment_id": "UUID | null",
  "appointment": {
    "id": "UUID",
    "date": "ISO8601 date",
    "time": "HH:MM"
  },
  "treatment_plan_item": {
    "id": "UUID",
    "description": "string",
    "treatment_plan_id": "UUID",
    "treatment_plan_name": "string",
    "status": "string",
    "completed_at": "ISO8601 datetime"
  },
  "evolution_note": {
    "id": "UUID",
    "template_id": "UUID | null",
    "template_name": "string | null",
    "content": "object — contenido completo de la nota con variables interpoladas",
    "template_variables": "object | null — variables tal como fueron ingresadas",
    "created_at": "ISO8601 datetime"
  },
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
  "odontogram_changes": [
    {
      "tooth_number": "integer",
      "old_condition": "string",
      "new_condition": "string",
      "changed_at": "ISO8601 datetime"
    }
  ],
  "billing": {
    "invoice_item_id": "UUID | null",
    "cost": "number | null",
    "currency": "string | null",
    "invoice_id": "UUID | null",
    "invoice_status": "string | null"
  },
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime",
  "created_by": {
    "id": "UUID",
    "name": "string",
    "role": "string — usuario que registro el procedimiento (puede ser asistente)"
  }
}
```

**Example:**
```json
{
  "id": "proc_e1f2a3b4-c5d6-7890-ef12-345678901234",
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "cups_code": "89.01.02.01",
  "cups_description": "Restauracion en resina compuesta de una superficie en diente permanente",
  "custom_description": "Restauracion clase I oclusal diente 16",
  "tooth_number": 16,
  "tooth_notation_fdi": "16",
  "zones": ["oclusal"],
  "materials_used": [
    {
      "name": "Resina compuesta A2",
      "brand": "3M Filtek Z350",
      "lot_number": "LOT2026A1234",
      "quantity": 2.5,
      "unit": "g"
    },
    {
      "name": "Adhesivo",
      "brand": "Scotchbond Universal",
      "lot_number": "LOT2026B5678",
      "quantity": 1.0,
      "unit": "ml"
    }
  ],
  "doctor": {
    "id": "usr_doctor_001",
    "name": "Dra. Ana Martinez",
    "specialty": "Odontologia General",
    "license_number": "CO-12345"
  },
  "duration_minutes": 45,
  "notes": "Restauracion directa clase I. Diente vital sin sintomatologia. Ajuste oclusal realizado.",
  "appointment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "appointment": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "date": "2026-02-24",
    "time": "10:00"
  },
  "treatment_plan_item": {
    "id": "tpi_789abc12-3456-7890-abcd-ef1234567890",
    "description": "Restauracion resina diente 16",
    "treatment_plan_id": "tp_abc12345-6789-0abc-def1-234567890abc",
    "treatment_plan_name": "Plan de tratamiento integral 2026",
    "status": "completed",
    "completed_at": "2026-02-24T11:00:00Z"
  },
  "evolution_note": {
    "id": "cr_nota_abc123",
    "template_id": "evt_abc12345-6789-0abc-def1-234567890abc",
    "template_name": "Nota de Evolucion - Restauracion",
    "content": {
      "subjective": "Paciente asintomatico. Viene para procedimiento programado.",
      "objective": "Diente 16: caries oclusal clase I. Diente vital.",
      "assessment": "Restauracion clase I oclusal diente 16.",
      "plan": "Restauracion directa resina compuesta A2. Seguimiento en 3 meses."
    },
    "template_variables": {
      "procedimiento_realizado": "Restauracion clase I oclusal",
      "diente": "16",
      "material": "Resina compuesta A2 Filtek Z350",
      "anestesia": "No",
      "complicaciones": "Sin complicaciones"
    },
    "created_at": "2026-02-24T11:00:00Z"
  },
  "diagnoses": [
    {
      "id": "dx_d9e8f7a6-b5c4-3210-fedc-ba9876543210",
      "cie10_code": "K02.1",
      "cie10_description": "Caries de la dentina",
      "tooth_number": 16,
      "severity": "moderate",
      "status": "resolved"
    }
  ],
  "odontogram_changes": [
    {
      "tooth_number": 16,
      "old_condition": "caries",
      "new_condition": "restauracion_resina",
      "changed_at": "2026-02-24T11:00:00Z"
    }
  ],
  "billing": {
    "invoice_item_id": "inv_item_abc123",
    "cost": 150000.00,
    "currency": "COP",
    "invoice_id": "inv_xyz789",
    "invoice_status": "draft"
  },
  "created_at": "2026-02-24T11:00:00Z",
  "updated_at": "2026-02-24T11:00:00Z",
  "created_by": {
    "id": "usr_doctor_001",
    "name": "Dra. Ana Martinez",
    "role": "doctor"
  }
}
```

### Error Responses

#### 401 Unauthorized
**When:** Token ausente, expirado o invalido.

#### 403 Forbidden
**When:** Rol sin acceso (receptionist).

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para acceder al detalle de procedimientos."
}
```

#### 404 Not Found
**When:** `patient_id` no existe, o `procedure_id` no existe o no pertenece al `patient_id`.

```json
{
  "error": "not_found",
  "message": "El procedimiento especificado no existe."
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido.

#### 500 Internal Server Error
**When:** Error inesperado al recuperar el procedimiento.

---

## Business Logic

**Step-by-step process:**

1. Validar parametros de URL (UUIDs validos).
2. Resolver tenant desde JWT. Verificar rol (doctor o assistant). Receptionist retorna 403.
3. Verificar que `patient_id` existe en el tenant.
4. Buscar procedimiento: `SELECT * FROM procedures WHERE id=procedure_id AND patient_id=patient_id AND tenant_id=tenant_id`. Si no encontrado: 404.
5. Cargar relaciones con selectinload/joinedload:
   - `doctor` (JOIN con users)
   - `appointment` (JOIN si appointment_id no es null)
   - `treatment_plan_item` + `treatment_plan` (JOIN si treatment_plan_item_id no es null)
   - `evolution_note` / `clinical_record` vinculado al procedimiento
   - `diagnoses` vinculados al appointment o al paciente en el contexto de este procedimiento
   - `odontogram_changes` (cambios al odontograma generados por este procedimiento)
6. Cargar datos de facturacion: buscar `billing_items` vinculados al `procedure_id`.
7. Registrar entrada de auditoria (action=read, resource=procedure, phi=true).
8. Retornar 200 con el detalle completo.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| patient_id | UUID valido, paciente existente en tenant | "El paciente especificado no existe." |
| procedure_id | UUID valido, procedimiento existente perteneciente al patient_id | "El procedimiento especificado no existe." |

**Business Rules:**

- La recepcionista no puede ver el detalle de procedimientos (contiene informacion clinica y de materiales).
- El `procedure_id` debe pertenecer al `patient_id` especificado en la URL (validacion cruzada para prevenir acceso indirecto entre pacientes).
- Los diagnosticos en `diagnoses` son los diagnosticos que estaban activos para ese paciente/diente en el momento del procedimiento. Se obtienen desde la relacion directa en `procedure_diagnoses` o desde el contexto del appointment.
- `odontogram_changes` muestra los cambios automaticos al odontograma generados por este procedimiento (almacenados al momento de la creacion).
- `billing.invoice_item_id` puede ser null si la facturacion no ha sido generada aun para este procedimiento.
- `evolution_note.template_variables` retorna los valores tal como fueron ingresados por el usuario (para referencia y re-uso futuro).
- `created_by` puede ser diferente de `doctor` cuando un asistente registro el procedimiento.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Procedimiento sin materials_used | `materials_used: []` |
| Procedimiento sin treatment_plan_item | `treatment_plan_item: null` |
| Procedimiento sin evolution_note | `evolution_note: null` |
| Procedimiento sin diagnosticos vinculados | `diagnoses: []` |
| Procedimiento sin cambios al odontograma | `odontogram_changes: []` |
| Procedimiento sin facturacion | `billing: { invoice_item_id: null, cost: null, currency: null, invoice_id: null, invoice_status: null }` |
| procedure_id pertenece a otro paciente | Retornar 404 (no revelar que el procedimiento existe para otro paciente) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `audit_logs`: INSERT — entrada de auditoria de lectura PHI

**Example query (SQLAlchemy):**
```python
stmt = (
    select(Procedure)
    .options(
        joinedload(Procedure.doctor),
        joinedload(Procedure.appointment),
        joinedload(Procedure.treatment_plan_item).joinedload(TreatmentPlanItem.treatment_plan),
        selectinload(Procedure.evolution_note),
        selectinload(Procedure.diagnoses),
        selectinload(Procedure.odontogram_changes),
    )
    .where(
        Procedure.id == procedure_id,
        Procedure.patient_id == patient_id,
        Procedure.tenant_id == tenant_id,
    )
)
result = await session.execute(stmt)
procedure = result.scalar_one_or_none()

if not procedure:
    raise ProcedureNotFoundException()

# Obtener datos de facturacion
billing_item = await session.scalar(
    select(BillingItem).where(
        BillingItem.procedure_id == procedure_id
    )
)
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:procedure:{procedure_id}`: GET — lectura desde cache; SET si cache miss

**Cache TTL:** 300s (5 minutos; invalidado si el procedimiento o sus relaciones se actualizan)

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| audit | procedure.read | { procedure_id, patient_id, user_id, role, tenant_id, timestamp } | Siempre al leer |

### Audit Log

**Audit entry:** Yes

- **Action:** read
- **Resource:** procedure
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 150ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** Redis cache con TTL de 5 minutos
- **Cache key:** `tenant:{tenant_id}:procedure:{procedure_id}`
- **TTL:** 300s
- **Invalidation:** Al actualizar el procedimiento o sus relaciones

### Database Performance

**Queries executed:** 2-3 (1 query con JOINs para procedimiento + relaciones, 1 para billing, 1 para audit log)

**Indexes required:**
- `procedures.(id, patient_id, tenant_id)` — UNIQUE compuesto
- `billing_items.procedure_id` — INDEX
- `procedure_diagnoses.procedure_id` — INDEX
- `procedure_odontogram_changes.procedure_id` — INDEX

**N+1 prevention:** Todas las relaciones cargadas con `selectinload` y `joinedload` en un unico query.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| patient_id | Pydantic UUID | Prevenir inyeccion |
| procedure_id | Pydantic UUID | Prevenir inyeccion |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM con queries parametrizadas. Sin SQL raw.

### XSS Prevention

**Output encoding:** Todos los strings escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `cups_code` + descripcion (tipo de procedimiento realizado), `materials_used` (con numeros de lote), `notes` clinicas, `evolution_note.content`, `diagnoses` (codigos CIE-10), `odontogram_changes`

**Audit requirement:** All access logged — toda lectura de PHI auditada.

---

## Testing

### Test Cases

#### Happy Path
1. Obtener procedimiento completo con todas las relaciones
   - **Given:** Doctor autenticado, procedimiento con treatment_plan_item, evolution_note, diagnoses y odontogram_changes
   - **When:** GET /api/v1/patients/{pid}/procedures/{proc_id}
   - **Then:** 200 OK, todos los campos presentes, audit log registrado

2. Procedimiento registrado por asistente
   - **Given:** Doctor autenticado como viewer, procedimiento creado por asistente
   - **When:** GET del procedimiento
   - **Then:** 200 OK, `doctor` muestra el doctor que realizo el procedimiento, `created_by` muestra la asistente

3. Procedimiento con billing info
   - **Given:** Procedimiento con item de factura generado
   - **When:** GET del procedimiento
   - **Then:** 200 OK, `billing.cost` y `billing.invoice_id` presentes

4. Procedimiento sin relaciones opcionales
   - **Given:** Procedimiento creado sin treatment_plan_item ni evolution_template
   - **When:** GET del procedimiento
   - **Then:** 200 OK, campos opcionales null o vacios, sin errores

#### Edge Cases
1. Procedimiento sin materiales
   - **Given:** Procedimiento sin materials_used
   - **When:** GET del procedimiento
   - **Then:** 200 OK, `materials_used: []`

2. Procedimiento sin cambios al odontograma
   - **Given:** Procedimiento cuyo tipo no implica cambios de condicion
   - **When:** GET del procedimiento
   - **Then:** 200 OK, `odontogram_changes: []`

3. Cache hit en segunda solicitud
   - **Given:** Primera solicitud ya cacheada
   - **When:** Segunda solicitud GET del mismo procedimiento
   - **Then:** 200 OK, respuesta desde cache (< 50ms), audit log registrado igualmente

#### Error Cases
1. procedure_id pertenece a otro paciente
   - **Given:** procedure_id valido pero de otro paciente
   - **When:** GET con patient_id incorrecto
   - **Then:** 404 Not Found

2. Recepcionista intenta ver el detalle
   - **Given:** Usuario con rol receptionist
   - **When:** GET del endpoint
   - **Then:** 403 Forbidden

3. procedure_id inexistente
   - **Given:** procedure_id que no existe
   - **When:** GET del endpoint
   - **Then:** 404 Not Found

4. Token expirado
   - **Given:** JWT expirado
   - **When:** GET sin Authorization valido
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** Doctor activo, asistente activo, recepcionista (para probar 403)

**Patients/Entities:** Paciente con procedimiento completo (incluyendo materials_used con lot_numbers, treatment_plan_item completado, evolution_note generada, diagnostico K02.1, odontogram_change de caries a restauracion, billing_item con costo COP)

**Billing:** Item de factura vinculado al procedimiento de prueba

### Mocking Strategy

- **Redis:** fakeredis para cache en unit tests
- **Audit service:** Mock que verifica llamada con PHI=true y procedure resource
- **Billing service:** No mockear — leer directamente desde DB de test

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Procedimiento retornado con todos los campos definidos
- [ ] `materials_used` con numeros de lote correctamente incluidos
- [ ] `treatment_plan_item` con nombre del plan de tratamiento vinculado
- [ ] `evolution_note` con content completo y `template_variables` originales
- [ ] `diagnoses` vinculados al contexto del procedimiento
- [ ] `odontogram_changes` muestra cambios realizados por el procedimiento
- [ ] `billing` muestra costo e informacion de factura cuando disponible
- [ ] `created_by` diferenciado de `doctor` cuando asistente registro el procedimiento
- [ ] Recepcionista recibe 403
- [ ] 404 retornado cuando procedure no pertenece al patient_id
- [ ] Auditoria registrada en cada lectura
- [ ] Cache de 5min funcional
- [ ] All test cases pass
- [ ] Performance targets met (< 400ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verified (PHI)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Editar un procedimiento (los procedimientos son inmutables despues de la creacion)
- Listar procedimientos (ver CR-13)
- Crear procedimientos (ver CR-12)
- Facturacion directa del procedimiento (ver billing/)
- Ver el detalle de la nota de evolucion separada (usar CR-02 con el clinical_record.id de la nota)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models completos con billing, materials, evolution_note)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (doctor + assistant; NO receptionist)
- [x] Side effects listed
- [x] Examples provided (respuesta completa con todos los campos)

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (billing integrado como campo informativo)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, selectinload/joinedload)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (doctor + assistant; receptionist bloqueada)
- [x] Input sanitization defined (Pydantic UUIDs)
- [x] SQL injection prevented (SQLAlchemy ORM con selectinload)
- [x] No PHI exposure in logs or errors
- [x] Audit trail para PHI

### Hook 4: Performance & Scalability
- [x] Response time target definido (< 400ms)
- [x] Caching strategy stated (5min TTL)
- [x] DB queries optimized (selectinload/joinedload, indexes)
- [x] Pagination: N/A (detalle de un item)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified (procedimiento completo con todas las relaciones)
- [x] Mocking strategy for cache y audit
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
