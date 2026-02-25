# Buscar Codigos CUPS (CR-11)

---

## Overview

**Feature:** Busqueda typeahead de codigos CUPS (Clasificacion Unica de Procedimientos en Salud — subconjunto dental) para uso en formularios de procedimientos. Busqueda full-text en codigo y descripcion en espanol. Optimizado para latencia < 100ms. Cache Redis 1 hora compartido entre tenants. CUPS es el sistema colombiano de codigos de procedimientos, pero funciona como base para los sistemas de codigos de procedimientos de otros paises en el MVP.

**Domain:** clinical-records

**Priority:** High

**Dependencies:** infra/authentication-rules.md, public schema (cups_catalog table)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** Cualquier usuario autenticado (doctor, assistant, receptionist, clinic_owner, superadmin)
- **Tenant context:** Not required — catalogo publico en schema `public`, compartido entre todos los tenants
- **Special rules:** Sin contexto de tenant. Cache compartido entre tenants. No contiene PHI.

---

## Endpoint

```
GET /api/v1/catalog/cups
```

**Rate Limiting:**
- 200 requests por minuto por usuario
- Redis sliding window: `dentalos:rate:cups_search:{user_id}`

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer JWT token | Bearer eyJhbGc... |

### URL Parameters

N/A

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| q | Yes | string | Minimo 2 caracteres, maximo 100 | Termino de busqueda en codigo o descripcion | restauracion |
| limit | No | integer | 1-20, default 20 | Numero maximo de resultados | 10 |
| category | No | string | Codigo de categoria CUPS | Filtrar por categoria de procedimiento | 89 |

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
      "code": "string — codigo CUPS (ej: 89.01.01.01)",
      "description": "string — descripcion oficial en espanol",
      "category": "string — categoria del procedimiento",
      "category_code": "string — codigo de categoria",
      "unit": "string | null — unidad de medida del procedimiento",
      "requires_anesthesia": "boolean | null",
      "is_dental": "boolean — siempre true"
    }
  ],
  "total": "integer — cantidad de resultados retornados",
  "query": "string — termino de busqueda aplicado",
  "category_filter": "string | null — categoria filtrada si se aplico",
  "cached": "boolean"
}
```

**Example (busqueda: "restauracion"):**
```json
{
  "data": [
    {
      "code": "89.01.01.01",
      "description": "Restauracion en resina compuesta de una superficie en diente temporal",
      "category": "Procedimientos dentales basicos",
      "category_code": "89.01",
      "unit": "Diente",
      "requires_anesthesia": false,
      "is_dental": true
    },
    {
      "code": "89.01.01.02",
      "description": "Restauracion en resina compuesta de dos superficies en diente temporal",
      "category": "Procedimientos dentales basicos",
      "category_code": "89.01",
      "unit": "Diente",
      "requires_anesthesia": false,
      "is_dental": true
    },
    {
      "code": "89.01.01.03",
      "description": "Restauracion en resina compuesta de tres o mas superficies en diente temporal",
      "category": "Procedimientos dentales basicos",
      "category_code": "89.01",
      "unit": "Diente",
      "requires_anesthesia": true,
      "is_dental": true
    },
    {
      "code": "89.01.02.01",
      "description": "Restauracion en resina compuesta de una superficie en diente permanente",
      "category": "Procedimientos dentales basicos",
      "category_code": "89.01",
      "unit": "Diente",
      "requires_anesthesia": false,
      "is_dental": true
    },
    {
      "code": "89.01.02.02",
      "description": "Restauracion en resina compuesta de dos superficies en diente permanente",
      "category": "Procedimientos dentales basicos",
      "category_code": "89.01",
      "unit": "Diente",
      "requires_anesthesia": false,
      "is_dental": true
    }
  ],
  "total": 5,
  "query": "restauracion",
  "category_filter": null,
  "cached": false
}
```

**Example (busqueda por codigo: "89.01"):**
```json
{
  "data": [
    {
      "code": "89.01.01.01",
      "description": "Restauracion en resina compuesta de una superficie en diente temporal",
      "category": "Procedimientos dentales basicos",
      "category_code": "89.01",
      "unit": "Diente",
      "requires_anesthesia": false,
      "is_dental": true
    },
    {
      "code": "89.01.01.02",
      "description": "Restauracion en resina compuesta de dos superficies en diente temporal",
      "category": "Procedimientos dentales basicos",
      "category_code": "89.01",
      "unit": "Diente",
      "requires_anesthesia": false,
      "is_dental": true
    }
  ],
  "total": 2,
  "query": "89.01",
  "category_filter": null,
  "cached": true
}
```

### Error Responses

#### 400 Bad Request
**When:** Parametro `q` faltante o menor a 2 caracteres.

```json
{
  "error": "invalid_input",
  "message": "El termino de busqueda no es valido.",
  "details": {
    "q": ["El termino de busqueda debe tener al menos 2 caracteres."]
  }
}
```

#### 401 Unauthorized
**When:** Token ausente, expirado o invalido.

#### 429 Too Many Requests
**When:** Rate limit excedido.

```json
{
  "error": "rate_limit_exceeded",
  "message": "Demasiadas solicitudes de busqueda. Intente nuevamente en un momento.",
  "details": { "retry_after_seconds": 10 }
}
```

#### 500 Internal Server Error
**When:** Error inesperado en la busqueda o en el catalogo.

---

## Business Logic

**Step-by-step process:**

1. Validar parametro `q` (requerido, minimo 2 chars, maximo 100 chars). Si invalido: retornar 400.
2. Verificar autenticacion via JWT (cualquier rol valido).
3. Construir cache key: `dentalos:catalog:cups:search:{normalized_q}:{limit}:{category_filter}` (sin tenant_id).
4. Consultar Redis por la cache key. Si hit: retornar con `cached: true`.
5. Si cache miss: ejecutar busqueda full-text en `public.cups_catalog`:
   - Detectar si `q` parece un codigo CUPS (numeros y puntos: ej. "89", "89.01").
   - Si es busqueda por codigo: `WHERE code LIKE '{q}%'` union full-text.
   - Si es busqueda por descripcion: `WHERE search_vector @@ plainto_tsquery('spanish', '{q}')`.
   - Si `category` provisto: agregar `AND category_code = '{category}'`.
   - Ordenar por relevancia (ts_rank DESC) o por codigo ASC si es busqueda exacta de codigo.
6. Limitar a `min(limit, 20)` resultados.
7. Almacenar resultado en Redis con TTL de 3600s.
8. Retornar 200 con `cached: false`.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| q | Requerido. Minimo 2 caracteres. Maximo 100 caracteres. | "El termino de busqueda debe tener al menos 2 caracteres." |
| limit | Opcional. Entero entre 1 y 20. Default 20. | "El limite debe ser entre 1 y 20." |
| category | Opcional. Codigo de categoria valido si provisto. | "La categoria especificada no existe en el catalogo CUPS." |

**Business Rules:**

- El catalogo CUPS es el subconjunto dental (capitulo 89 de CUPS Colombia: procedimientos odontologicos y maxilofaciales).
- CUPS es especifico de Colombia pero en el MVP sirve como base para los codigos de procedimientos de otros paises. Tenants de otros paises usan este mismo catalogo hasta que se implementen adaptaciones por pais (post-MVP).
- La busqueda soporta tanto busqueda por codigo (ej: "89.01", "89.01.01") como por descripcion en espanol (ej: "restauracion", "endodoncia", "exodoncia").
- El catalogo NO se filtra por tenant — es un catalogo publico compartido.
- El cache es compartido entre todos los tenants (no PHI, catalogo publico).
- El campo `requires_anesthesia` es informativo para la UI (puede mostrar icono de alerta).

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| q="89" (busqueda de categoria completa) | Retorna hasta 20 procedimientos del capitulo 89 |
| q="ex" (2 chars) | Busqueda valida; puede retornar exodoncia, extracion, etc. |
| Sin resultados para el query | `data: []`, `total: 0` — NO retornar 404 |
| category filter que no existe | Retornar `data: []` (no error) |
| q con tildes (ej: "extraccion" vs "extraccion") | Full-text con stemming espanol maneja ambas formas |
| Terminos sinonimos en espanol | Full-text con diccionario espanol puede no cubrir sinonimos; retornar resultado de best-effort |

---

## Side Effects

### Database Changes

**Public schema tables read:**
- `public.cups_catalog`: SELECT — busqueda full-text

No hay escrituras en este endpoint.

**Example query (SQLAlchemy):**
```python
from sqlalchemy import text

is_code_search = bool(re.match(r'^\d', q))

if is_code_search:
    stmt = text("""
        SELECT code, description, category, category_code, unit, requires_anesthesia, is_dental,
               CASE WHEN code LIKE :code_prefix THEN 1 ELSE 0 END AS code_priority,
               ts_rank(search_vector, plainto_tsquery('spanish', :q)) AS rank
        FROM public.cups_catalog
        WHERE is_dental = true
          AND (:category_filter IS NULL OR category_code = :category_filter)
          AND (
              code LIKE :code_prefix
              OR search_vector @@ plainto_tsquery('spanish', :q)
          )
        ORDER BY code_priority DESC, rank DESC, code ASC
        LIMIT :limit
    """)
    result = await session.execute(stmt, {
        "q": q,
        "code_prefix": q + "%",
        "limit": limit,
        "category_filter": category_filter,
    })
else:
    stmt = text("""
        SELECT code, description, category, category_code, unit, requires_anesthesia, is_dental,
               ts_rank(search_vector, plainto_tsquery('spanish', :q)) AS rank
        FROM public.cups_catalog
        WHERE is_dental = true
          AND (:category_filter IS NULL OR category_code = :category_filter)
          AND search_vector @@ plainto_tsquery('spanish', :q)
        ORDER BY rank DESC, code ASC
        LIMIT :limit
    """)
    result = await session.execute(stmt, {
        "q": q,
        "limit": limit,
        "category_filter": category_filter,
    })
```

**Nota:** SQL raw justificado por el uso de funciones especializadas PostgreSQL full-text (`ts_rank`, `plainto_tsquery`, `@@`). Todos los parametros son named (`:q`, `:limit`) — sin concatenacion de strings de usuario.

### Cache Operations

**Cache keys affected:**
- `dentalos:catalog:cups:search:{sha256(q.lower().strip())}:{limit}:{category}`: GET (hit) o SET (miss)

**Cache TTL:** 3600s (1 hora)

### Queue Jobs (RabbitMQ)

No aplica — endpoint de solo lectura de catalogo publico.

### Audit Log

**Audit entry:** No — catalogo publico sin PHI

### Notifications

**Notifications triggered:** No

---

## Performance

### Expected Response Time
- **Target:** < 50ms (con cache hit)
- **Maximum acceptable:** < 100ms (incluyendo cache miss con DB query)

### Caching Strategy
- **Strategy:** Redis cache con TTL de 1 hora; compartido entre todos los tenants
- **Cache key:** `dentalos:catalog:cups:search:{sha256(q.lower().strip())}:{limit}:{category_filter}`
- **TTL:** 3600s
- **Invalidation:** Al actualizar el catalogo CUPS (operacion de admin/superadmin, raramente)

### Database Performance

**Queries executed:** 0 (cache hit) o 1 (cache miss — full-text search en public schema)

**Indexes required:**
- `public.cups_catalog.search_vector` — GIN INDEX (para full-text search)
- `public.cups_catalog.code` — INDEX (para busqueda por prefijo de codigo)
- `public.cups_catalog.is_dental` — INDEX (filtro base)
- `public.cups_catalog.category_code` — INDEX (para filtro por categoria)

**Schema para public.cups_catalog:**
```sql
CREATE TABLE public.cups_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    category VARCHAR(200),
    category_code VARCHAR(20),
    unit VARCHAR(50),
    requires_anesthesia BOOLEAN,
    is_dental BOOLEAN NOT NULL DEFAULT false,
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('spanish', code || ' ' || description)
    ) STORED,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX cups_search_vector_idx ON public.cups_catalog USING GIN(search_vector);
CREATE INDEX cups_code_idx ON public.cups_catalog(code);
CREATE INDEX cups_is_dental_idx ON public.cups_catalog(is_dental) WHERE is_dental = true;
CREATE INDEX cups_category_code_idx ON public.cups_catalog(category_code);
```

**N+1 prevention:** No aplica (query unica contra catalogo publico).

### Pagination

**Pagination:** No (maximo 20 resultados por diseno — typeahead)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| q | Strip whitespace, maxlen 100, remover caracteres SQL peligrosos | Aunque se usan parametros named, sanitizar como defensa en profundidad |
| limit | Pydantic int, rango 1-20 | Prevenir DoS |
| category | Pydantic str + strip + maxlen 20 | Prevenir inyeccion |

### SQL Injection Prevention

**All queries use:** Parametros named via `text()` de SQLAlchemy. Ver justificacion en Business Logic. Ningun valor de usuario es concatenado directamente en el SQL.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Ninguno — catalogo publico de codigos de procedimientos.

**Audit requirement:** No requerido — sin PHI.

---

## Testing

### Test Cases

#### Happy Path
1. Busqueda por descripcion parcial
   - **Given:** Catalogo CUPS cargado, usuario autenticado
   - **When:** GET /api/v1/catalog/cups?q=restauracion
   - **Then:** 200 OK, codigos de restauracion retornados, ordenados por relevancia

2. Busqueda por prefijo de codigo
   - **Given:** Catalogo cargado, usuario autenticado
   - **When:** GET ?q=89.01
   - **Then:** 200 OK, todos los subcategorias de 89.01.x como primeros resultados

3. Cache hit en segunda solicitud
   - **Given:** Redis con resultado cacheado para q=exodoncia
   - **When:** Segunda solicitud con q=exodoncia
   - **Then:** 200 OK, `cached: true`, respuesta < 50ms

4. Filtro por categoria
   - **Given:** Catalogo con multiples categorias
   - **When:** GET ?q=resina&category=89.01
   - **Then:** 200 OK, solo procedimientos de categoria 89.01

#### Edge Cases
1. q de exactamente 2 caracteres
   - **Given:** Usuario autenticado
   - **When:** GET ?q=ex
   - **Then:** 200 OK, resultados que coincidan

2. Sin resultados
   - **Given:** q que no coincide con ningun codigo dental
   - **When:** GET ?q=zz
   - **Then:** 200 OK, `data: []`, `total: 0`

3. q con tilde (extraccion)
   - **Given:** Procedimiento "Extraccion dental simple" en catalogo
   - **When:** GET ?q=extraccion (sin tilde)
   - **Then:** 200 OK, resultado encontrado (stemming espanol)

#### Error Cases
1. q de 1 caracter
   - **Given:** Usuario autenticado
   - **When:** GET ?q=r
   - **Then:** 400 con mensaje de minimo 2 caracteres

2. q faltante
   - **Given:** Usuario autenticado
   - **When:** GET sin parametro q
   - **Then:** 400 con campo q requerido

3. limit=25 (sobre el maximo)
   - **Given:** Usuario autenticado
   - **When:** GET ?q=restauracion&limit=25
   - **Then:** 400 con limite invalido (max 20)

4. Sin token
   - **Given:** Solicitud sin Authorization header
   - **When:** GET al endpoint
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** Cualquier usuario autenticado

**Catalog:** Tabla `public.cups_catalog` cargada con al menos 50 codigos dentales del capitulo 89 CUPS en el entorno de test

### Mocking Strategy

- **Redis:** fakeredis para simular cache hit/miss
- **PostgreSQL full-text:** Usar DB de test con GIN index configurado y datos seed

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Busqueda por descripcion en espanol retorna resultados relevantes ordenados por ts_rank
- [ ] Busqueda por prefijo de codigo (89, 89.01, 89.01.01) retorna codigos en orden ascendente
- [ ] Resultados cacheados en Redis 1 hora con `cached: true` en segunda solicitud
- [ ] Cache compartido entre todos los tenants (sin tenant_id en cache key)
- [ ] Filtro por `category` funciona correctamente
- [ ] Minimo 2 caracteres en `q` — 400 si menor
- [ ] Maximo 20 resultados por solicitud
- [ ] Respuesta < 100ms en cache miss, < 50ms en cache hit
- [ ] Sin audit log (no PHI)
- [ ] GIN index configurado en `public.cups_catalog.search_vector`
- [ ] Schema de `cups_catalog` documentado con DDL
- [ ] All test cases pass
- [ ] Performance targets met (< 100ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creacion o edicion del catalogo CUPS (solo via admin/superadmin)
- Busqueda de codigos CIE-10 (ver CR-10)
- Adaptaciones de codigos de procedimientos para paises distintos a Colombia (post-MVP)
- Precios o tarifas de procedimientos (ver billing/)
- CUPS completo (todos los capitulos) — solo subconjunto dental (capitulo 89)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas incluyendo category filter)
- [x] All outputs defined (response models con unit y requires_anesthesia)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (authenticated, no tenant context)
- [x] Side effects listed (cache SET)
- [x] Examples provided (busqueda por descripcion y por codigo)

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (catalogo publico separado de datos de tenant)
- [x] Uses public schema isolation
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] DDL del schema definido con indexes

### Hook 3: Security & Privacy
- [x] Auth level stated (authenticated, any role)
- [x] Input sanitization defined (Pydantic + strip + sanitize)
- [x] SQL injection prevented (parametros named en SQL raw justificado)
- [x] No PHI en catalogo publico
- [x] Sin audit log requerido

### Hook 4: Performance & Scalability
- [x] Response time target definido (< 100ms, < 50ms cached)
- [x] Caching strategy stated (Redis 1h, compartido entre tenants)
- [x] DB queries optimized (GIN index, partial indexes)
- [x] Pagination: maximo 20 (typeahead, sin paginacion)

### Hook 5: Observability
- [x] Structured logging (JSON, user_id incluido)
- [x] Sin audit log (no PHI)
- [x] Error tracking (Sentry-compatible)
- [x] Cache hit ratio monitoreable

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified (cups_catalog con datos seed)
- [x] Mocking strategy (fakeredis)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
