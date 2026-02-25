# Caching Strategy Spec

> **Spec ID:** I-05 | **Status:** Draft | **Last Updated:** 2026-02-24

---

## 1. Overview

Redis serves as the caching layer for DentalOS, a multi-tenant dental SaaS targeting LATAM clinics. Every cache key is namespaced per tenant to guarantee data isolation, mirroring schema-per-tenant PostgreSQL isolation (see `infra/multi-tenancy.md`). Redis is a **performance enhancement**, not a hard dependency. If Redis is down, the app falls through to PostgreSQL -- slower but fully functional.

**Stack:** Python 3.12 + FastAPI + `redis.asyncio` + Redis 7.x on Hetzner.

---

## 2. Key Naming Convention

**Pattern:** `dentalos:{tenant_id}:{domain}:{resource}:{id}`

| Segment | Description | Example |
|---------|-------------|---------|
| `dentalos` | Global prefix | `dentalos` |
| `{tenant_id}` | First 12 hex chars of tenant UUID | `a1b2c3d4e5f6` |
| `{domain}` | Functional domain | `auth`, `config`, `clinical`, `appointment` |
| `{resource}:{id}` | Entity and identifier | `odontogram:p1p2p3`, `slots:d1d2d3:2026-03-15` |

**Tenant-scoped examples:**
```
dentalos:a1b2c3d4e5f6:auth:session:u1u2u3u4u5u6
dentalos:a1b2c3d4e5f6:auth:refresh:jti_abc123
dentalos:a1b2c3d4e5f6:auth:permissions:u1u2u3u4u5u6
dentalos:a1b2c3d4e5f6:config:tenant_meta
dentalos:a1b2c3d4e5f6:config:plan_limits
dentalos:a1b2c3d4e5f6:clinical:odontogram:p1p2p3p4p5p6
dentalos:a1b2c3d4e5f6:clinical:patient_summary:p1p2p3p4p5p6
dentalos:a1b2c3d4e5f6:appointment:slots:d1d2d3d4d5d6:2026-03-15
dentalos:a1b2c3d4e5f6:appointment:today
```

**Shared keys (cross-tenant catalogs):** `dentalos:shared:catalog:{type}:{query}`
```
dentalos:shared:catalog:cie10:search:caries
dentalos:shared:catalog:cups:search:endodoncia
dentalos:shared:catalog:medications:search:amoxicilina
```

---

## 3. Cache Categories with TTL

### Session / Auth
| Key Pattern | TTL | Description |
|-------------|-----|-------------|
| `dentalos:{tid}:auth:session:{user_id}` | 15 min | User session data (role, permissions, tenant context) |
| `dentalos:{tid}:auth:refresh:{jti}` | 30 days | Refresh token metadata (device, IP, revocation flag) |
| `dentalos:{tid}:auth:permissions:{user_id}` | 5 min | Resolved RBAC permission set |

### Tenant Config
| Key Pattern | TTL | Description |
|-------------|-----|-------------|
| `dentalos:{tid}:config:tenant_meta` | 5 min | Name, country, timezone, schema_name, status |
| `dentalos:{tid}:config:plan_limits` | 10 min | max_patients, max_doctors, max_storage_mb |
| `dentalos:{tid}:config:settings` | 5 min | Odontogram mode, appointment duration, reminders |

### Clinical Data
| Key Pattern | TTL | Description |
|-------------|-----|-------------|
| `dentalos:{tid}:clinical:odontogram:{patient_id}` | 2 min | Odontogram state (frequently updated during consults) |
| `dentalos:{tid}:clinical:patient_summary:{patient_id}` | 5 min | Last visit, active treatments, next appointment |

### Appointment Data
| Key Pattern | TTL | Description |
|-------------|-----|-------------|
| `dentalos:{tid}:appointment:schedule:{doctor_id}` | 10 min | Doctor weekly schedule template |
| `dentalos:{tid}:appointment:slots:{doctor_id}:{date}` | 1 min | Available booking slots (short TTL for accuracy) |
| `dentalos:{tid}:appointment:today` | 2 min | Today's appointment count for dashboard |

### Catalog Data (Shared, `dentalos:shared:*`)
| Key Pattern | TTL | Description |
|-------------|-----|-------------|
| `dentalos:shared:catalog:cie10:search:{q}` | 24 h | CIE-10 diagnosis code search results |
| `dentalos:shared:catalog:cups:search:{q}` | 24 h | CUPS procedure code search results |
| `dentalos:shared:catalog:medications:search:{q}` | 24 h | Medication catalog search results |

### Rate Limiting
| Key Pattern | TTL | Description |
|-------------|-----|-------------|
| `dentalos:{tid}:ratelimit:user:{uid}:{window}` | 1 min | Sliding window counter (see `infra/rate-limiting.md`) |

---

## 4. Cache Invalidation Rules

| Event | Keys Invalidated | Trigger |
|-------|-----------------|---------|
| Patient created/updated/deleted | `...:patient_summary:{pid}` | POST/PUT/DELETE `/patients/{id}` |
| Odontogram condition changed | `...:odontogram:{pid}` | POST/PUT/DELETE `/odontogram/conditions` |
| Appointment booked/cancelled | `...:slots:{did}:{date}`, `...:today` | POST/DELETE `/appointments` |
| Doctor schedule changed | `...:schedule:{did}`, `...:slots:{did}:*` | PUT `/doctors/{id}/schedule` |
| Tenant settings updated | `...:config:settings` | PUT `/settings` |
| Plan upgraded/downgraded | `...:config:plan_limits`, `...:tenant_meta` | Plan change event |
| User role changed | `...:auth:permissions:{uid}` | PUT `/users/{id}/role` |
| Password changed | `...:auth:session:{uid}`, `...:auth:refresh:*` | POST `/auth/change-password` |
| Logout | `...:auth:refresh:{jti}` | POST `/auth/logout` |
| Catalog updated (superadmin) | `dentalos:shared:catalog:*` | Admin catalog import |

**FastAPI event handlers:**
```python
# app/events/cache_invalidation.py
from app.core.cache import cache_delete, cache_delete_pattern

async def on_patient_updated(tenant_id: str, patient_id: str) -> None:
    tid = tenant_id.replace("-", "")[:12]
    await cache_delete(f"dentalos:{tid}:clinical:patient_summary:{patient_id}")
    await cache_delete(f"dentalos:{tid}:clinical:odontogram:{patient_id}")

async def on_appointment_changed(tenant_id: str, doctor_id: str, date: str) -> None:
    tid = tenant_id.replace("-", "")[:12]
    await cache_delete(f"dentalos:{tid}:appointment:slots:{doctor_id}:{date}")
    await cache_delete(f"dentalos:{tid}:appointment:today")
```

---

## 5. Python Implementation

```python
# app/core/redis.py
import redis.asyncio as redis
from app.core.config import settings

pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL, max_connections=50, decode_responses=True,
    socket_timeout=5, socket_connect_timeout=5, retry_on_timeout=True,
)
redis_client = redis.Redis(connection_pool=pool)
```

```python
# app/core/cache.py
import json, logging
from typing import Any, Optional
logger = logging.getLogger("dentalos.cache")

async def get_cached(key: str) -> Optional[Any]:
    try:
        raw = await redis_client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        logger.warning("cache_get_failed", extra={"key_domain": key.split(":")[2]})
        return None

async def set_cached(key: str, value: Any, ttl_seconds: int) -> None:
    try:
        await redis_client.setex(key, ttl_seconds, json.dumps(value, default=str))
    except Exception:
        logger.warning("cache_set_failed", extra={"key_domain": key.split(":")[2]})

async def cache_delete(key: str) -> None:
    try: await redis_client.delete(key)
    except Exception: logger.warning("cache_delete_failed", extra={"key": key})

async def cache_delete_pattern(pattern: str) -> None:
    """Delete keys matching glob pattern. Uses SCAN, never KEYS."""
    try:
        cursor = 0
        while True:
            cursor, keys = await redis_client.scan(cursor=cursor, match=pattern, count=100)
            if keys: await redis_client.delete(*keys)
            if cursor == 0: break
    except Exception:
        logger.warning("cache_pattern_delete_failed", extra={"pattern": pattern})
```

---

## 6. Cache-Aside Pattern

```python
# app/core/cache_aside.py
async def cache_aside(key: str, ttl_seconds: int, fetch_fn) -> Any:
    """Read cache -> miss -> fetch from DB -> populate cache."""
    cached = await get_cached(key)
    if cached is not None:
        return cached
    value = await fetch_fn()
    if value is not None:
        await set_cached(key, value, ttl_seconds)
    return value

# Usage in FastAPI route:
@router.get("/patients/{patient_id}/summary")
async def get_patient_summary(patient_id: str, request: Request):
    tid = request.state.tenant_id_short
    return await cache_aside(
        key=f"dentalos:{tid}:clinical:patient_summary:{patient_id}",
        ttl_seconds=300,
        fetch_fn=lambda: patient_service.get_summary(patient_id),
    )
```

---

## 7. Shared vs Tenant-Scoped Keys

| Scope | Prefix | Use Cases |
|-------|--------|-----------|
| **Tenant** | `dentalos:{tenant_id}:*` | Sessions, config, clinical, appointments, rate limits |
| **Shared** | `dentalos:shared:*` | CIE-10, CUPS, medications, odontogram condition catalog |

Shared keys are populated at startup and refreshed every 24h. Tenant keys are populated lazily on first access.

---

## 8. Memory Budget

| Category | Keys/Tenant | Avg Size | Subtotal |
|----------|-------------|----------|----------|
| Auth/Session | ~20 | 0.5 KB | 10 KB |
| Config | 3 | 2 KB | 6 KB |
| Clinical | ~100 | 3 KB | 300 KB |
| Appointments | ~30 | 2 KB | 60 KB |
| Rate limiting | ~20 | 0.1 KB | 2 KB |
| **Per tenant** | | | **~380 KB** |

**Projections:** 100 tenants = ~39 MB | 500 tenants = ~191 MB | 2,000 tenants = ~761 MB (shared catalogs add ~1 MB).

**Redis config:** `maxmemory 512mb`, `maxmemory-policy allkeys-lru`. Cold tenants are evicted first.

**Alerts:** Memory > 70% (warn), > 85% (critical). Hit rate < 80% (warn). Evictions > 0 sustained (warn). Latency p99 > 5ms (warn).

---

## 9. Failure Handling

| Component | Behavior When Redis Is Down |
|-----------|---------------------------|
| Cache reads | Return None. Proceed to PostgreSQL. Slower but functional. |
| Cache writes | Silently dropped. Warning logged. |
| Session validation | Falls back to database lookup. |
| Rate limiting | Temporarily disabled. Warning logged. Requests not blocked. |
| Catalog lookups | Query PostgreSQL catalog tables directly. |

All cache operations wrapped in try/except. Redis failure never causes a 500 error.

---

## 10. Testing

```python
# tests/conftest.py
import fakeredis.aioredis, pytest

@pytest.fixture
async def mock_redis():
    server = fakeredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()

# tests/test_cache.py
async def test_cache_aside_populates_on_miss(mock_redis):
    fetch_called = False
    async def fetch_fn():
        nonlocal fetch_called; fetch_called = True
        return {"name": "Patient A"}
    result = await cache_aside("dentalos:abc:clinical:patient_summary:123", 300, fetch_fn)
    assert result == {"name": "Patient A"} and fetch_called
    fetch_called = False
    result = await cache_aside("dentalos:abc:clinical:patient_summary:123", 300, fetch_fn)
    assert result == {"name": "Patient A"} and not fetch_called

async def test_cache_delete_pattern(mock_redis):
    await mock_redis.setex("dentalos:abc:appointment:slots:d1:2026-03-15", 60, "x")
    await mock_redis.setex("dentalos:abc:appointment:slots:d1:2026-03-16", 60, "y")
    await mock_redis.setex("dentalos:abc:config:settings", 300, "z")
    await cache_delete_pattern("dentalos:abc:appointment:slots:d1:*")
    assert await mock_redis.get("dentalos:abc:appointment:slots:d1:2026-03-15") is None
    assert await mock_redis.get("dentalos:abc:config:settings") == "z"
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
| 2.0 | 2026-02-24 | Full rewrite: `dentalos:` key prefix, TTL per category, invalidation rules, cache-aside, memory budget, failure handling, pytest with fakeredis |
