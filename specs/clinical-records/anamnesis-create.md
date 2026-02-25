# Crear o Actualizar Anamnesis (CR-05)

---

## Overview

**Feature:** Crea o actualiza la anamnesis (historia clinica medica) de un paciente. Comportamiento upsert: si ya existe una anamnesis, se actualiza; si no, se crea. Incluye secciones estructuradas: medicamentos, alergias, condiciones cronicas, historia quirurgica, antecedentes familiares, habitos y campos especificos por pais (Colombia: informacion EPS/IPS).

**Domain:** clinical-records

**Priority:** High

**Dependencies:** patients/patient-get.md, infra/audit-logging.md, infra/authentication-rules.md, compliance/country-adapter.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** doctor, assistant
- **Tenant context:** Required — resuelto desde JWT
- **Special rules:** PHI altamente sensible. Toda escritura es auditada. Solo doctor o asistente pueden registrar/actualizar la anamnesis.

---

## Endpoint

```
POST /api/v1/patients/{patient_id}/anamnesis
```

**Rate Limiting:**
- 30 requests por minuto por usuario
- Redis sliding window: `tenant:{tenant_id}:rate:anamnesis_write:{user_id}`

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
  "current_medications": [
    {
      "name": "string (required) — nombre del medicamento",
      "dose": "string (optional) — dosis ej: 500mg",
      "frequency": "string (optional) — frecuencia ej: cada 8 horas",
      "since": "string (optional) — fecha de inicio YYYY-MM"
    }
  ],
  "allergies": [
    {
      "allergen": "string (required) — sustancia alergena",
      "type": "string (optional) — medicamento | alimento | ambiental | latex | otro",
      "severity": "string (optional) — leve | moderada | severa | anafilactica",
      "reaction": "string (optional) — descripcion de la reaccion"
    }
  ],
  "chronic_conditions": [
    {
      "condition": "string (required) — nombre de la condicion",
      "cie10_code": "string (optional) — codigo CIE-10",
      "since": "string (optional) — anio de diagnostico YYYY",
      "controlled": "boolean (optional) — si la condicion esta controlada",
      "treatment": "string (optional) — tratamiento actual"
    }
  ],
  "surgical_history": [
    {
      "procedure": "string (required) — nombre del procedimiento",
      "year": "integer (optional) — anio de la cirugia",
      "complications": "string (optional) — complicaciones si las hubo"
    }
  ],
  "family_history": {
    "diabetes": "boolean (optional)",
    "hypertension": "boolean (optional)",
    "cancer": "boolean (optional)",
    "heart_disease": "boolean (optional)",
    "bleeding_disorders": "boolean (optional)",
    "notes": "string (optional) — observaciones adicionales de antecedentes familiares"
  },
  "habits": {
    "smoking": {
      "status": "string (optional) — never | former | current",
      "packs_per_day": "number (optional) — cigarrillos por dia si status=current",
      "years": "integer (optional) — anios fumando"
    },
    "alcohol": {
      "status": "string (optional) — never | occasional | frequent | daily",
      "drinks_per_week": "integer (optional)"
    },
    "recreational_drugs": {
      "status": "string (optional) — never | former | current",
      "substances": "array<string> (optional)"
    },
    "physical_activity": "string (optional) — sedentary | light | moderate | intense"
  },
  "pregnancy_status": "string (optional) — not_applicable | not_pregnant | pregnant | breastfeeding | postpartum",
  "pregnancy_weeks": "integer (optional) — semanas si pregnancy_status=pregnant",
  "blood_type": "string (optional) — A+ | A- | B+ | B- | AB+ | AB- | O+ | O- | unknown",
  "rh_factor": "string (optional) — positive | negative | unknown",
  "country_specific": {
    "eps": "string (optional) — Colombia: entidad prestadora de salud",
    "ips": "string (optional) — Colombia: institucion prestadora de servicios de salud",
    "health_regime": "string (optional) — Colombia: contributivo | subsidiado | vinculado | especial",
    "poliza_seguro": "string (optional) — numero de poliza de seguro complementario"
  },
  "notes": "string (optional) — observaciones generales de la anamnesis"
}
```

**Example Request:**
```json
{
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
    },
    {
      "condition": "Hipertension arterial",
      "cie10_code": "I10",
      "since": "2022",
      "controlled": true,
      "treatment": "Losartan"
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
    "smoking": { "status": "former", "years": 10 },
    "alcohol": { "status": "occasional", "drinks_per_week": 2 },
    "recreational_drugs": { "status": "never" },
    "physical_activity": "light"
  },
  "pregnancy_status": "not_applicable",
  "blood_type": "O+",
  "rh_factor": "positive",
  "country_specific": {
    "eps": "Nueva EPS",
    "ips": "Clinica del Country",
    "health_regime": "contributivo",
    "poliza_seguro": "POL-2024-123456"
  },
  "notes": "Paciente refiere alergia severa a penicilina. Verificar siempre antes de prescribir antibioticos."
}
```

---

## Response

### Success Response

**Status:** 200 OK (si se actualiza anamnesis existente) / 201 Created (si es primera anamnesis)

**Schema:**
```json
{
  "id": "UUID",
  "patient_id": "UUID",
  "version": "integer — numero de version (1 para nueva, incrementa en cada update)",
  "current_medications": "array<object>",
  "allergies": "array<object>",
  "chronic_conditions": "array<object>",
  "surgical_history": "array<object>",
  "family_history": "object",
  "habits": "object",
  "pregnancy_status": "string | null",
  "pregnancy_weeks": "integer | null",
  "blood_type": "string | null",
  "rh_factor": "string | null",
  "country_specific": "object",
  "notes": "string | null",
  "completed_by": {
    "id": "UUID",
    "name": "string",
    "role": "string"
  },
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime",
  "allergies_alert": "boolean — true si hay alergias registradas (para alertas en UI)"
}
```

**Example (201 Created — primera anamnesis):**
```json
{
  "id": "ana_7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "version": 1,
  "current_medications": [
    { "name": "Losartan", "dose": "50mg", "frequency": "1 vez al dia", "since": "2022-03" }
  ],
  "allergies": [
    { "allergen": "Penicilina", "type": "medicamento", "severity": "severa", "reaction": "Erupciones cutaneas y dificultad para respirar" }
  ],
  "chronic_conditions": [
    { "condition": "Diabetes mellitus tipo 2", "cie10_code": "E11", "since": "2021", "controlled": true, "treatment": "Metformina + dieta" }
  ],
  "surgical_history": [
    { "procedure": "Apendicectomia", "year": 2015, "complications": "Ninguna" }
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
    "smoking": { "status": "former", "years": 10 },
    "alcohol": { "status": "occasional", "drinks_per_week": 2 },
    "recreational_drugs": { "status": "never" },
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
  "notes": "Paciente refiere alergia severa a penicilina.",
  "completed_by": {
    "id": "usr_doctor_001",
    "name": "Dra. Ana Martinez",
    "role": "doctor"
  },
  "created_at": "2026-02-24T10:00:00Z",
  "updated_at": "2026-02-24T10:00:00Z",
  "allergies_alert": true
}
```

### Error Responses

#### 400 Bad Request
**When:** Campos mal formateados o combinaciones invalidas.

```json
{
  "error": "invalid_input",
  "message": "Los datos proporcionados no son validos.",
  "details": {
    "pregnancy_weeks": ["Semanas de embarazo solo aplica si pregnancy_status es 'pregnant'."],
    "blood_type": ["Tipo de sangre invalido. Opciones: A+, A-, B+, B-, AB+, AB-, O+, O-."]
  }
}
```

#### 401 Unauthorized
**When:** Token ausente, expirado o invalido.

#### 403 Forbidden
**When:** Rol sin permiso (receptionist).

```json
{
  "error": "forbidden",
  "message": "No tiene permisos para registrar la anamnesis del paciente."
}
```

#### 404 Not Found
**When:** `patient_id` no existe en el tenant.

```json
{
  "error": "not_found",
  "message": "El paciente especificado no existe."
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido.

#### 500 Internal Server Error
**When:** Error inesperado al persistir la anamnesis.

---

## Business Logic

**Step-by-step process:**

1. Validar input contra schema Pydantic (`AnamnesisUpsertSchema`).
2. Resolver tenant desde JWT. Verificar rol (doctor o assistant).
3. Verificar que `patient_id` existe en el tenant.
4. Verificar campos dependientes: si `pregnancy_weeks` provisto y `pregnancy_status != 'pregnant'`, retornar 400.
5. Aplicar compliance adapter segun pais del tenant: si el tenant es de Colombia, validar que `country_specific.health_regime` sea un valor valido para Colombia.
6. Buscar anamnesis existente: `SELECT * FROM anamnesis WHERE patient_id = patient_id AND tenant_id = tenant_id LIMIT 1`.
7. Si no existe: INSERT nueva anamnesis con `version=1`. Retornar 201.
8. Si existe: UPDATE anamnesis con los nuevos valores. Incrementar `version`. Retornar 200.
9. Calcular `allergies_alert = len(allergies) > 0`.
10. Actualizar campo de alerta en el perfil del paciente: `patients.has_allergies = allergies_alert`.
11. Registrar entrada de auditoria (action=create o update, resource=anamnesis, phi=true).
12. Invalidar cache de la anamnesis del paciente.
13. Retornar respuesta con la anamnesis persistida.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| pregnancy_weeks | Solo si pregnancy_status=pregnant | "Semanas de embarazo solo aplica si el estado es 'pregnant'." |
| blood_type | Enum: A+, A-, B+, B-, AB+, AB-, O+, O-, unknown | "Tipo de sangre invalido." |
| allergies[].severity | Enum: leve, moderada, severa, anafilactica | "Severidad de alergia invalida." |
| habits.smoking.status | Enum: never, former, current | "Estado de tabaquismo invalido." |
| habits.alcohol.status | Enum: never, occasional, frequent, daily | "Estado de consumo de alcohol invalido." |
| country_specific.health_regime | Colombia: contributivo, subsidiado, vinculado, especial | "Regimen de salud invalido para Colombia." |

**Business Rules:**

- Solo existe UNA anamnesis por paciente (upsert). Nunca se crean multiples registros.
- El campo `version` se incrementa en cada actualizacion para trazabilidad.
- Si el paciente tiene alergias registradas, se actualiza el flag `patients.has_allergies = true` para mostrar alertas visuales en la UI en toda la aplicacion.
- Los campos `country_specific` son validados por el compliance adapter del pais del tenant. Campos desconocidos para el pais son almacenados pero no validados.
- El historial de versiones de la anamnesis no es recuperable via API en MVP (solo via audit log directo).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Anamnesis sin medicamentos ni alergias | Arrays vacios aceptados; `allergies_alert: false` |
| Paciente sin genero femenino con pregnancy_status=pregnant | Aceptar sin error (no hay validacion de genero en esta version) |
| country_specific con campos desconocidos para el pais del tenant | Almacenar los campos extra, no retornar error |
| Anamnesis actualizada sin cambios reales | Aceptar; version incrementa igualmente |
| chronic_conditions con cie10_code invalido | Aceptar pero marcar como "no validado" en el codigo; no retornar 400 (validacion laxa para no bloquear flujo clinico) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `anamnesis`: INSERT (primera vez) o UPDATE (actualizaciones)
- `patients`: UPDATE — `has_allergies` flag actualizado
- `audit_logs`: INSERT — entrada de auditoria

**Example query (SQLAlchemy):**
```python
existing = await session.scalar(
    select(Anamnesis).where(
        Anamnesis.patient_id == patient_id,
        Anamnesis.tenant_id == tenant_id,
    )
)
if existing:
    existing.current_medications = body.current_medications
    existing.allergies = body.allergies
    existing.chronic_conditions = body.chronic_conditions
    existing.surgical_history = body.surgical_history
    existing.family_history = body.family_history
    existing.habits = body.habits
    existing.pregnancy_status = body.pregnancy_status
    existing.blood_type = body.blood_type
    existing.country_specific = body.country_specific
    existing.notes = body.notes
    existing.version += 1
    existing.updated_at = datetime.utcnow()
    status_code = 200
else:
    existing = Anamnesis(patient_id=patient_id, tenant_id=tenant_id, **body.dict(), version=1)
    session.add(existing)
    status_code = 201

# Actualizar flag de alergias en el paciente
await session.execute(
    update(Patient)
    .where(Patient.id == patient_id)
    .values(has_allergies=len(body.allergies) > 0)
)
await session.commit()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:patient:{patient_id}:anamnesis`: DELETE — invalidar cache de la anamnesis

**Cache TTL:** N/A (invalidacion)

### Queue Jobs (RabbitMQ)

| Queue | Job Type | Payload | When |
|-------|----------|---------|------|
| audit | anamnesis.created | { anamnesis_id, patient_id, user_id, tenant_id, timestamp } | Primera creacion |
| audit | anamnesis.updated | { anamnesis_id, patient_id, user_id, tenant_id, version, timestamp } | Actualizaciones |

### Audit Log

**Audit entry:** Yes

- **Action:** create (primera vez) / update (actualizaciones)
- **Resource:** anamnesis
- **PHI involved:** Yes

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 200ms
- **Maximum acceptable:** < 400ms

### Caching Strategy
- **Strategy:** Invalidacion de cache al escribir
- **Cache key:** `tenant:{tenant_id}:patient:{patient_id}:anamnesis`
- **TTL:** N/A (solo invalidacion)
- **Invalidation:** Al crear o actualizar la anamnesis

### Database Performance

**Queries executed:** 3-4 (verificar paciente, buscar anamnesis existente, upsert anamnesis, update flag paciente)

**Indexes required:**
- `anamnesis.(patient_id, tenant_id)` — UNIQUE (garantiza una anamnesis por paciente)

**N+1 prevention:** No aplica (1 registro por paciente).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| current_medications[].name | Pydantic str + strip | Prevenir inyeccion |
| allergies[].reaction | Pydantic str + bleach strip_tags | Rich text no permitido |
| notes | Pydantic str + bleach strip_tags | Prevenir XSS |
| country_specific | Pydantic dict validado | Campos whitelist por pais |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM con queries parametrizadas. Sin SQL raw.

### XSS Prevention

**Output encoding:** Todos los strings escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Todo el body — medicamentos, alergias, condiciones cronicas, historial quirurgico, antecedentes familiares, habitos, estado de embarazo, tipo de sangre, datos de EPS/IPS.

**Audit requirement:** All access logged — anamnesis es el registro de PHI mas sensible del sistema.

---

## Testing

### Test Cases

#### Happy Path
1. Crear primera anamnesis de paciente
   - **Given:** Doctor autenticado, paciente sin anamnesis previa
   - **When:** POST con todos los campos
   - **Then:** 201 Created, version=1, has_allergies actualizado, audit log generado

2. Actualizar anamnesis existente
   - **Given:** Doctor autenticado, paciente con anamnesis version=1
   - **When:** POST con datos actualizados
   - **Then:** 200 OK, version=2, datos actualizados

3. Anamnesis con alergias — flag actualizado
   - **Given:** Paciente sin alergias (has_allergies=false)
   - **When:** POST con allergies=[{allergen: "Penicilina", ...}]
   - **Then:** 200 OK, patients.has_allergies=true

4. Anamnesis de Colombia con campos EPS/IPS
   - **Given:** Tenant de Colombia, paciente activo
   - **When:** POST con country_specific.health_regime=contributivo
   - **Then:** 201 Created, campos country_specific almacenados correctamente

#### Edge Cases
1. Anamnesis con arrays vacios
   - **Given:** Doctor autenticado
   - **When:** POST con current_medications=[], allergies=[]
   - **Then:** 201 Created, allergies_alert=false, patients.has_allergies=false

2. pregnancy_weeks sin pregnancy_status=pregnant
   - **Given:** Doctor autenticado
   - **When:** POST con pregnancy_status=not_pregnant, pregnancy_weeks=20
   - **Then:** 400 con detalle de error de validacion

#### Error Cases
1. Rol sin permiso
   - **Given:** Recepcionista autenticada
   - **When:** POST al endpoint
   - **Then:** 403 Forbidden

2. Paciente inexistente
   - **Given:** patient_id que no existe
   - **When:** POST al endpoint
   - **Then:** 404 Not Found

### Test Data Requirements

**Users:** Doctor activo, asistente activo, recepcionista (para probar 403)

**Patients/Entities:** Paciente sin anamnesis previa, paciente con anamnesis previa (version 1)

**Compliance:** Tenant configurado con country=CO para pruebas de campos especificos de Colombia

### Mocking Strategy

- **Redis:** fakeredis para cache en unit tests
- **Compliance adapter:** Mock que retorna reglas de validacion para CO
- **Audit service:** Mock que verifica llamada con PHI flag=true

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Primera anamnesis crea nuevo registro (201) con version=1
- [ ] Anamnesis existente es actualizada (200) con version incrementado
- [ ] Flag `patients.has_allergies` se actualiza correctamente
- [ ] Campos `country_specific` almacenados y validados segun pais del tenant
- [ ] Campos dependientes validados (pregnancy_weeks solo si pregnant)
- [ ] Auditoria registrada en cada escritura (create/update)
- [ ] Cache invalidado al escribir
- [ ] All test cases pass
- [ ] Performance targets met (< 400ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verified (PHI)

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Obtener la anamnesis (ver CR-06)
- Historial de versiones de anamnesis accesible via API (solo en audit log)
- Anamnesis de pacientes del portal (portal/patient-anamnesis.md)
- Campos especificos de paises distintos a Colombia en MVP

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas con todas las secciones)
- [x] All outputs defined (response models)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (role + tenant)
- [x] Side effects listed (including has_allergies flag)
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
- [x] Audit trail para PHI altamente sensible

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (invalidacion)
- [x] DB queries optimized (UNIQUE index en patient_id+tenant_id)
- [x] Pagination applied where needed (N/A — 1 registro por paciente)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified
- [x] Mocking strategy for compliance adapter
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
