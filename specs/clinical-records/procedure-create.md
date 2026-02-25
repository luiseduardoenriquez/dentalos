# Registrar Procedimiento Completado (CR-12)

---

## Overview

**Feature:** Registra un procedimiento dental completado para un paciente. Valida el codigo CUPS, vincula opcionalmente a un item de plan de tratamiento (marcandolo como completado), puede actualizar automaticamente el odontograma segun el tipo de procedimiento, y acepta plantilla de evolucion con variables pre-llenadas. Toda escritura es auditada (PHI).

**Domain:** clinical-records

**Priority:** High

**Dependencies:** CR-11 (cups-search.md), CR-15 (evolution-template-get.md), treatment-plans/TP-07 (mark-item-complete.md), odontogram/tooth-update.md, infra/audit-logging.md, infra/authentication-rules.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant
- **Tenant context:** Required — resuelto desde JWT
- **Special rules:** PHI. Toda escritura es auditada. El asistente puede registrar procedimientos pero no puede modificar el odontograma (esa parte es ejecutada por el sistema automaticamente segun el procedimiento).

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/procedures
```

**Rate Limiting:**
- 60 requests por minuto por usuario
- Redis sliding window: `tenant:{tenant_id}:rate:procedures_write:{user_id}`

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
  "cups_code": "string (required) — codigo CUPS valido del procedimiento",
  "description": "string (optional) — descripcion adicional del procedimiento. Default: descripcion oficial del catalogo CUPS",
  "tooth_number": "integer (optional) — numero de diente FDI involucrado (11-48)",
  "zones": "array<string> (optional) — zonas del diente: mesial | distal | oclusal | vestibular | lingual | palatino | cervical | total",
  "materials_used": [
    {
      "name": "string (required) — nombre del material",
      "brand": "string (optional) — marca del material",
      "lot_number": "string (optional) — numero de lote (trazabilidad)",
      "quantity": "number (optional) — cantidad usada",
      "unit": "string (optional) — unidad de medida (ml, g, unidad)"
    }
  ],
  "doctor_id": "UUID (optional) — ID del doctor que realizo el procedimiento. Default: usuario autenticado",
  "duration_minutes": "integer (optional) — duracion del procedimiento en minutos",
  "notes": "string (optional) — notas clinicas adicionales",
  "appointment_id": "UUID (optional) — cita a la que se vincula el procedimiento",
  "treatment_plan_item_id": "UUID (optional) — item del plan de tratamiento que este procedimiento completa",
  "evolution_template_id": "UUID (optional) — plantilla de evolucion pre-configurada para este tipo de procedimiento",
  "template_variables": "object (optional) — valores de las variables de la plantilla de evolucion"
}
```

**Example Request (restauracion con plan de tratamiento y plantilla):**
```json
{
  "cups_code": "89.01.02.01",
  "description": "Restauracion en resina compuesta clase I oclusal diente 16",
  "tooth_number": 16,
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
      "quantity": 1,
      "unit": "ml"
    }
  ],
  "doctor_id": "usr_doctor_001",
  "duration_minutes": 45,
  "notes": "Restauracion directa clase I. Diente vital sin sintomatologia. Ajuste oclusal realizado.",
  "appointment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "treatment_plan_item_id": "tpi_789abc12-3456-7890-abcd-ef1234567890",
  "evolution_template_id": "evt_abc12345-6789-0abc-def1-234567890abc",
  "template_variables": {
    "procedimiento_realizado": "Restauracion clase I oclusal",
    "diente": "16",
    "material": "Resina compuesta A2 Filtek Z350",
    "anestesia": "No",
    "complicaciones": "Sin complicaciones"
  }
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
  "cups_code": "string",
  "cups_description": "string — descripcion oficial del catalogo CUPS",
  "custom_description": "string | null",
  "tooth_number": "integer | null",
  "zones": "array<string>",
  "materials_used": "array<object>",
  "doctor": {
    "id": "UUID",
    "name": "string",
    "specialty": "string | null"
  },
  "duration_minutes": "integer | null",
  "notes": "string | null",
  "appointment_id": "UUID | null",
  "treatment_plan_item": {
    "id": "UUID",
    "description": "string",
    "status": "string — completed",
    "completed_at": "ISO8601 datetime"
  },
  "evolution_note": {
    "id": "UUID",
    "template_id": "UUID",
    "template_name": "string",
    "content": "object — nota de evolucion con variables interpoladas"
  },
  "odontogram_updated": "boolean — true si se actualizo el odontograma automaticamente",
  "odontogram_changes": [
    {
      "tooth_number": "integer",
      "old_condition": "string",
      "new_condition": "string"
    }
  ],
  "created_at": "ISO8601 datetime"
}
```

**Example:**
```json
{
  "id": "proc_e1f2a3b4-c5d6-7890-ef12-345678901234",
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "cups_code": "89.01.02.01",
  "cups_description": "Restauracion en resina compuesta de una superficie en diente permanente",
  "custom_description": "Restauracion en resina compuesta clase I oclusal diente 16",
  "tooth_number": 16,
  "zones": ["oclusal"],
  "materials_used": [
    {
      "name": "Resina compuesta A2",
      "brand": "3M Filtek Z350",
      "lot_number": "LOT2026A1234",
      "quantity": 2.5,
      "unit": "g"
    }
  ],
  "doctor": {
    "id": "usr_doctor_001",
    "name": "Dra. Ana Martinez",
    "specialty": "Odontologia General"
  },
  "duration_minutes": 45,
  "notes": "Restauracion directa clase I. Diente vital sin sintomatologia. Ajuste oclusal realizado.",
  "appointment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "treatment_plan_item": {
    "id": "tpi_789abc12-3456-7890-abcd-ef1234567890",
    "description": "Restauracion resina diente 16",
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
    }
  },
  "odontogram_updated": true,
  "odontogram_changes": [
    {
      "tooth_number": 16,
      "old_condition": "caries",
      "new_condition": "restauracion_resina"
    }
  ],
  "created_at": "2026-02-24T11:00:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Campos requeridos faltantes o codigo CUPS invalido.

```json
{
  "error": "invalid_input",
  "message": "Los datos del procedimiento no son validos.",
  "details": {
    "cups_code": ["El codigo CUPS '89.99.99.99' no existe en el catalogo."],
    "zones": ["Zona invalida 'superior'. Opciones: mesial, distal, oclusal, vestibular, lingual, palatino, cervical, total."]
  }
}
```

#### 401 Unauthorized
**When:** Token ausente, expirado o invalido.

#### 403 Forbidden
**When:** Rol sin permiso.

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para registrar procedimientos."
}
```

#### 404 Not Found
**When:** `patient_id`, `treatment_plan_item_id`, o `evolution_template_id` no existen.

```json
{
  "error": "not_found",
  "message": "El item de plan de tratamiento especificado no existe."
}
```

#### 409 Conflict
**When:** `treatment_plan_item_id` ya fue marcado como completado anteriormente.

```json
{
  "error": "already_completed",
  "message": "Este item del plan de tratamiento ya fue completado.",
  "details": {
    "treatment_plan_item_id": "tpi_789abc12-...",
    "completed_at": "2026-02-10T09:00:00Z",
    "completed_by_procedure_id": "proc_previo_123"
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido.

#### 500 Internal Server Error
**When:** Error inesperado al persistir el procedimiento o actualizar el odontograma.

---

## Business Logic

**Step-by-step process:**

1. Validar input contra schema Pydantic (`ProcedureCreateSchema`).
2. Resolver tenant desde JWT. Verificar rol (doctor o assistant).
3. Verificar que `patient_id` existe en el tenant.
4. Validar `cups_code` contra `public.cups_catalog`. Si no existe: retornar 400.
5. Si `tooth_number` provisto: verificar rango FDI (11-48).
6. Si `zones` provistos: validar cada zona contra el enum permitido.
7. Si `doctor_id` provisto en body y el usuario es `assistant`: verificar que el `doctor_id` es un doctor activo en el tenant.
8. Si `treatment_plan_item_id` provisto: verificar que existe y pertenece al `patient_id`. Si ya esta completed: retornar 409.
9. Si `evolution_template_id` provisto: cargar la plantilla (CR-15), interpolar `template_variables` en el contenido de la plantilla.
10. Insertar el procedimiento en `tenant_{id}.procedures`.
11. Si `treatment_plan_item_id` provisto: marcar el item como completado (llamada interna al servicio TP-07), estableciendo `completed_at = now()` y `procedure_id = nuevo_procedimiento.id`.
12. Si `evolution_template_id` provisto: crear automaticamente un registro clinico de tipo `evolution_note` con el contenido interpolado (vinculado al procedimiento y al appointment si existe). Guardar `clinical_record_id` en el procedimiento.
13. Auto-actualizar el odontograma si el tipo de procedimiento implica un cambio de condicion conocido:
    - Restauracion (CUPS 89.01.x) en diente con condicion `caries`: cambiar condicion a `restauracion_resina`.
    - Exodoncia (CUPS 89.13.x) en cualquier diente: cambiar condicion a `exodonte`.
    - Endodoncia (CUPS 89.03.x): cambiar condicion a `endodoncia`.
    - Protesis fija (corona CUPS 89.05.x): cambiar condicion a `corona`.
    - Si el diente no tiene condicion registrada o la condicion no coincide: no modificar el odontograma.
14. Registrar entrada de auditoria (action=create, resource=procedure, phi=true).
15. Invalidar cache del listado de procedimientos del paciente.
16. Retornar 201 con el procedimiento creado, incluyendo cambios al odontograma y nota de evolucion generada.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| cups_code | Requerido. Debe existir en `public.cups_catalog`. | "El codigo CUPS '{code}' no existe en el catalogo." |
| tooth_number | Opcional. Entero 11-48 si provisto. | "El numero de diente debe estar entre 11 y 48 (numeracion FDI)." |
| zones | Opcional. Cada elemento debe ser: mesial, distal, oclusal, vestibular, lingual, palatino, cervical, total. | "Zona invalida '{zone}'." |
| materials_used[].name | Requerido dentro del objeto si se provee el objeto. | "El nombre del material es obligatorio." |
| treatment_plan_item_id | Si provisto: debe existir, pertenecer al patient_id y estar en estado pendiente. | "El item de plan de tratamiento no existe o ya fue completado." |

**Business Rules:**

- El `doctor_id` del procedimiento puede ser diferente al usuario autenticado cuando un asistente registra un procedimiento realizado por un doctor. En ese caso, el asistente provee el `doctor_id` del doctor en el body.
- Si el usuario es doctor y no provee `doctor_id`, se usa el id del usuario autenticado.
- Si el `treatment_plan_item_id` ya esta completado, se retorna 409 (no se permite sobrescribir la completacion).
- Los cambios automaticos al odontograma se realizan en la misma transaccion que el procedimiento (atomicos). Si el odontograma no se puede actualizar, el procedimiento se crea igualmente y `odontogram_updated: false`.
- Si se provee `evolution_template_id`: se crea automaticamente un registro clinico de tipo `evolution_note` vinculado al procedimiento. Este registro es independiente y puede editarse via CR-04 dentro de las 24h habituales.
- Los `materials_used` se almacenan con sus numeros de lote para trazabilidad y cumplimiento normativo.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| cups_code de procedimiento en diente sin condicion en odontograma | Crear procedimiento; `odontogram_updated: false`, `odontogram_changes: []` |
| cups_code de exodoncia en diente con corona | Actualizar odontograma de corona -> exodonte |
| evolution_template_id con template_variables incompletas | Interpolar lo que haya; variables no provistas quedan como placeholders `{variable_name}` |
| treatment_plan_item_id de plan de tratamiento de otro paciente | Retornar 404 (no revelar que existe para otro paciente) |
| appointment_id no provisto pero hay cita in_progress | Auto-vincular a la cita activa del doctor |
| materials_used vacio `[]` | Aceptado; procedimiento sin materiales registrados |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `procedures`: INSERT — nuevo procedimiento
- `treatment_plan_items`: UPDATE — `status=completed`, `completed_at`, `procedure_id` si `treatment_plan_item_id` provisto
- `clinical_records`: INSERT — nota de evolucion auto-generada si `evolution_template_id` provisto
- `odontogram_teeth`: UPDATE — condicion del diente si el procedimiento implica cambio conocido
- `audit_logs`: INSERT — entrada de auditoria

**Example query (SQLAlchemy):**
```python
async with session.begin():
    # Insertar procedimiento
    procedure = Procedure(
        patient_id=patient_id,
        doctor_id=effective_doctor_id,
        tenant_id=tenant_id,
        cups_code=cups_entry.code,
        cups_description=cups_entry.description,
        custom_description=body.description,
        tooth_number=body.tooth_number,
        zones=body.zones,
        materials_used=body.materials_used,
        duration_minutes=body.duration_minutes,
        notes=body.notes,
        appointment_id=body.appointment_id,
    )
    session.add(procedure)
    await session.flush()

    # Marcar item de plan de tratamiento como completado
    if body.treatment_plan_item_id:
        await session.execute(
            update(TreatmentPlanItem)
            .where(TreatmentPlanItem.id == body.treatment_plan_item_id)
            .values(
                status="completed",
                completed_at=datetime.utcnow(),
                procedure_id=procedure.id,
            )
        )

    # Crear nota de evolucion desde plantilla
    if body.evolution_template_id:
        template = await load_template(body.evolution_template_id, session)
        note_content = interpolate_template(template, body.template_variables)
        evolution_note = ClinicalRecord(
            patient_id=patient_id,
            doctor_id=effective_doctor_id,
            tenant_id=tenant_id,
            type="evolution_note",
            content=note_content,
            appointment_id=body.appointment_id,
            template_id=body.evolution_template_id,
            procedure_id=procedure.id,
        )
        session.add(evolution_note)

    # Actualizar odontograma
    odontogram_changes = await update_odontogram_for_procedure(
        session, patient_id, body.cups_code, body.tooth_number
    )
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:procedures:list`: DELETE — invalidar listado de procedimientos
- `tenant:{tenant_id}:patient:{patient_id}:clinical_records:list`: DELETE — si se creo nota de evolucion
- `tenant:{tenant_id}:treatment_plan:{plan_id}`: DELETE — si se actualizo item de plan

**Cache TTL:** N/A (invalidacion)

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| audit | procedure.created | { procedure_id, patient_id, doctor_id, cups_code, tooth_number, tenant_id, timestamp } | Siempre al crear |
| billing | procedure.completed | { procedure_id, cups_code, patient_id, doctor_id, tenant_id, duration_minutes, timestamp } | Para generar item de factura |
| analytics | procedure.created | { tenant_id, cups_code, tooth_number, duration_minutes, had_template, timestamp } | Para estadisticas clinicas |

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** procedure
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No (la notificacion al paciente de procedimiento completado, si aplica, se maneja desde el dominio de notifications al completar la cita)

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 600ms (incluye update de odontograma y creacion de nota de evolucion)

### Caching Strategy
- **Strategy:** Sin cache en escritura. Invalidacion de multiples caches.
- **Cache key:** N/A
- **Invalidation:** Listado de procedimientos, registros clinicos, y plan de tratamiento si aplica

### Database Performance

**Queries executed:** 4-8 (validar paciente, validar CUPS, insertar procedimiento, actualizar plan, crear nota, actualizar odontograma, audit log)

**Indexes required:**
- `procedures.(patient_id, tenant_id)` — INDEX compuesto
- `procedures.cups_code` — INDEX
- `procedures.tooth_number` — INDEX
- `procedures.doctor_id` — INDEX
- `procedures.appointment_id` — INDEX
- `procedures.treatment_plan_item_id` — UNIQUE (evita doble completacion)

**N+1 prevention:** Todas las operaciones en una sola transaccion atomica.

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| cups_code | Pydantic str + strip + uppercase | Normalizar formato |
| description | Pydantic str + bleach strip_tags | Prevenir XSS |
| notes | Pydantic str + bleach strip_tags | Prevenir XSS |
| materials_used | Pydantic list[object] validado | Validar cada campo |
| zones | Pydantic list[Literal enum] | Prevenir valores arbitrarios |
| tooth_number | Pydantic int, rango 11-48 | Prevenir valores fuera de rango |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM con queries parametrizadas. Sin SQL raw (excepto validacion CUPS via cache que ya usa parametros).

### XSS Prevention

**Output encoding:** Todos los strings escapados via serializacion Pydantic. Campos de texto sanitizados con bleach.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** `cups_code` (revela procedimiento medico), `tooth_number`, `materials_used`, `notes`, vinculo a `patient_id`

**Audit requirement:** All access logged — toda escritura de procedimiento auditada.

---

## Testing

### Test Cases

#### Happy Path
1. Procedimiento sin plan de tratamiento ni plantilla
   - **Given:** Doctor autenticado, paciente activo, CUPS 89.01.02.01 valido
   - **When:** POST con cups_code, tooth_number=16, materials_used
   - **Then:** 201 Created, procedimiento persistido, audit log generado, billing job encolado

2. Procedimiento que completa item de plan de tratamiento
   - **Given:** Doctor autenticado, item de plan pendiente para restauracion diente 16
   - **When:** POST con treatment_plan_item_id
   - **Then:** 201 Created, treatment_plan_item.status=completed, completed_at establecido

3. Procedimiento con plantilla de evolucion
   - **Given:** Doctor autenticado, evolution_template_id valido
   - **When:** POST con evolution_template_id y template_variables
   - **Then:** 201 Created, nota de evolucion auto-creada con content interpolado

4. Restauracion que actualiza odontograma
   - **Given:** Diente 16 con condicion=caries en odontograma
   - **When:** POST restauracion CUPS 89.01.02.01 en diente 16
   - **Then:** 201 Created, `odontogram_updated: true`, condicion cambia a restauracion_resina

#### Edge Cases
1. Exodoncia en diente sin condicion previa
   - **Given:** Diente 38 sin condicion registrada
   - **When:** POST exodoncia CUPS 89.13.x en diente 38
   - **Then:** 201 Created, `odontogram_updated: false` (no hay condicion que cambiar)

2. Asistente registra procedimiento de un doctor
   - **Given:** Asistente autenticada, doctor_id provisto en body
   - **When:** POST con doctor_id del doctor en body
   - **Then:** 201 Created, procedimiento con doctor_id del doctor, registrado_por=asistente en audit log

3. template_variables con variables desconocidas
   - **Given:** Template con variable {diente}, body provee {diente} y {extra_desconocida}
   - **When:** POST con template_variables extra
   - **Then:** 201 Created, solo {diente} interpolada, {extra_desconocida} ignorada

#### Error Cases
1. CUPS code inexistente
   - **Given:** Doctor autenticado
   - **When:** POST con cups_code=89.99.99.99
   - **Then:** 400 con detalle del codigo invalido

2. treatment_plan_item_id ya completado
   - **Given:** Item de plan con status=completed
   - **When:** POST con ese treatment_plan_item_id
   - **Then:** 409 Conflict con detalle de completacion previa

3. Rol sin permiso (receptionist)
   - **Given:** Usuario con rol receptionist
   - **When:** POST al endpoint
   - **Then:** 403 Forbidden

4. patient_id inexistente
   - **Given:** patient_id invalido
   - **When:** POST al endpoint
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** Doctor activo, asistente activo, recepcionista (para probar 403)

**Patients/Entities:** Paciente activo, odontograma con diente 16 condicion=caries, item de plan de tratamiento pendiente, plantilla de evolucion tipo restauracion, catalogo CUPS con 89.01.02.01

### Mocking Strategy

- **Redis:** fakeredis para cache del catalogo CUPS
- **RabbitMQ:** Mock de publisher; verificar billing job encolado
- **Audit service:** Mock que verifica llamada con PHI=true
- **Template service (CR-15):** Mock con template de prueba

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Procedimiento creado con CUPS code validado contra el catalogo
- [ ] Item de plan de tratamiento marcado como completado si se provee `treatment_plan_item_id`
- [ ] 409 retornado si el item de plan ya estaba completado
- [ ] Nota de evolucion auto-creada cuando se provee `evolution_template_id`
- [ ] Odontograma actualizado automaticamente para tipos de procedimiento conocidos
- [ ] `odontogram_changes` retorna los cambios realizados
- [ ] Trazabilidad de materiales almacenada con numeros de lote
- [ ] Billing job encolado para cada procedimiento creado
- [ ] Audit log generado en cada creacion
- [ ] Asistente puede registrar procedimientos de un doctor (con doctor_id en body)
- [ ] All test cases pass
- [ ] Performance targets met (< 600ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verified (PHI)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Listado de procedimientos (ver CR-13)
- Detalle de un procedimiento (ver CR-14)
- Facturacion directa del procedimiento (ver billing/)
- Prescripciones asociadas al procedimiento (ver prescriptions/)
- Calcular el costo del procedimiento (ver billing/)
- CUPS de procedimientos no dentales (solo subconjunto dental cap. 89)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas con todos los campos)
- [x] All outputs defined (response models con odontogram_changes y evolution_note)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated (incluyendo 409 para item ya completado)
- [x] Auth requirements explicit (doctor + assistant)
- [x] Side effects listed (plan, odontograma, nota de evolucion, billing queue)
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (llama a TP-07 internamente)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (doctor + assistant + tenant context)
- [x] Input sanitization defined (Pydantic + bleach)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail completo para PHI

### Hook 4: Performance & Scalability
- [x] Response time target definido (< 600ms por operaciones multiples)
- [x] Caching strategy stated (invalidacion multiple)
- [x] DB queries optimized (transaccion atomica, indexes listed)
- [x] Pagination applied where needed (N/A)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (audit, billing, analytics)

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy for RabbitMQ y template service
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
