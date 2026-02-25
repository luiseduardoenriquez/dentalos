# Buscar Codigos CIE-10 (CR-10)

---

## Overview

**Feature:** Busqueda typeahead de codigos CIE-10 (subconjunto dental) para uso en formularios de diagnostico. Busqueda full-text en codigo y descripcion en espanol (ts_vector con configuracion spanish). Optimizado para latencia < 100ms. Resultado cacheado en Redis por 1 hora (compartido entre todos los tenants ya que es un catalogo publico).

**Domain:** clinical-records

**Priority:** High

**Dependencies:** infra/authentication-rules.md, public schema (cie10_catalog table)

---

## Authentication

- **Level:** Authenticated
- **Roles allowed:** Cualquier usuario autenticado (doctor, assistant, receptionist, clinic_owner, superadmin)
- **Tenant context:** Not required — catalogo publico en schema `public`, compartido entre todos los tenants
- **Special rules:** Sin contexto de tenant. Cache compartido entre todos los tenants. No contiene PHI.

---

## Endpoint

```
GET /api/v1/catalog/cie10
```

**Rate Limiting:**
- 200 requests por minuto por usuario
- Redis sliding window: `dentalos:rate:cie10_search:{user_id}`

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
| q | Yes | string | Minimo 2 caracteres, maximo 100 | Termino de busqueda en codigo o descripcion | caries |
| limit | No | integer | 1-20, default 20 | Numero maximo de resultados | 10 |

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
      "code": "string — codigo CIE-10 (ej: K02.1)",
      "description": "string — descripcion oficial en espanol",
      "category": "string — categoria de la enfermedad (ej: K00-K14 Enfermedades de la cavidad bucal)",
      "is_dental": "boolean — siempre true (solo catalogo dental)"
    }
  ],
  "total": "integer — cantidad de resultados retornados (maximo limit)",
  "query": "string — termino de busqueda aplicado",
  "cached": "boolean — true si la respuesta viene del cache de Redis"
}
```

**Example (busqueda por descripcion: "caries"):**
```json
{
  "data": [
    {
      "code": "K02.0",
      "description": "Caries del esmalte",
      "category": "K00-K14 Enfermedades de la cavidad bucal, de las glandulas salivales y de los maxilares",
      "is_dental": true
    },
    {
      "code": "K02.1",
      "description": "Caries de la dentina",
      "category": "K00-K14 Enfermedades de la cavidad bucal, de las glandulas salivales y de los maxilares",
      "is_dental": true
    },
    {
      "code": "K02.2",
      "description": "Caries del cemento",
      "category": "K00-K14 Enfermedades de la cavidad bucal, de las glandulas salivales y de los maxilares",
      "is_dental": true
    },
    {
      "code": "K02.3",
      "description": "Caries dentaria detenida",
      "category": "K00-K14 Enfermedades de la cavidad bucal, de las glandulas salivales y de los maxilares",
      "is_dental": true
    },
    {
      "code": "K02.4",
      "description": "Odontoclasia",
      "category": "K00-K14 Enfermedades de la cavidad bucal, de las glandulas salivales y de los maxilares",
      "is_dental": true
    },
    {
      "code": "K02.5",
      "description": "Caries con exposicion pulpar",
      "category": "K00-K14 Enfermedades de la cavidad bucal, de las glandulas salivales y de los maxilares",
      "is_dental": true
    },
    {
      "code": "K02.8",
      "description": "Otras caries dentales",
      "category": "K00-K14 Enfermedades de la cavidad bucal, de las glandulas salivales y de los maxilares",
      "is_dental": true
    },
    {
      "code": "K02.9",
      "description": "Caries dental, no especificada",
      "category": "K00-K14 Enfermedades de la cavidad bucal, de las glandulas salivales y de los maxilares",
      "is_dental": true
    }
  ],
  "total": 8,
  "query": "caries",
  "cached": true
}
```

**Example (busqueda por codigo: "K05"):**
```json
{
  "data": [
    {
      "code": "K05.0",
      "description": "Gingivitis aguda",
      "category": "K00-K14 Enfermedades de la cavidad bucal, de las glandulas salivales y de los maxilares",
      "is_dental": true
    },
    {
      "code": "K05.1",
      "description": "Gingivitis cronica",
      "category": "K00-K14 Enfermedades de la cavidad bucal, de las glandulas salivales y de los maxilares",
      "is_dental": true
    },
    {
      "code": "K05.2",
      "description": "Periodontitis aguda",
      "category": "K00-K14 Enfermedades de la cavidad bucal, de las glandulas salivales y de los maxilares",
      "is_dental": true
    },
    {
      "code": "K05.3",
      "description": "Periodontitis cronica",
      "category": "K00-K14 Enfermedades de la cavidad bucal, de las glandulas salivales y de los maxilares",
      "is_dental": true
    }
  ],
  "total": 4,
  "query": "K05",
  "cached": false
}
```

### Error Responses

#### 400 Bad Request
**When:** Parametro `q` faltante o muy corto (< 2 caracteres).

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
**When:** Rate limit excedido (200/min por usuario).

```json
{
  "error": "rate_limit_exceeded",
  "message": "Demasiadas solicitudes de busqueda. Intente nuevamente en un momento.",
  "details": { "retry_after_seconds": 10 }
}
```

#### 500 Internal Server Error
**When:** Error inesperado en la busqueda full-text o en el catalogo.

---

## Business Logic

**Step-by-step process:**

1. Validar parametro `q` (requerido, minimo 2 chars, maximo 100 chars). Si invalido: retornar 400.
2. Verificar autenticacion via JWT (cualquier rol valido).
3. Construir cache key: `dentalos:catalog:cie10:search:{normalized_q}:{limit}` (sin tenant_id — catalogo publico).
4. Consultar Redis por la cache key. Si hit: retornar con `cached: true`.
5. Si cache miss: ejecutar busqueda full-text en `public.cie10_catalog`:
   - Si `q` parece un codigo (empieza con letra seguida de digitos, ej: K, K0, K02): buscar por `code ILIKE '{q}%'` ademas del full-text.
   - Full-text: `WHERE search_vector @@ plainto_tsquery('spanish', '{q}')` ordenado por `ts_rank(search_vector, plainto_tsquery('spanish', '{q}')) DESC`.
   - Si busqueda por codigo: `UNION` de ambos resultados, priorizando matches exactos de codigo.
6. Limitar a `min(limit, 20)` resultados.
7. Almacenar resultado en Redis con TTL de 3600s.
8. Retornar 200 con `cached: false`.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| q | Requerido. Minimo 2 caracteres. Maximo 100 caracteres. | "El termino de busqueda debe tener al menos 2 caracteres." |
| limit | Opcional. Entero entre 1 y 20. Default 20. | "El limite debe ser entre 1 y 20." |

**Business Rules:**

- El catalogo CIE-10 es el subconjunto dental (codigos K00-K14, K08, J34, J35, y codigos relacionados con odontalgia y patologia maxilofacial relevante para odontologia).
- La busqueda soporta tanto busqueda por codigo (ej: "K02", "K02.1") como por descripcion en espanol (ej: "caries", "gingivitis", "periodontitis").
- Los resultados se ordenan por relevancia (ts_rank). Si hay match exacto de codigo, ese resultado aparece primero.
- El catalogo NO se filtra por tenant — es un catalogo publico compartido.
- El cache es compartido entre todos los tenants y usuarios para el mismo query. Esto es seguro porque el catalogo no contiene PHI.
- Terminos de busqueda en espanol: la configuracion `spanish` del ts_vector usa el diccionario de stopwords y stemming en espanol.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| q="ca" (2 chars minimo) | Busqueda valida; retorna codigos con "ca" en descripcion |
| q="K" (1 char) | Retornar 400 — minimo 2 caracteres |
| q="K02" (busqueda exacta por codigo) | Retornar todos los subcategorias de K02.x |
| q="caries dental" (multiple palabras) | Full-text busca documentos con ambas palabras; ordenado por relevancia |
| q con caracteres especiales (ej: "caries/dental") | Sanitizar: remover caracteres que no sean letras, numeros, espacios o puntos |
| No hay resultados para el query | `data: []`, `total: 0` — NO retornar 404 |
| Catalogo vacio (error de configuracion) | Retornar 500 con error interno |

---

## Side Effects

### Database Changes

**Tenant schema tables affected:**
- Ninguna — solo lectura del schema `public`

**Public schema tables read:**
- `public.cie10_catalog`: SELECT — busqueda full-text

**Example query (SQLAlchemy — schema publico):**
```python
from sqlalchemy import text

# Detectar si es busqueda por codigo
is_code_search = bool(re.match(r'^[A-Za-z][0-9]', q))

if is_code_search:
    # Busqueda por codigo (prefix match) + full-text
    stmt = text("""
        SELECT code, description, category, is_dental,
               CASE WHEN UPPER(code) LIKE UPPER(:code_prefix) THEN 1 ELSE 0 END AS code_priority,
               ts_rank(search_vector, plainto_tsquery('spanish', :q)) AS rank
        FROM public.cie10_catalog
        WHERE is_dental = true
          AND (
              UPPER(code) LIKE UPPER(:code_prefix)
              OR search_vector @@ plainto_tsquery('spanish', :q)
          )
        ORDER BY code_priority DESC, rank DESC, code ASC
        LIMIT :limit
    """)
    result = await session.execute(stmt, {
        "q": q, "code_prefix": q.upper() + "%", "limit": limit
    })
else:
    # Solo busqueda full-text por descripcion
    stmt = text("""
        SELECT code, description, category, is_dental,
               ts_rank(search_vector, plainto_tsquery('spanish', :q)) AS rank
        FROM public.cie10_catalog
        WHERE is_dental = true
          AND search_vector @@ plainto_tsquery('spanish', :q)
        ORDER BY rank DESC, code ASC
        LIMIT :limit
    """)
    result = await session.execute(stmt, {"q": q, "limit": limit})
```

**Nota sobre SQL raw:** Se usa SQL raw (via `text()`) por la necesidad de funciones especializadas de PostgreSQL full-text search (`ts_rank`, `plainto_tsquery`) que no tienen soporte ORM directo en SQLAlchemy. La query usa parametros named (`:q`, `:limit`) para prevenir SQL injection.

### Cache Operations

**Cache keys affected:**
- `dentalos:catalog:cie10:search:{normalized_q}:{limit}`: GET (hit) o SET (miss)

**Cache TTL:** 3600s (1 hora)

**Nota:** Cache key NO incluye tenant_id (catalogo publico compartido). La normalizacion de `normalized_q` incluye: lowercase + strip + reemplazo de multiples espacios.

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
- **Cache key:** `dentalos:catalog:cie10:search:{sha256(q.lower().strip())}:{limit}`
- **TTL:** 3600s (1 hora)
- **Invalidation:** Al actualizar el catalogo CIE-10 (operacion de admin, raramente)

### Database Performance

**Queries executed:** 0 (cache hit) o 1 (cache miss — full-text search en public schema)

**Indexes required:**
- `public.cie10_catalog.search_vector` — GIN INDEX (para full-text search)
- `public.cie10_catalog.code` — INDEX (para busqueda por prefijo de codigo)
- `public.cie10_catalog.is_dental` — INDEX (filtro base)

**Schema para public.cie10_catalog:**
```sql
CREATE TABLE public.cie10_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(10) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    category VARCHAR(200),
    is_dental BOOLEAN NOT NULL DEFAULT false,
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('spanish', code || ' ' || description)
    ) STORED,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX cie10_search_vector_idx ON public.cie10_catalog USING GIN(search_vector);
CREATE INDEX cie10_code_idx ON public.cie10_catalog(code);
CREATE INDEX cie10_is_dental_idx ON public.cie10_catalog(is_dental) WHERE is_dental = true;
```

**N+1 prevention:** No aplica (query unica contra catalogo publico).

### Pagination

**Pagination:** No (maximo 20 resultados por diseno — typeahead)

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| q | Strip whitespace, remover caracteres especiales peligrosos, maxlen 100 | Prevenir SQL injection (aunque usa queries parametrizadas) |
| limit | Pydantic int, rango 1-20 | Prevenir DoS por limit enorme |

### SQL Injection Prevention

**All queries use:** Queries con parametros named via `text()` de SQLAlchemy. **Justificacion de SQL raw:** Las funciones de full-text search de PostgreSQL (`ts_rank`, `plainto_tsquery`, `@@`) requieren SQL raw ya que SQLAlchemy ORM no las expone directamente de forma segura para queries complejas. Todos los parametros de usuario son parametros named, nunca concatenados.

### XSS Prevention

**Output encoding:** Todos los strings de salida escapados via serializacion Pydantic.

### CSRF Protection

**Strategy:** JWT-based (stateless) — CSRF no aplica para API.

### Data Privacy (PHI)

**PHI fields in this endpoint:** Ninguno — catalogo publico de codigos de clasificacion de enfermedades.

**Audit requirement:** No requerido — sin PHI.

---

## Testing

### Test Cases

#### Happy Path
1. Busqueda por descripcion parcial
   - **Given:** Catalogo cargado con codigos dentales, usuario autenticado
   - **When:** GET /api/v1/catalog/cie10?q=caries
   - **Then:** 200 OK, resultados ordenados por relevancia, todos con is_dental=true

2. Busqueda por codigo
   - **Given:** Catalogo cargado, usuario autenticado
   - **When:** GET /api/v1/catalog/cie10?q=K02
   - **Then:** 200 OK, K02.x como primeros resultados, codigos exactos primero

3. Cache hit
   - **Given:** Redis con resultado cacheado para q=caries
   - **When:** Segunda solicitud con q=caries
   - **Then:** 200 OK, `cached: true`, respuesta < 50ms

4. Busqueda multipalabra
   - **Given:** Catalogo cargado
   - **When:** GET ?q=caries dental
   - **Then:** 200 OK, resultados que contienen ambas palabras (full-text AND)

#### Edge Cases
1. q con 2 caracteres exactos
   - **Given:** Usuario autenticado
   - **When:** GET ?q=ca
   - **Then:** 200 OK, resultados que coincidan

2. Sin resultados para el query
   - **Given:** q que no coincide con ningun codigo dental
   - **When:** GET ?q=zzz
   - **Then:** 200 OK, `data: []`, `total: 0`

3. q con caracteres especiales
   - **Given:** Usuario autenticado
   - **When:** GET ?q=caries/dental
   - **Then:** 200 OK, caracteres especiales sanitizados, busqueda funcional

#### Error Cases
1. q de 1 caracter
   - **Given:** Usuario autenticado
   - **When:** GET ?q=k
   - **Then:** 400 con mensaje de minimo 2 caracteres

2. q faltante
   - **Given:** Usuario autenticado
   - **When:** GET sin parametro q
   - **Then:** 400 con campo q requerido

3. Token invalido
   - **Given:** Token expirado
   - **When:** GET sin Authorization valido
   - **Then:** 401 Unauthorized

4. limit=0 o limit=21
   - **Given:** Usuario autenticado
   - **When:** GET ?q=caries&limit=0 o limit=21
   - **Then:** 400 con limite invalido

### Test Data Requirements

**Users:** Cualquier usuario autenticado (doctor, assistant, etc.)

**Catalog:** Tabla `public.cie10_catalog` cargada con al menos 50 codigos dentales del rango K00-K14 en el entorno de test

### Mocking Strategy

- **Redis:** fakeredis para simular cache hit/miss
- **PostgreSQL full-text:** No mockear — usar DB de test con GIN index configurado

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] Busqueda por descripcion en espanol retorna resultados relevantes ordenados por ts_rank
- [ ] Busqueda por prefijo de codigo (K02, K02.1) retorna matches de codigo primero
- [ ] Resultados cacheados en Redis 1 hora con `cached: true` en segunda solicitud
- [ ] Cache compartido entre todos los tenants (sin tenant_id en cache key)
- [ ] Minimo 2 caracteres en `q` — 400 si menor
- [ ] Maximo 20 resultados por solicitud
- [ ] Respuesta < 100ms en cache miss, < 50ms en cache hit
- [ ] Sin audit log (no PHI)
- [ ] GIN index configurado en `public.cie10_catalog.search_vector`
- [ ] All test cases pass
- [ ] Performance targets met (< 100ms)
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Creacion o edicion del catalogo CIE-10 (solo via admin/superadmin)
- Busqueda de codigos CUPS (ver CR-11)
- Catalogo completo de CIE-10 (todos los rangos de enfermedades) — solo subconjunto dental
- CIE-11 (nueva version de la clasificacion) — post-MVP
- Validacion de codigos CIE-10 en el contexto de un diagnostico (ver CR-07)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined (Pydantic schemas)
- [x] All outputs defined (response models con cached flag)
- [x] API contract defined (OpenAPI compatible)
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit (authenticated, no tenant context)
- [x] Side effects listed (cache SET)
- [x] Examples provided (busqueda por descripcion y por codigo)

### Hook 2: Architecture Compliance
- [x] Follows service boundaries (catalogo publico separado de datos de tenant)
- [x] Uses public schema isolation (no tenant schema)
- [x] Matches FastAPI conventions (async, dependency injection)
- [x] Database models (public schema con GIN index definido)

### Hook 3: Security & Privacy
- [x] Auth level stated (authenticated, any role)
- [x] Input sanitization defined (Pydantic + strip)
- [x] SQL injection prevented (parametros named en SQL raw justificado)
- [x] No PHI en catalogo publico
- [x] Sin audit log requerido (no PHI)

### Hook 4: Performance & Scalability
- [x] Response time target definido (< 100ms, < 50ms cached)
- [x] Caching strategy stated (Redis 1h, compartido entre tenants)
- [x] DB queries optimized (GIN index, partial index is_dental)
- [x] Pagination: maximo 20 (typeahead, sin paginacion)

### Hook 5: Observability
- [x] Structured logging (JSON, user_id incluido)
- [x] Sin audit log (no PHI)
- [x] Error tracking (Sentry-compatible)
- [x] Cache hit ratio monitoreable via Redis MONITOR

### Hook 6: Testability
- [x] Test cases enumerated (happy + edge + error)
- [x] Test data requirements specified (cie10_catalog con datos)
- [x] Mocking strategy (fakeredis para cache)
- [x] Acceptance criteria stated

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
