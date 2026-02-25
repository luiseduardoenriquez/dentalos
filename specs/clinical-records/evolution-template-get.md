# Evolution Template Get (CR-17)

---

## Overview

**Feature:** Obtener el detalle completo de una plantilla de evolucion clinica, incluyendo todos sus pasos ordenados y las variables tipadas de cada paso. Accesible tanto para plantillas integradas del sistema como para plantillas personalizadas del tenant del usuario autenticado.

**Domain:** clinical-records

**Priority:** High

**Dependencies:** CR-15 (evolution-template-list.md), CR-16 (evolution-template-create.md), I-02 (authentication-rules.md)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** doctor, assistant
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** Un usuario solo puede acceder a plantillas integradas (globales) o a plantillas del tenant al que pertenece. No puede acceder a plantillas de otro tenant.

---

## Endpoint

```
GET /api/v1/evolution-templates/{template_id}
```

**Rate Limiting:**
- Inherits global rate limit (100/min per user)

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |
| X-Tenant-ID | Yes | string | Tenant identifier (auto from JWT) | tn_abc123 |

### URL Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| template_id | Yes | UUID | Formato UUID v4 valido | ID unico de la plantilla de evolucion | etpl_550e8400-e29b-41d4-a716-446655440001 |

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
  "name": "string",
  "procedure_type": "string",
  "cups_code": "string | null",
  "complexity": "basic | standard | complex",
  "is_builtin": "boolean",
  "tenant_id": "UUID | null",
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
          "type": "select | number | text | date",
          "options": ["string"] ,
          "default": "string | number | null",
          "unit": "string | null"
        }
      ]
    }
  ],
  "created_by": "UUID | null",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

**Example (plantilla integrada — Resina Oclusal):**
```json
{
  "id": "etpl_550e8400-e29b-41d4-a716-446655440001",
  "name": "Resina Oclusal",
  "procedure_type": "restauracion",
  "cups_code": "89.31.01",
  "complexity": "standard",
  "is_builtin": true,
  "tenant_id": null,
  "steps_count": 10,
  "variables_count": 4,
  "steps": [
    {
      "id": "step_aabb1122-ccdd-3344-eeff-556677889900",
      "order": 1,
      "text": "Anestesia infiltrativa con [tipo_anestesia] al [porcentaje]%.",
      "variables": [
        {
          "id": "var_1111aaaa-2222-bbbb-3333-cccc4444dddd",
          "name": "tipo_anestesia",
          "type": "select",
          "options": ["lidocaina", "mepivacaina", "articaina"],
          "default": "lidocaina",
          "unit": null
        },
        {
          "id": "var_2222bbbb-3333-cccc-4444-dddd5555eeee",
          "name": "porcentaje",
          "type": "number",
          "options": null,
          "default": 2,
          "unit": "%"
        }
      ]
    },
    {
      "id": "step_bbcc2233-ddee-4455-ff00-667788990011",
      "order": 2,
      "text": "Aislamiento absoluto con dique de goma.",
      "variables": []
    },
    {
      "id": "step_ccdd3344-eeff-5566-0011-778899001122",
      "order": 3,
      "text": "Preparacion cavitaria con turbina de alta velocidad.",
      "variables": []
    },
    {
      "id": "step_ddee4455-ff00-6677-1122-889900112233",
      "order": 4,
      "text": "Aplicacion de adhesivo, fotopolimerizado por 20 segundos.",
      "variables": []
    },
    {
      "id": "step_eeff5566-0011-7788-2233-990011223344",
      "order": 5,
      "text": "Restauracion con resina [marca_resina] color [color_resina], tecnica incremental.",
      "variables": [
        {
          "id": "var_3333cccc-4444-dddd-5555-eeee6666ffff",
          "name": "marca_resina",
          "type": "text",
          "options": null,
          "default": "Filtek Z350",
          "unit": null
        },
        {
          "id": "var_4444dddd-5555-eeee-6666-ffff00001111",
          "name": "color_resina",
          "type": "select",
          "options": ["A1", "A2", "A3", "A3.5", "B1", "B2"],
          "default": "A2",
          "unit": null
        }
      ]
    },
    {
      "id": "step_ff006677-1122-8899-3344-001122334455",
      "order": 6,
      "text": "Fotopolimerizacion por incrementos de 20 segundos.",
      "variables": []
    },
    {
      "id": "step_00117788-2233-9900-4455-112233445566",
      "order": 7,
      "text": "Retiro del dique de goma y ajuste de oclusion.",
      "variables": []
    },
    {
      "id": "step_11228899-3344-0011-5566-223344556677",
      "order": 8,
      "text": "Pulido con discos y gomas de pulir.",
      "variables": []
    },
    {
      "id": "step_22339900-4455-1122-6677-334455667788",
      "order": 9,
      "text": "Control radiografico post-operatorio.",
      "variables": []
    },
    {
      "id": "step_33440011-5566-2233-7788-445566778899",
      "order": 10,
      "text": "Indicaciones post-operatorias al paciente: evitar alimentos duros por [horas_espera] horas.",
      "variables": [
        {
          "id": "var_5555eeee-6666-ffff-7777-00001111aaaa",
          "name": "horas_espera",
          "type": "number",
          "options": null,
          "default": 2,
          "unit": "horas"
        }
      ]
    }
  ],
  "created_by": null,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

### Error Responses

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** La plantilla pertenece a un tenant diferente al del usuario autenticado (no es integrada ni del propio tenant).

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para acceder a esta plantilla."
}
```

#### 404 Not Found
**When:** No existe ninguna plantilla con el `template_id` proporcionado (ni integrada ni del tenant del usuario).

```json
{
  "error": "template_not_found",
  "message": "La plantilla de evolucion no fue encontrada."
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido. Ver `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Error inesperado en base de datos o cache.

---

## Business Logic

**Step-by-step process:**

1. Validar token JWT y extraer `tenant_id`, `user_id`, `role`.
2. Verificar que el rol sea `doctor` o `assistant`. Si no, retornar 403.
3. Validar que `template_id` sea un UUID v4 valido. Si no, retornar 404 directamente (no revelar info de formato).
4. Construir cache key: `tenant:{tenant_id}:evolution_template:{template_id}`.
5. Intentar leer desde Redis. Si cache hit, verificar que `is_builtin=true` o `tenant_id` en cache coincida con el del JWT. Retornar con header `X-Cache: HIT`.
6. Si cache miss: buscar en base de datos:
   ```sql
   SELECT * FROM evolution_templates
   WHERE id = :template_id
   AND (tenant_id IS NULL OR tenant_id = :tenant_id)
   AND is_active = true
   ```
7. Si no se encuentra ningun registro: retornar 404.
8. Cargar pasos ordenados: `SELECT * FROM evolution_template_steps WHERE template_id = :template_id ORDER BY order ASC`.
9. Cargar variables por cada paso: `SELECT * FROM evolution_template_variables WHERE step_id = ANY(:step_ids) ORDER BY step_id, id`.
10. Ensamblar objeto de respuesta anidado (template → steps → variables).
11. Almacenar en Redis con TTL de 30 minutos.
12. Retornar 200 OK con la plantilla completa.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| template_id | UUID v4 valido | 404 (no revelar formato invalido) |

**Business Rules:**

- Las plantillas integradas (`is_builtin=true`, `tenant_id=null`) son accesibles por cualquier tenant.
- Las plantillas personalizadas solo son accesibles por el tenant que las creo (`tenant_id` del JWT debe coincidir con `tenant_id` de la plantilla).
- Los pasos siempre se retornan ordenados por el campo `order` ascendente.
- Las variables se retornan en el contexto del paso al que pertenecen.
- El campo `created_by` es `null` para plantillas integradas.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| template_id de plantilla de otro tenant | 404 (no revelar que existe) |
| Plantilla integrada con cualquier tenant | 200 OK (acceso permitido) |
| Plantilla marcada como inactiva (`is_active=false`) | 404 |
| UUID sintaticamente invalido en URL | 404 (no 400, para no revelar estructura) |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `evolution_templates`: SELECT — lectura de metadatos de la plantilla
- `evolution_template_steps`: SELECT — lectura de pasos
- `evolution_template_variables`: SELECT — lectura de variables

**Example query (SQLAlchemy):**
```python
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

stmt = (
    select(EvolutionTemplate)
    .where(EvolutionTemplate.id == template_id)
    .where(
        or_(
            EvolutionTemplate.tenant_id.is_(None),
            EvolutionTemplate.tenant_id == tenant_id
        )
    )
    .where(EvolutionTemplate.is_active == True)
    .options(
        selectinload(EvolutionTemplate.steps)
        .selectinload(EvolutionTemplateStep.variables)
    )
)
result = await session.execute(stmt)
template = result.scalar_one_or_none()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:evolution_template:{template_id}`: SET — resultado completo de la plantilla

**Cache TTL:** 1800s (30 minutos) — mismo TTL que el listado (CR-15)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** Ninguno

### Audit Log

**Audit entry:** No — lectura de metadata de plantilla, sin PHI.

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 80ms (cache hit)
- **Maximum acceptable:** < 350ms (cache miss con joins)

### Caching Strategy
- **Strategy:** Redis cache por plantilla y tenant
- **Cache key:** `tenant:{tenant_id}:evolution_template:{template_id}`
- **TTL:** 1800s (30 minutos)
- **Invalidation:** Cuando la plantilla se edita o elimina (mismo patron que CR-16 invalida el cache de listado)

### Database Performance

**Queries executed:** 1 (con eager loading via `selectinload`)

**Indexes required:**
- `evolution_templates.id` — PRIMARY KEY
- `evolution_templates.(id, tenant_id)` — INDEX COMPUESTO para la query de acceso por tenant
- `evolution_template_steps.template_id` — INDEX
- `evolution_template_steps.order` — INDEX
- `evolution_template_variables.step_id` — INDEX

**N+1 prevention:** SQLAlchemy `selectinload` carga pasos y variables en queries adicionales pero no en bucle N+1. Total: 3 queries (template + steps + variables).

### Pagination

**Pagination:** No — se retorna la plantilla completa con todos sus pasos y variables.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| template_id | Pydantic UUID, validacion de formato | Si no es UUID valido, 404 directo |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — las plantillas son estructuras de procedimientos, no contienen datos de pacientes.

**Audit requirement:** Not required

---

## Testing

### Test Cases

#### Happy Path
1. Obtener plantilla integrada
   - **Given:** Usuario `doctor` autenticado, plantilla integrada "Resina Oclusal" existe con `is_builtin=true`
   - **When:** GET /api/v1/evolution-templates/{id_resina_oclusal}
   - **Then:** 200 OK, response incluye todos los 10 pasos en orden ascendente, variables correctamente anidadas

2. Obtener plantilla personalizada del propio tenant
   - **Given:** Usuario `doctor`, plantilla personalizada del mismo tenant
   - **When:** GET /api/v1/evolution-templates/{id_plantilla_personalizada}
   - **Then:** 200 OK, datos completos, `is_builtin: false`, `tenant_id` del usuario

3. Respuesta desde cache (segunda llamada)
   - **Given:** Primera llamada ya realizada
   - **When:** Segunda GET identica
   - **Then:** 200 OK, `X-Cache: HIT`, tiempo < 80ms

4. Assistant puede acceder a plantillas
   - **Given:** Usuario con rol `assistant`
   - **When:** GET /api/v1/evolution-templates/{id}
   - **Then:** 200 OK

#### Edge Cases
1. Plantilla integrada accesible desde cualquier tenant
   - **Given:** Dos tenants distintos, plantilla integrada
   - **When:** GET desde tenant A y desde tenant B
   - **Then:** Ambos reciben 200 OK con el mismo contenido

2. Cache TTL expira
   - **Given:** Cache entry expirada (simulada)
   - **When:** GET /api/v1/evolution-templates/{id}
   - **Then:** 200 OK, `X-Cache: MISS`, cache re-populado

#### Error Cases
1. Plantilla de otro tenant
   - **Given:** Plantilla personalizada del tenant B, usuario del tenant A
   - **When:** GET /api/v1/evolution-templates/{id_de_tenant_B}
   - **Then:** 404 Not Found (no revelar existencia)

2. UUID inexistente
   - **Given:** UUID valido en formato pero sin registro en BD
   - **When:** GET /api/v1/evolution-templates/00000000-0000-0000-0000-000000000000
   - **Then:** 404 con mensaje "La plantilla de evolucion no fue encontrada."

3. Plantilla inactiva
   - **Given:** Plantilla con `is_active=false`
   - **When:** GET /api/v1/evolution-templates/{id}
   - **Then:** 404

4. Token expirado
   - **Given:** JWT con `exp` en el pasado
   - **When:** GET /api/v1/evolution-templates/{id}
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** Un `doctor` del tenant A, un `assistant` del tenant A, un `doctor` del tenant B.

**Entities:** Las 10 plantillas integradas (seed), al menos 2 plantillas personalizadas del tenant A, 1 plantilla personalizada del tenant B (para test de aislamiento).

### Mocking Strategy

- **Redis:** fakeredis para simular cache hit/miss
- **Database:** SQLite en memoria con esquema relacional completo

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Plantillas integradas son accesibles por cualquier tenant autenticado
- [ ] Plantillas personalizadas solo son accesibles por el tenant propietario
- [ ] La respuesta incluye pasos ordenados por `order` ASC
- [ ] Variables anidadas correctamente en cada paso
- [ ] Cache funciona: segunda llamada devuelve `X-Cache: HIT`
- [ ] Plantilla de otro tenant retorna 404 (no 403)
- [ ] Plantilla inactiva retorna 404
- [ ] All test cases pass
- [ ] Performance targets met (< 80ms cache hit, < 350ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Edicion de plantillas (PATCH)
- Eliminacion de plantillas (DELETE)
- Uso de plantillas para generar evoluciones (ver CR-aplicar-template)
- Historial de cambios de una plantilla

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models con anidamiento completo)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (role + tenant isolation)
- [x] Side effects listed
- [x] Examples provided (plantilla completa con 10 pasos)

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (clinical-records domain)
- [x] Uses tenant schema isolation (query filtra por tenant_id o NULL)
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models match M1-TECHNICAL-SPEC.md

### Hook 3: Security & Privacy
- [x] Auth level stated (Authenticated, doctor/assistant)
- [x] Input sanitization defined (UUID validation)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure (plantillas son estructuras, no datos de pacientes)
- [x] Tenant isolation: plantilla de otro tenant retorna 404

### Hook 4: Performance & Scalability
- [x] Response time target defined (< 80ms cache hit)
- [x] Caching strategy stated (Redis 30 min, tenant-namespaced)
- [x] DB queries optimized (selectinload evita N+1, indexes listados)
- [x] Pagination N/A (se retorna plantilla completa)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id incluido)
- [x] Audit log entries N/A (lectura de metadata sin PHI)
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
