# Evolution Template Create (CR-16)

---

## Overview

**Feature:** Crear una plantilla de evolucion clinica personalizada para el tenant. Las plantillas definen pasos ordenados con texto libre y variables tipadas (select, number, text, date) que el medico completa al momento de registrar una evolucion. Al crear, se invalida el cache de listado del tenant para garantizar consistencia.

**Domain:** clinical-records

**Priority:** High

**Dependencies:** CR-15 (evolution-template-list.md), CR-17 (evolution-template-get.md), I-02 (authentication-rules.md), database-architecture.md (`evolution_templates`, `evolution_template_steps`, `evolution_template_variables`)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** doctor, clinic_owner
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** Los asistentes NO pueden crear plantillas. Solo doctores y propietarios de clinica.

---

## Endpoint

```
POST /api/v1/evolution-templates
```

**Rate Limiting:**
- 30 requests por minuto por usuario
- Redis sliding window: `dentalos:rl:evolution_templates_create:{user_id}` (TTL 60s)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| Content-Type | Yes | string | Formato de request | application/json |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

N/A

### Query Parameters

N/A

### Request Body Schema

```json
{
  "name": "string (required) — nombre de la plantilla, unico por tenant",
  "procedure_type": "string (required) — categoria del procedimiento",
  "cups_code": "string (optional) — codigo CUPS colombiano",
  "complexity": "string (required) — enum: basic | standard | complex",
  "steps": [
    {
      "order": "integer (required) — posicion del paso, desde 1",
      "text": "string (required) — texto del paso con placeholders entre corchetes [variable]",
      "variables": [
        {
          "name": "string (required) — nombre del placeholder sin corchetes",
          "type": "string (required) — enum: select | number | text | date",
          "options": ["string (conditional) — requerido solo si type=select"],
          "default": "string|number (optional) — valor por defecto",
          "unit": "string (optional) — unidad de medida para type=number"
        }
      ]
    }
  ]
}
```

**Example Request:**
```json
{
  "name": "Resina Oclusal Personalizada",
  "procedure_type": "restauracion",
  "cups_code": "89.31.01",
  "complexity": "standard",
  "steps": [
    {
      "order": 1,
      "text": "Anestesia infiltrativa con [tipo_anestesia] al [porcentaje]%.",
      "variables": [
        {
          "name": "tipo_anestesia",
          "type": "select",
          "options": ["lidocaina", "mepivacaina", "articaina"],
          "default": "lidocaina"
        },
        {
          "name": "porcentaje",
          "type": "number",
          "default": 2,
          "unit": "%"
        }
      ]
    },
    {
      "order": 2,
      "text": "Aislamiento absoluto con dique de goma.",
      "variables": []
    },
    {
      "order": 3,
      "text": "Preparacion cavitaria con fresa [tipo_fresa].",
      "variables": [
        {
          "name": "tipo_fresa",
          "type": "select",
          "options": ["fresa 245", "fresa redonda #4", "fresa troncoconica"],
          "default": "fresa 245"
        }
      ]
    },
    {
      "order": 4,
      "text": "Aplicacion de adhesivo [marca_adhesivo], fotopolimerizado por [tiempo_adhesivo] segundos.",
      "variables": [
        {
          "name": "marca_adhesivo",
          "type": "text",
          "default": "Single Bond 2"
        },
        {
          "name": "tiempo_adhesivo",
          "type": "number",
          "default": 20,
          "unit": "segundos"
        }
      ]
    },
    {
      "order": 5,
      "text": "Restauracion con resina [marca_resina] color [color_resina], tecnica incremental.",
      "variables": [
        {
          "name": "marca_resina",
          "type": "text",
          "default": "Filtek Z350"
        },
        {
          "name": "color_resina",
          "type": "select",
          "options": ["A1", "A2", "A3", "A3.5", "B1", "B2", "C2"],
          "default": "A2"
        }
      ]
    }
  ]
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
  "name": "string",
  "procedure_type": "string",
  "cups_code": "string | null",
  "complexity": "string",
  "is_builtin": false,
  "tenant_id": "UUID",
  "steps_count": "integer",
  "variables_count": "integer",
  "steps": [
    {
      "id": "UUID",
      "order": "integer",
      "text": "string",
      "variables": [
        {
          "id": "UUID",
          "name": "string",
          "type": "string",
          "options": ["string"] ,
          "default": "string | number | null",
          "unit": "string | null"
        }
      ]
    }
  ],
  "created_by": "UUID",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

**Example:**
```json
{
  "id": "etpl_9a1b2c3d-e4f5-6789-abcd-ef0123456789",
  "name": "Resina Oclusal Personalizada",
  "procedure_type": "restauracion",
  "cups_code": "89.31.01",
  "complexity": "standard",
  "is_builtin": false,
  "tenant_id": "tn_7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "steps_count": 5,
  "variables_count": 7,
  "steps": [
    {
      "id": "step_aabbccdd-1122-3344-5566-778899001122",
      "order": 1,
      "text": "Anestesia infiltrativa con [tipo_anestesia] al [porcentaje]%.",
      "variables": [
        {
          "id": "var_11223344-aabb-ccdd-eeff-001122334455",
          "name": "tipo_anestesia",
          "type": "select",
          "options": ["lidocaina", "mepivacaina", "articaina"],
          "default": "lidocaina",
          "unit": null
        },
        {
          "id": "var_22334455-bbcc-ddee-ff00-112233445566",
          "name": "porcentaje",
          "type": "number",
          "options": null,
          "default": 2,
          "unit": "%"
        }
      ]
    }
  ],
  "created_by": "usr_550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-02-24T10:30:00Z",
  "updated_at": "2026-02-24T10:30:00Z"
}
```

### Error Responses

#### 400 Bad Request
**When:** Cuerpo de request malformado o campos requeridos ausentes.

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Los datos proporcionados no son validos.",
  "details": {
    "steps": ["Se requiere al menos un paso en la plantilla."]
  }
}
```

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** El rol del usuario no permite crear plantillas (ej. `assistant`, `receptionist`).

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para crear plantillas de evolucion."
}
```

#### 409 Conflict
**When:** Ya existe una plantilla con el mismo nombre para este tenant.

```json
{
  "error": "template_name_conflict",
  "message": "Ya existe una plantilla con el nombre 'Resina Oclusal Personalizada' en esta clinica."
}
```

#### 422 Unprocessable Entity
**When:** Errores de validacion de negocio: orden duplicado en pasos, variable referenciada en texto no declarada, `type=select` sin opciones.

**Example:**
```json
{
  "error": "validation_failed",
  "message": "La plantilla contiene errores de validacion.",
  "details": {
    "steps[0].variables[0].options": ["Las opciones son obligatorias cuando el tipo es 'select'."],
    "steps[1].order": ["El orden '2' esta duplicado. Cada paso debe tener un numero de orden unico."]
  }
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido (30 creaciones/min por usuario).

#### 500 Internal Server Error
**When:** Error inesperado al persistir la plantilla.

---

## Business Logic

**Step-by-step process:**

1. Validar JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea `doctor` o `clinic_owner`. Si no, retornar 403.
3. Validar el body del request contra schema Pydantic:
   - `name` requerido, max 200 chars.
   - `procedure_type` requerido, max 100 chars.
   - `cups_code` opcional, regex `^[A-Za-z0-9.\\-]{1,20}$`.
   - `complexity` requerido, enum `basic | standard | complex`.
   - `steps` requerido, array no vacio, max 50 elementos.
4. Para cada paso en `steps`:
   - `order` debe ser unico dentro del array (no duplicados).
   - `text` requerido, max 1000 chars.
   - Extraer todos los placeholders del formato `[nombre_variable]` del campo `text`.
   - Verificar que cada placeholder tenga un objeto correspondiente en `variables[].name`.
   - Para variables con `type = "select"`: verificar que `options` sea un array con al menos 2 elementos.
   - Para variables con `type = "number"`: `default` si presente debe ser numerico.
5. Verificar unicidad del `name` en el tenant: `SELECT 1 FROM evolution_templates WHERE tenant_id = :tenant_id AND lower(name) = lower(:name)`. Si existe, retornar 409.
6. Iniciar transaccion de base de datos.
7. Insertar registro en `evolution_templates` con `is_builtin = false`, `tenant_id`, `created_by = user_id`, calcular y almacenar `steps_count` y `variables_count`.
8. Por cada paso, insertar en `evolution_template_steps` en orden.
9. Por cada variable de cada paso, insertar en `evolution_template_variables`.
10. Confirmar transaccion.
11. Invalida cache: `DELETE tenant:{tenant_id}:evolution_templates:*` (patron wildcard en Redis).
12. Registrar en log estructurado: `clinical_records.template.created` con `tenant_id`, `user_id`, `template_id`.
13. Retornar 201 Created con la plantilla completa incluyendo pasos y variables.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| name | Requerido, max 200 chars, unico por tenant (case-insensitive) | "El nombre es obligatorio." / "Ya existe una plantilla con este nombre." |
| procedure_type | Requerido, max 100 chars | "El tipo de procedimiento es obligatorio." |
| cups_code | Opcional, regex `^[A-Za-z0-9.\\-]{1,20}$` | "El codigo CUPS no tiene un formato valido." |
| complexity | Requerido, enum: basic, standard, complex | "La complejidad debe ser: basic, standard o complex." |
| steps | Min 1 item, max 50 items | "Se requiere al menos un paso." / "La plantilla no puede tener mas de 50 pasos." |
| steps[].order | Unico dentro del array, integer >= 1 | "El orden del paso debe ser unico y mayor a 0." |
| steps[].text | Requerido, max 1000 chars | "El texto del paso es obligatorio." |
| steps[].variables[].name | Requerido, debe existir como placeholder `[name]` en steps[].text | "La variable '[nombre]' no esta referenciada en el texto del paso." |
| steps[].variables[].type | Enum: select, number, text, date | "El tipo de variable debe ser: select, number, text o date." |
| steps[].variables[].options | Requerido si type=select, min 2 opciones | "Las opciones son obligatorias para variables de tipo select." |

**Business Rules:**

- Las plantillas personalizadas nunca pueden tener `is_builtin = true`.
- El `tenant_id` siempre proviene del JWT, no del body del request.
- Los placeholders en el texto de un paso son de la forma `[nombre_variable]`. Los corchetes son el delimitador.
- Todos los placeholders en el texto deben tener una variable declarada. Variables declaradas pero no referenciadas en el texto generan advertencia pero no bloquean (pueden ser usadas para metadata futura).
- El `steps_count` y `variables_count` se calculan y persisten en `evolution_templates` como campos desnormalizados para optimizar el listado (CR-15).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Paso sin variables (solo texto fijo) | Valido: `variables: []` es permitido |
| Nombre igual a plantilla integrada | Permitido: la unicidad se valida solo por `tenant_id`, no globalmente |
| Steps enviados en orden desordenado | Se procesan y almacenan segun el campo `order`, no el orden del array |
| Variable con type=number y default="dos" | 422: el default debe ser numerico para type=number |
| Mismo placeholder usado dos veces en el mismo texto | Se declara una sola variable; el placeholder se reemplaza en ambas ocurrencias al usar la plantilla |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `evolution_templates`: INSERT — nuevo registro de plantilla con metadatos
- `evolution_template_steps`: INSERT — un registro por cada paso
- `evolution_template_variables`: INSERT — un registro por cada variable de cada paso

**Example query (SQLAlchemy):**
```python
from sqlalchemy import insert

async with session.begin():
    # 1. Insertar plantilla
    template_result = await session.execute(
        insert(EvolutionTemplate).values(
            name=body.name,
            procedure_type=body.procedure_type,
            cups_code=body.cups_code,
            complexity=body.complexity,
            is_builtin=False,
            tenant_id=tenant_id,
            created_by=user_id,
            steps_count=len(body.steps),
            variables_count=sum(len(s.variables) for s in body.steps),
        ).returning(EvolutionTemplate.id)
    )
    template_id = template_result.scalar_one()

    # 2. Insertar pasos
    for step in sorted(body.steps, key=lambda s: s.order):
        step_result = await session.execute(
            insert(EvolutionTemplateStep).values(
                template_id=template_id,
                order=step.order,
                text=step.text,
            ).returning(EvolutionTemplateStep.id)
        )
        step_id = step_result.scalar_one()

        # 3. Insertar variables del paso
        for var in step.variables:
            await session.execute(
                insert(EvolutionTemplateVariable).values(
                    step_id=step_id,
                    name=var.name,
                    type=var.type,
                    options=var.options,
                    default=var.default,
                    unit=var.unit,
                )
            )
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:evolution_templates:*`: DELETE (invalidacion de todos los filtros cacheados)

**Cache TTL:** N/A (invalidacion, no escritura directa)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** Ninguno

### Audit Log

**Audit entry:** Yes

- **Action:** create
- **Resource:** evolution_template
- **PHI involved:** No

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 300ms
- **Maximum acceptable:** < 800ms (incluye transaccion multi-tabla e invalidacion de cache)

### Caching Strategy
- **Strategy:** Invalidacion de cache al crear nueva plantilla
- **Cache key:** `tenant:{tenant_id}:evolution_templates:*` (pattern delete)
- **TTL:** N/A
- **Invalidation:** Inmediata al crear la plantilla

### Database Performance

**Queries executed:** 4-N (verificacion unicidad, insert template, insert N steps, insert M variables)

**Indexes required:**
- `evolution_templates.(tenant_id, lower(name))` — UNIQUE (garantiza unicidad case-insensitive)
- `evolution_template_steps.template_id` — INDEX
- `evolution_template_variables.step_id` — INDEX

**N+1 prevention:** Todos los inserts de pasos y variables en la misma transaccion atomica. No hay lecturas adicionales post-insert (se construye la respuesta a partir de los datos del request + ID generado).

### Pagination

**Pagination:** No

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| name | Pydantic str, strip, max_length=200 | Prevenir XSS en nombre |
| procedure_type | Pydantic str, strip, max_length=100 | |
| cups_code | Pydantic str, strip, regex validado | Solo alfanumerico |
| steps[].text | Pydantic str, strip, max_length=1000, bleach para HTML | El texto puede mostrarse en PDF |
| steps[].variables[].options[] | Pydantic list[str], cada elemento max 100 chars | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic. El campo `text` se sanitiza con bleach antes de almacenar (strip HTML tags).

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — las plantillas son estructuras de procedimientos, no datos de pacientes.

**Audit requirement:** Write-only logged (creacion de plantilla registrada con `user_id` y `tenant_id`)

---

## Testing

### Test Cases

#### Happy Path
1. Crear plantilla con pasos y variables validos
   - **Given:** Usuario `doctor` autenticado con tenant valido
   - **When:** POST /api/v1/evolution-templates con body completo y valido (5 pasos, 7 variables)
   - **Then:** 201 Created, respuesta incluye `id` UUID, todos los pasos y variables persistidos

2. Crear plantilla con pasos sin variables (texto fijo)
   - **Given:** Usuario `clinic_owner` autenticado
   - **When:** POST con steps donde todos tienen `variables: []`
   - **Then:** 201 Created, `variables_count: 0`

3. Cache invalidado tras creacion
   - **Given:** Cache de listado populado para el tenant
   - **When:** POST crea nueva plantilla exitosamente
   - **Then:** Siguiente GET /api/v1/evolution-templates resulta en cache miss (X-Cache: MISS)

#### Edge Cases
1. Steps enviados fuera de orden
   - **Given:** Request con steps en orden `[3, 1, 2]` en el array
   - **When:** POST /api/v1/evolution-templates
   - **Then:** 201 Created, pasos almacenados y retornados en orden `[1, 2, 3]` segun campo `order`

2. Nombre identico a plantilla integrada
   - **Given:** Plantilla integrada "Resina Oclusal" existe con `tenant_id=null`
   - **When:** POST con `name: "Resina Oclusal"`
   - **Then:** 201 Created (no hay conflicto con plantillas integradas)

3. Placeholder en texto sin variable declarada
   - **Given:** Paso con texto "Usar [material] en la cavidad" pero `variables: []`
   - **When:** POST /api/v1/evolution-templates
   - **Then:** 422 con detalle del placeholder no declarado

#### Error Cases
1. Rol no autorizado (assistant)
   - **Given:** Usuario con rol `assistant`
   - **When:** POST /api/v1/evolution-templates
   - **Then:** 403 Forbidden

2. Nombre duplicado en el mismo tenant
   - **Given:** Plantilla "Mi Plantilla" ya existe para el tenant
   - **When:** POST con el mismo nombre
   - **Then:** 409 Conflict con mensaje descriptivo

3. Steps vacio
   - **Given:** Request con `"steps": []`
   - **When:** POST /api/v1/evolution-templates
   - **Then:** 400 Bad Request — "Se requiere al menos un paso."

4. Mas de 50 pasos
   - **Given:** Request con 51 elementos en `steps`
   - **When:** POST /api/v1/evolution-templates
   - **Then:** 422 Unprocessable Entity

5. Variable type=select sin opciones
   - **Given:** Variable con `"type": "select", "options": []`
   - **When:** POST /api/v1/evolution-templates
   - **Then:** 422 con detalle del campo

### Test Data Requirements

**Users:** Un `doctor` activo, un `clinic_owner` activo, un `assistant` activo (para test 403), un `receptionist` activo (para test 403).

**Entities:** Ninguna plantilla preexistente del tenant (estado limpio). Seed con las 10 plantillas integradas.

### Mocking Strategy

- **Redis:** fakeredis para validar invalidacion de cache
- **Database:** SQLite en memoria con esquema completo para tests de integracion

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] POST crea plantilla con pasos y variables y retorna 201 con datos completos
- [ ] Unicidad de nombre por tenant se valida (409 si duplicado)
- [ ] Min 1 paso y max 50 pasos se valida correctamente
- [ ] Variables de tipo `select` sin opciones son rechazadas con 422
- [ ] Placeholders en texto sin variable declarada son rechazados con 422
- [ ] Cache del listado se invalida correctamente tras creacion
- [ ] Rol `assistant` y `receptionist` reciben 403
- [ ] `tenant_id` siempre proviene del JWT, nunca del body
- [ ] `steps_count` y `variables_count` almacenados correctamente
- [ ] All test cases pass
- [ ] Performance targets met (< 800ms)
- [ ] Quality Hooks passed
- [ ] Audit logging verificado

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Edicion de plantillas existentes (PATCH /api/v1/evolution-templates/{id})
- Eliminacion de plantillas (DELETE)
- Clonacion de plantillas integradas como base para personalizadas
- Importacion masiva de plantillas (CSV/JSON)
- Versionado de plantillas

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
- [x] Follows service boundaries (clinical-records domain)
- [x] Uses tenant schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (role + tenant context)
- [x] Input sanitization defined (Pydantic + bleach para texto)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail para escritura (template creado)

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 800ms)
- [x] Caching strategy stated (invalidacion de cache del tenant)
- [x] DB queries optimized (transaccion atomica, indexes listados)
- [x] Pagination N/A

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id incluido)
- [x] Audit log entries defined (create, no PHI)
- [x] Error tracking (Sentry-compatible)
- [x] Queue job monitoring (N/A)

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
