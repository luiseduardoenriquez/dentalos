# Evolution Template List (CR-15)

---

## Overview

**Feature:** Listar las plantillas de evolucion clinica disponibles para el tenant. Incluye plantillas integradas del sistema (10 procedimientos comunes predefinidos) y plantillas personalizadas creadas por el tenant. Soporta filtrado por tipo de procedimiento, codigo CUPS, complejidad y origen (integrado vs. personalizado).

**Domain:** clinical-records

**Priority:** High

**Dependencies:** CR-16 (evolution-template-create.md), treatment-plans (para auto-seleccion de plantilla al agregar procedimiento), I-02 (authentication-rules.md)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** doctor, assistant
- **Tenant context:** Required — resuelto desde claims del JWT (`tenant_id`)
- **Special rules:** Los asistentes solo pueden listar; no pueden crear ni editar plantillas. Las plantillas integradas son globales pero se sirven en contexto de tenant para incluir las personalizadas del mismo.

---

## Endpoint

```
GET /api/v1/evolution-templates
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

N/A

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| procedure_type | No | string | Max 100 chars | Filtrar por tipo de procedimiento (nombre libre o categoria) | resina |
| cups_code | No | string | Formato CUPS colombiano | Filtrar por codigo CUPS exacto | 89.31.01 |
| complexity | No | enum | basic, standard, complex | Filtrar por nivel de complejidad del procedimiento | standard |
| is_builtin | No | boolean | true / false | Si true: solo plantillas del sistema. Si false: solo personalizadas del tenant | false |
| page | No | integer | >= 1, default: 1 | Pagina actual | 1 |
| page_size | No | integer | 1–100, default: 20 | Registros por pagina | 20 |

### Request Body Schema

N/A (GET request)

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "data": [
    {
      "id": "UUID",
      "name": "string",
      "procedure_type": "string",
      "cups_code": "string | null",
      "complexity": "basic | standard | complex",
      "is_builtin": "boolean",
      "steps_count": "integer",
      "variables_count": "integer",
      "tenant_id": "UUID | null",
      "created_at": "ISO8601",
      "updated_at": "ISO8601"
    }
  ],
  "pagination": {
    "page": "integer",
    "page_size": "integer",
    "total": "integer",
    "total_pages": "integer"
  }
}
```

**Example:**
```json
{
  "data": [
    {
      "id": "etpl_550e8400-e29b-41d4-a716-446655440001",
      "name": "Resina Oclusal",
      "procedure_type": "restauracion",
      "cups_code": "89.31.01",
      "complexity": "standard",
      "is_builtin": true,
      "steps_count": 10,
      "variables_count": 4,
      "tenant_id": null,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    },
    {
      "id": "etpl_660e8400-e29b-41d4-a716-446655440002",
      "name": "Resina Proximal",
      "procedure_type": "restauracion",
      "cups_code": "89.31.02",
      "complexity": "standard",
      "is_builtin": true,
      "steps_count": 11,
      "variables_count": 4,
      "tenant_id": null,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    },
    {
      "id": "etpl_770e8400-e29b-41d4-a716-446655440010",
      "name": "Resina Oclusal Personalizada Dr. Gomez",
      "procedure_type": "restauracion",
      "cups_code": null,
      "complexity": "standard",
      "is_builtin": false,
      "steps_count": 8,
      "variables_count": 3,
      "tenant_id": "tn_7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "created_at": "2026-02-10T14:30:00Z",
      "updated_at": "2026-02-10T14:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 13,
    "total_pages": 1
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** Parametros de filtro invalidos (ej. `complexity` con valor fuera del enum, `page_size` mayor a 100).

**Example:**
```json
{
  "error": "invalid_input",
  "message": "Los parametros de busqueda no son validos.",
  "details": {
    "complexity": ["Debe ser uno de: basic, standard, complex."]
  }
}
```

#### 401 Unauthorized
**When:** Token JWT ausente, expirado o invalido. Ver `infra/authentication-rules.md`.

#### 403 Forbidden
**When:** Rol del usuario no tiene permiso para este endpoint (ej. `patient`, `receptionist`).

```json
{
  "error": "forbidden",
  "message": "No tienes permiso para acceder a las plantillas de evolucion."
}
```

#### 429 Too Many Requests
**When:** Rate limit excedido. Ver `infra/rate-limiting.md`.

#### 500 Internal Server Error
**When:** Error inesperado en base de datos o cache.

---

## Business Logic

**Step-by-step process:**

1. Validar token JWT y extraer `tenant_id`, `user_id`, `role` de los claims.
2. Verificar que el rol sea `doctor` o `assistant`. Si no, retornar 403.
3. Validar parametros de query contra schema Pydantic: enum `complexity`, rango `page_size`, formato `cups_code`.
4. Construir cache key: `tenant:{tenant_id}:evolution_templates:{hash_of_filters}`.
5. Intentar leer desde Redis. Si cache hit, retornar directamente con header `X-Cache: HIT`.
6. Si cache miss: ejecutar query contra base de datos:
   - Seleccionar plantillas donde `tenant_id IS NULL` (integradas) UNION plantillas donde `tenant_id = :tenant_id` (personalizadas del tenant).
   - Aplicar filtros `WHERE` segun parametros de query recibidos.
   - Ordenar: integradas primero (`is_builtin DESC`), luego por `name ASC`.
   - Paginar con LIMIT/OFFSET.
7. Calcular `total` con COUNT separado (o subquery) para el objeto `pagination`.
8. Mapear resultados a schema de respuesta (incluir `steps_count` y `variables_count` como campos calculados o columnas desnormalizadas).
9. Escribir resultado en Redis con TTL de 30 minutos.
10. Retornar 200 OK con datos y metadata de paginacion. Incluir header `X-Cache: MISS`.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| complexity | Enum: basic, standard, complex | "Debe ser uno de: basic, standard, complex." |
| page | Integer >= 1 | "La pagina debe ser mayor o igual a 1." |
| page_size | Integer entre 1 y 100 | "El tamano de pagina debe estar entre 1 y 100." |
| cups_code | Formato alfanumerico con puntos, max 20 chars | "El codigo CUPS no tiene un formato valido." |
| is_builtin | Boolean (true/false) | "El valor debe ser true o false." |

**Business Rules:**

- Las plantillas integradas (`is_builtin = true`) tienen `tenant_id = NULL` y son compartidas por todos los tenants.
- Las plantillas personalizadas solo son visibles para el tenant que las creo.
- El listado combina siempre integradas + personalizadas del tenant, a menos que se filtre con `is_builtin`.
- Las plantillas integradas del sistema son las 10 siguientes: Resina Oclusal, Resina Proximal, Endodoncia Unirradicular, Endodoncia Multirradicular, Exodoncia Simple, Exodoncia Quirurgica, Limpieza/Profilaxis, Sellantes, Corona Provisional, Amalgama.
- El listado no incluye el detalle de pasos (solo metadata). Para pasos completos usar CR-17.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| Tenant sin plantillas personalizadas | Retornar solo las 10 integradas |
| Filtro `is_builtin=false` en tenant sin personalizadas | Retornar lista vacia con `total: 0` |
| Filtro `cups_code` que no existe | Retornar lista vacia con `total: 0` |
| page mayor a total_pages | Retornar lista vacia en `data`, `total` correcto |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- `evolution_templates`: SELECT — lectura de plantillas integradas y del tenant

**Example query (SQLAlchemy):**
```python
from sqlalchemy import select, or_, func

stmt = (
    select(EvolutionTemplate)
    .where(
        or_(
            EvolutionTemplate.tenant_id.is_(None),
            EvolutionTemplate.tenant_id == tenant_id
        )
    )
    .where(EvolutionTemplate.is_active == True)
    .order_by(EvolutionTemplate.is_builtin.desc(), EvolutionTemplate.name.asc())
    .offset((page - 1) * page_size)
    .limit(page_size)
)
results = await session.execute(stmt)
templates = results.scalars().all()
```

### Cache Operations

**Cache keys affected:**
- `tenant:{tenant_id}:evolution_templates:{filter_hash}`: SET — resultado paginado con filtros aplicados

**Cache TTL:** 1800s (30 minutos por tenant)

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** Ninguno

### Audit Log

**Audit entry:** No

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 100ms (cache hit)
- **Maximum acceptable:** < 400ms (cache miss con query)

### Caching Strategy
- **Strategy:** Redis cache, invalidado al crear/editar/eliminar plantilla del tenant
- **Cache key:** `tenant:{tenant_id}:evolution_templates:{filter_hash}` donde `filter_hash` es SHA-256 de los parametros de query serializados
- **TTL:** 1800s (30 minutos)
- **Invalidation:** Al ejecutar CR-16 (crear), CR-17-update (editar) o delete de plantilla del mismo tenant

### Database Performance

**Queries executed:** 2 (count + select paginado)

**Indexes required:**
- `evolution_templates.tenant_id` — INDEX (NULL para integradas, UUID para personalizadas)
- `evolution_templates.procedure_type` — INDEX
- `evolution_templates.cups_code` — INDEX
- `evolution_templates.complexity` — INDEX
- `evolution_templates.is_builtin` — INDEX
- `evolution_templates.is_active` — INDEX

**N+1 prevention:** `steps_count` y `variables_count` se almacenan como columnas desnormalizadas en `evolution_templates`, actualizadas por trigger o en servicio al modificar pasos. No se hace JOIN en el listado.

### Pagination

**Pagination:** Yes

- **Style:** offset-based
- **Default page size:** 20
- **Max page size:** 100

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| procedure_type | Pydantic str, strip, max_length=100 | Prevenir busquedas maliciosas |
| cups_code | Pydantic str, strip, regex `^[A-Za-z0-9.\\-]{1,20}$` | Solo alfanumerico con puntos/guiones |
| complexity | Pydantic Enum | Rechazo automatico de valores invalidos |
| is_builtin | Pydantic bool | Conversion estricta |

### SQL Injection Prevention

**All queries use:** SQLAlchemy ORM with parameterized queries. No raw SQL.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None — este endpoint devuelve metadata de plantillas clinicas, no datos de pacientes.

**Audit requirement:** Not required

---

## Testing

### Test Cases

#### Happy Path
1. Listar todas las plantillas (sin filtros)
   - **Given:** Tenant con 3 plantillas personalizadas, usuario con rol `doctor`
   - **When:** GET /api/v1/evolution-templates
   - **Then:** 200 OK, `data` contiene 10 integradas + 3 personalizadas, `total: 13`

2. Filtrar solo plantillas integradas
   - **Given:** Tenant con 3 plantillas personalizadas
   - **When:** GET /api/v1/evolution-templates?is_builtin=true
   - **Then:** 200 OK, `data` contiene exactamente 10 registros, todos con `is_builtin: true`

3. Filtrar por complejidad
   - **Given:** Plantillas con distintas complejidades
   - **When:** GET /api/v1/evolution-templates?complexity=standard
   - **Then:** 200 OK, todos los registros tienen `complexity: "standard"`

4. Respuesta desde cache
   - **Given:** Primera llamada ya ejecutada (cache poblado)
   - **When:** Segunda GET identica
   - **Then:** 200 OK, header `X-Cache: HIT`, tiempo de respuesta < 50ms

#### Edge Cases
1. Tenant sin plantillas personalizadas
   - **Given:** Tenant nuevo sin ninguna plantilla creada
   - **When:** GET /api/v1/evolution-templates
   - **Then:** 200 OK, `data` contiene exactamente las 10 integradas

2. Filtro `is_builtin=false` en tenant sin personalizadas
   - **Given:** Tenant nuevo
   - **When:** GET /api/v1/evolution-templates?is_builtin=false
   - **Then:** 200 OK, `data: []`, `total: 0`

3. Paginacion segunda pagina vacia
   - **Given:** Tenant con 13 plantillas totales, page_size=20
   - **When:** GET /api/v1/evolution-templates?page=2&page_size=20
   - **Then:** 200 OK, `data: []`, `total: 13`, `total_pages: 1`

#### Error Cases
1. Rol no autorizado
   - **Given:** Usuario con rol `receptionist`
   - **When:** GET /api/v1/evolution-templates
   - **Then:** 403 Forbidden con mensaje en espanol

2. Parametro complexity invalido
   - **Given:** Query con `complexity=ultracomlex`
   - **When:** GET /api/v1/evolution-templates?complexity=ultracomplex
   - **Then:** 400 Bad Request con detalle del campo

3. Token expirado
   - **Given:** JWT con `exp` en el pasado
   - **When:** GET /api/v1/evolution-templates
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** Un usuario `doctor` activo, un usuario `assistant` activo, un usuario `receptionist` (para test de 403).

**Entities:** 10 plantillas integradas (`is_builtin=true`, `tenant_id=null`) en base de datos seed. 3 plantillas personalizadas del tenant de prueba.

### Mocking Strategy

- **Redis:** fakeredis para simular cache hit/miss en unit tests
- **Database:** SQLite en memoria para tests de integracion

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Las 10 plantillas integradas son retornadas para cualquier tenant
- [ ] Las plantillas personalizadas del tenant son visibles solo para ese tenant
- [ ] Filtros por `procedure_type`, `cups_code`, `complexity` e `is_builtin` funcionan correctamente
- [ ] Paginacion retorna `total`, `total_pages`, `page`, `page_size` correctos
- [ ] Resultado se almacena en Redis por 30 minutos (cache miss → HIT en segunda llamada)
- [ ] Rol `receptionist` y `patient` reciben 403
- [ ] All test cases pass
- [ ] Performance targets met (< 100ms cache hit, < 400ms miss)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Detalle de pasos y variables de cada plantilla (ver CR-17)
- Creacion de plantillas (ver CR-16)
- Edicion o eliminacion de plantillas
- Versionado de plantillas integradas
- Exportar/importar plantillas entre tenants

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
- [x] Input sanitization defined (Pydantic)
- [x] SQL injection prevented (SQLAlchemy ORM)
- [x] No PHI exposure in logs or errors
- [x] Audit trail not required (metadata de plantillas, no datos clinicos)

### Hook 4: Performance & Scalability
- [x] Response time target defined
- [x] Caching strategy stated (tenant-namespaced, 30 min)
- [x] DB queries optimized (indexes listados, count + select separados)
- [x] Pagination applied (offset-based, max 100)

### Hook 5: Observability
- [x] Structured logging (JSON, tenant_id included)
- [x] Audit log entries defined (N/A para GET de metadata)
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
