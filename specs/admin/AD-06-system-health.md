# AD-06 — Admin System Health Dashboard Spec

## Overview

**Feature:** System health dashboard for superadmins. Returns real-time and near-real-time health metrics for all platform infrastructure components: PostgreSQL (connection pools, replication lag), Redis (memory, hit rate, clients), RabbitMQ (queue depths, consumer counts, message rates), application (uptime, request rate, error rate, p95 latency), and storage (total usage, top-10 tenants by storage). Designed to give the ops team an instant platform health snapshot.

**Domain:** admin

**Priority:** Critical (Sprint 1-2 — needed from day one for platform operations)

**Dependencies:** AD-01 (superadmin-login), infra/db-architecture.md, infra/caching.md, infra/bg-processing.md

---

## Authentication

- **Level:** Privileged
- **Roles allowed:** superadmin
- **Tenant context:** Not required — platform infrastructure metrics
- **Special rules:** Requires admin JWT (RS256). Response includes sensitive infrastructure details (connection counts, queue depths) — never expose to tenant-level users.

---

## Endpoint

```
GET /api/v1/admin/health
```

**Rate Limiting:**
- 120 requests per minute per admin session (health checks can be frequent for dashboards)
- Most data is fresh (TTL 10–30s) — polling every 10s is acceptable

---

## Request

### Headers

| Header | Required | Type | Description | Example |
|--------|----------|------|-------------|---------|
| Authorization | Yes | string | Bearer admin JWT | Bearer eyJhbGc... |

### Query Parameters

| Parameter | Required | Type | Constraints | Description | Example |
|-----------|----------|------|-------------|-------------|---------|
| components | No | string | Comma-separated: database, redis, rabbitmq, application, storage | Only return specific components | database,redis |
| include_slow_queries | No | boolean | default=false | Include list of top 10 slowest DB queries in the last 1 hour | false |
| include_error_details | No | boolean | default=false | Include breakdown of error types | false |

---

## Response

### Success Response

**Status:** 200 OK

**Schema:**
```json
{
  "collected_at": "string (ISO 8601) — when metrics were collected",
  "overall_status": "string — healthy | degraded | critical",
  "overall_status_color": "string — green | yellow | red",
  "components_checked": "array[string]",

  "database": {
    "status": "string — healthy | degraded | critical | unavailable",
    "primary": {
      "host": "string — hostname (last 4 chars only for security, e.g. db-01)",
      "connection_pool_size": "integer — configured pool size",
      "connection_pool_used": "integer — currently checked-out connections",
      "connection_pool_utilization_pct": "number",
      "active_connections": "integer — total active connections in pg_stat_activity",
      "idle_connections": "integer",
      "waiting_queries": "integer — queries waiting for a lock",
      "longest_query_duration_ms": "number | null — longest running query (if > 1s)",
      "database_size_gb": "number — total size of the platform DB",
      "transaction_rate_per_sec": "number",
      "cache_hit_rate_pct": "number — PostgreSQL buffer cache hit rate"
    },
    "replica": {
      "status": "string — in_sync | lagging | unavailable",
      "replication_lag_bytes": "integer",
      "replication_lag_seconds": "number",
      "is_lag_critical": "boolean — lag > 60s"
    },
    "tenant_schemas": {
      "total_schemas": "integer",
      "total_size_gb": "number",
      "largest_schemas_top5": [
        { "tenant_id": "string", "clinic_name": "string", "size_gb": "number" }
      ]
    },
    "slow_queries": "array[SlowQuery] | null — only if include_slow_queries=true"
  },

  "redis": {
    "status": "string — healthy | degraded | unavailable",
    "host": "string",
    "version": "string",
    "memory_used_mb": "number",
    "memory_limit_mb": "number",
    "memory_utilization_pct": "number",
    "hit_rate_pct": "number — keyspace hit / (hit + miss) * 100",
    "connected_clients": "integer",
    "blocked_clients": "integer — clients in BLPOP etc.",
    "total_commands_per_sec": "number",
    "evicted_keys": "integer — keys evicted due to memory pressure (should be 0)",
    "expired_keys_per_sec": "number",
    "keyspace": {
      "total_keys": "integer",
      "by_prefix_top5": [
        { "prefix": "string — e.g. tenant:", "key_count": "integer", "memory_pct": "number" }
      ]
    },
    "persistence": {
      "last_save_at": "string (ISO 8601)",
      "rdb_enabled": "boolean",
      "aof_enabled": "boolean"
    }
  },

  "rabbitmq": {
    "status": "string — healthy | degraded | unavailable",
    "host": "string",
    "version": "string",
    "queues": [
      {
        "name": "string — queue name",
        "messages_ready": "integer — unprocessed messages",
        "messages_unacknowledged": "integer — in-flight messages",
        "messages_total": "integer",
        "consumer_count": "integer",
        "message_rate_per_sec": "number — publish rate",
        "ack_rate_per_sec": "number",
        "is_paused": "boolean",
        "is_idle": "boolean",
        "status": "string — healthy | backed_up | no_consumers | critical"
      }
    ],
    "overall_message_rate_per_sec": "number",
    "total_consumers": "integer",
    "total_queued_messages": "integer",
    "nodes": [
      {
        "name": "string — node name",
        "is_running": "boolean",
        "memory_mb": "number",
        "fd_used": "integer",
        "fd_total": "integer"
      }
    ]
  },

  "application": {
    "status": "string — healthy | degraded | critical",
    "instances": [
      {
        "instance_id": "string",
        "uptime_seconds": "integer",
        "uptime_display": "string — e.g. 3d 4h 12m",
        "version": "string — git SHA or semver",
        "python_version": "string",
        "requests_per_sec": "number",
        "active_requests": "integer",
        "error_rate_pct": "number — 5xx errors / total requests * 100",
        "p50_latency_ms": "number",
        "p95_latency_ms": "number",
        "p99_latency_ms": "number",
        "memory_mb": "number",
        "cpu_pct": "number"
      }
    ],
    "aggregated": {
      "total_requests_1h": "integer",
      "total_errors_1h": "integer",
      "error_rate_pct_1h": "number",
      "p95_latency_ms_1h": "number",
      "avg_requests_per_sec": "number"
    },
    "error_breakdown": "object | null — only if include_error_details=true"
  },

  "storage": {
    "status": "string — healthy | warning | critical",
    "provider": "string — hetzner_s3 | local",
    "total_used_gb": "number",
    "total_limit_gb": "number",
    "utilization_pct": "number",
    "by_category": {
      "clinical_images_gb": "number",
      "rips_files_gb": "number",
      "einvoice_xml_gb": "number",
      "signatures_gb": "number",
      "other_gb": "number"
    },
    "top_10_tenants_by_storage": [
      {
        "tenant_id": "string",
        "clinic_name": "string",
        "storage_used_gb": "number",
        "storage_limit_gb": "number",
        "utilization_pct": "number"
      }
    ],
    "growth_rate_gb_per_day": "number — 7-day rolling average"
  }
}
```

**SlowQuery schema (when include_slow_queries=true):**
```json
{
  "query_hash": "string — MD5 of normalized query",
  "calls": "integer",
  "avg_duration_ms": "number",
  "max_duration_ms": "number",
  "query_preview": "string — first 200 chars, PHI-safe (no actual data values)"
}
```

**error_breakdown schema (when include_error_details=true):**
```json
{
  "by_status_code": { "500": "integer", "502": "integer", "503": "integer" },
  "by_endpoint_top5": [
    { "endpoint": "string", "error_count": "integer", "error_rate_pct": "number" }
  ],
  "by_error_type_top5": [
    { "error_type": "string", "count": "integer" }
  ]
}
```

**Overall Status Logic:**

| Condition | overall_status |
|-----------|---------------|
| All components healthy | healthy |
| Any component degraded (but none critical) | degraded |
| Any component critical or unavailable | critical |

**Queue Status Logic:**

| Condition | queue status |
|-----------|-------------|
| messages_ready < 100 and consumer_count > 0 | healthy |
| messages_ready >= 100 and < 500 | backed_up |
| consumer_count = 0 | no_consumers |
| messages_ready >= 500 | critical |

**Example Response (abbreviated):**
```json
{
  "collected_at": "2026-02-25T10:00:00Z",
  "overall_status": "healthy",
  "overall_status_color": "green",
  "components_checked": ["database", "redis", "rabbitmq", "application", "storage"],
  "database": {
    "status": "healthy",
    "primary": {
      "host": "db-01",
      "connection_pool_size": 20,
      "connection_pool_used": 4,
      "connection_pool_utilization_pct": 20.0,
      "active_connections": 12,
      "idle_connections": 8,
      "waiting_queries": 0,
      "longest_query_duration_ms": null,
      "database_size_gb": 4.7,
      "transaction_rate_per_sec": 42.3,
      "cache_hit_rate_pct": 99.2
    },
    "replica": {
      "status": "in_sync",
      "replication_lag_bytes": 512,
      "replication_lag_seconds": 0.01,
      "is_lag_critical": false
    },
    "tenant_schemas": {
      "total_schemas": 247,
      "total_size_gb": 3.2,
      "largest_schemas_top5": [
        { "tenant_id": "tn_xyz", "clinic_name": "Centro Dental Elite", "size_gb": 0.42 }
      ]
    },
    "slow_queries": null
  },
  "redis": {
    "status": "healthy",
    "host": "redis-01",
    "version": "7.2.4",
    "memory_used_mb": 512,
    "memory_limit_mb": 2048,
    "memory_utilization_pct": 25.0,
    "hit_rate_pct": 97.8,
    "connected_clients": 24,
    "blocked_clients": 0,
    "total_commands_per_sec": 1240,
    "evicted_keys": 0,
    "expired_keys_per_sec": 18.4
  },
  "rabbitmq": {
    "status": "healthy",
    "host": "rabbitmq-01",
    "version": "3.13.1",
    "queues": [
      { "name": "rips.generation", "messages_ready": 0, "messages_unacknowledged": 1, "messages_total": 1, "consumer_count": 2, "message_rate_per_sec": 0.02, "ack_rate_per_sec": 0.02, "is_paused": false, "is_idle": false, "status": "healthy" },
      { "name": "notifications.email", "messages_ready": 3, "messages_unacknowledged": 2, "messages_total": 5, "consumer_count": 3, "message_rate_per_sec": 0.5, "ack_rate_per_sec": 0.5, "is_paused": false, "is_idle": false, "status": "healthy" }
    ],
    "overall_message_rate_per_sec": 12.4,
    "total_consumers": 18,
    "total_queued_messages": 7
  }
}
```

### Error Responses

#### 400 Bad Request
**When:** `components` contains an unrecognized component name.

#### 401 Unauthorized
**When:** Admin JWT missing or invalid.

#### 403 Forbidden
**When:** Role is not superadmin.

#### 422 Unprocessable Entity
**When:** Query parameter types invalid.

#### 503 Service Unavailable
**When:** Cannot reach one or more monitoring backends (returns partial data with the unavailable component marked status=unavailable).

---

## Business Logic

**Step-by-step process:**

1. Validate admin JWT and superadmin role.
2. Parse `components` filter; default to all 5 if not specified.
3. For each requested component, collect metrics:

   **Database:**
   - Query `pg_stat_activity` for active/idle/waiting connections.
   - Query `pg_stat_bgwriter` for cache hit rate.
   - Query `pg_database_size('dentalos')` for total size.
   - Query connection pool state from SQLAlchemy's `pool.status()`.
   - Query replica lag via `pg_stat_replication` on primary.
   - If `include_slow_queries=true`: query `pg_stat_statements` (normalized query stats).

   **Redis:**
   - Execute `INFO all` command; parse memory, keyspace, stats sections.
   - Compute `hit_rate_pct = keyspace_hits / (keyspace_hits + keyspace_misses) * 100`.
   - Sample top key prefixes: use Redis SCAN with COUNT to sample key distribution.

   **RabbitMQ:**
   - Query RABBITMQ Management API: `GET /api/queues` for queue stats.
   - Query `/api/nodes` for node health.
   - Map to internal queue status using the queue status logic rules.

   **Application:**
   - Each FastAPI instance exposes an internal metrics endpoint (Prometheus-compatible).
   - Collect from all instances via internal service discovery.
   - Aggregate P50/P95/P99 latencies, error rates, request rates.
   - If `include_error_details=true`: query Sentry or internal error aggregates.

   **Storage:**
   - Query object storage provider API for bucket total size.
   - Query `tenant_storage_manifest` table for per-tenant and per-category breakdown.
   - Query top-10 tenants by storage.

4. Compute `overall_status` from component statuses.
5. Return 200.

**Note:** Health data is collected on-demand (this is a pull endpoint). There is no long-lived collection background job for this specific endpoint — each request triggers fresh metric pulls. For high-frequency dashboards, cache can be added at the client side.

**Validation Rules:**

| Field | Rule | Error Message |
|-------|------|---------------|
| components | Comma-separated subset of: database, redis, rabbitmq, application, storage | "Unknown component" |
| include_slow_queries | Boolean | Must be boolean |
| include_error_details | Boolean | Must be boolean |

**Business Rules:**

- Slow queries in response have parameter values stripped (only query structure shown) to avoid PHI leakage.
- Storage top-10 shows clinic names for context; no patient PHI.
- Database host names are truncated in response for security (show only alias, not full hostname/IP).
- If a component is unreachable (e.g., RabbitMQ management API down), that component's status is `unavailable` and remaining components are still returned with available data.
- `replication_lag_seconds > 60` sets `is_lag_critical=true` and contributes to `overall_status=degraded`.
- `evicted_keys > 0` in Redis signals memory pressure and sets Redis status to `degraded`.

**Edge Cases:**

| Scenario | Expected Behavior |
|----------|-------------------|
| RabbitMQ management API unreachable | rabbitmq.status=unavailable; overall_status=degraded; other components returned |
| All DB connections in use | connection_pool_utilization_pct=100; database.status=degraded |
| Redis memory > 80% | redis.status=degraded; overall_status=degraded |
| Queue has no consumers | queue.status=no_consumers; if messages_ready > 0, that's critical |
| Single-node setup (no replica) | database.replica=null (field omitted) |
| Storage > 80% full | storage.status=warning; > 90%: critical |

---

## Side Effects

### Database Changes

Read-only (queries `pg_stat_*` views and storage manifest). No writes.

### Cache Operations

**Cache keys affected:** None (health data is real-time; intentionally not cached to reflect true state)

**Note:** If called very frequently (e.g., dashboard polling every second), a light 10-second cache can be added at the implementation level without changing the spec contract.

### Queue Jobs (RabbitMQ)

**Jobs dispatched:** None — read-only.

### Audit Log

**Audit entry:** Yes (at DEBUG level — health checks are frequent and low-risk)

- **Action:** read
- **Resource:** system_health
- **PHI involved:** No

---

## Performance

### Expected Response Time
- **Target:** < 800ms (all components, fresh)
- **Maximum acceptable:** < 2,000ms
- **With components filter:** < 400ms for single component

### Caching Strategy
- **Strategy:** No server-side cache (health data must reflect current state)
- **Client-side:** Dashboard client should poll every 10–30s; not every request

### Database Performance

**Queries executed:** ~6 (pg_stat_activity, pg_database_size, pg_stat_replication, pg_stat_bgwriter, pg_stat_statements if enabled, tenant schema sizes)

**Indexes required:** None (reads from PostgreSQL system views)

**External API calls:** Redis INFO (< 5ms), RabbitMQ API (< 50ms), storage API (< 200ms), app metrics (< 100ms)

**Total:** Queries + external calls run in parallel; total < 800ms target.

---

## Security

### Input Sanitization

| Input | Sanitization | Notes |
|-------|-------------|-------|
| components | Pydantic: split by comma, each validated against known component list | Prevents unknown component injection |
| include_slow_queries | Boolean | |
| include_error_details | Boolean | |

### SQL Injection Prevention

**All queries use:** SQLAlchemy with parameterized queries. pg_stat_* queries are read-only system views.

### Data Privacy (PHI)

**PHI fields in this endpoint:** None. Query previews in slow_queries are stripped of parameter values (e.g., `SELECT * FROM patients WHERE id = $1` not `WHERE id = 'actual-uuid'`).

---

## Testing

### Test Cases

#### Happy Path
1. Full health check (all components healthy)
   - **Given:** superadmin JWT, all services running normally
   - **When:** GET /api/v1/admin/health
   - **Then:** 200 OK, overall_status=healthy, all 5 components healthy

2. Partial component check
   - **Given:** superadmin JWT
   - **When:** GET ?components=database,redis
   - **Then:** 200 OK, components_checked=["database","redis"], rabbitmq/application/storage absent

3. Include slow queries
   - **Given:** Some slow queries in pg_stat_statements
   - **When:** GET ?include_slow_queries=true
   - **Then:** 200 OK, database.slow_queries populated with top 10

#### Edge Cases
1. RabbitMQ unreachable
   - **Given:** RabbitMQ management API returns 503
   - **When:** GET health
   - **Then:** 200 OK (not 503), rabbitmq.status=unavailable, overall_status=degraded

2. Redis memory > 80%
   - **Given:** Redis memory_utilization_pct=85
   - **When:** GET health
   - **Then:** 200 OK, redis.status=degraded, overall_status=degraded

3. Queue backed up (500+ messages)
   - **Given:** rips.generation queue has 600 ready messages
   - **When:** GET health
   - **Then:** 200 OK, that queue's status=critical, rabbitmq.status=critical, overall_status=critical

#### Error Cases
1. Unknown component in filter
   - **Given:** superadmin JWT
   - **When:** GET ?components=database,kafka
   - **Then:** 400 Bad Request

2. Tenant JWT used
   - **Given:** Regular clinic_owner JWT
   - **When:** GET /api/v1/admin/health
   - **Then:** 401 Unauthorized

### Test Data Requirements

**Users:** 1 superadmin

**Patients/Entities:** Mocked infrastructure state fixtures (each component in healthy/degraded/unavailable state)

### Mocking Strategy

- PostgreSQL pg_stat views: Mock with known fixture data
- Redis INFO: Mock with configurable memory/hit-rate values
- RabbitMQ management API: Mock HTTP server with queue fixtures
- Application metrics: Mock per-instance metrics endpoint
- Storage API: Mock with known tenant storage fixtures

---

## Acceptance Criteria

**This feature is complete when:**

- [ ] GET returns all 5 component health sections
- [ ] overall_status correctly computed from component statuses
- [ ] database section: connection pool, replication lag, slow queries optional
- [ ] redis section: memory, hit rate, evicted keys
- [ ] rabbitmq section: per-queue depths, consumer counts, rates
- [ ] application section: latency percentiles, error rate, per-instance breakdown
- [ ] storage section: total usage, top-10 tenants
- [ ] Partial component filter works (components=database,redis)
- [ ] Degraded/critical states correctly detected per rules
- [ ] RabbitMQ unreachable returns 200 with unavailable status (not 500)
- [ ] No PHI in slow query previews
- [ ] All test cases pass
- [ ] Performance target: < 800ms
- [ ] Quality Hooks passed

---

## Out of Scope

**This spec explicitly does NOT cover:**

- Real-time streaming health (WebSocket) — future enhancement
- Historical health trend data (separate monitoring integration)
- Alert configuration (PagerDuty/OpsGenie integration — Hetzner monitoring)
- Per-tenant health metrics (see AD-02 tenant management for tenant-level data)
- Email/Slack alerting on critical state (Hetzner monitoring handles this externally)

---

## Quality Hooks Checklist

### Hook 1: Spec Completeness
- [x] All inputs defined
- [x] All outputs defined (all 5 component schemas)
- [x] API contract defined
- [x] Validation rules stated
- [x] Error cases enumerated
- [x] Auth requirements explicit
- [x] Side effects listed
- [x] Examples provided

### Hook 2: Architecture Compliance
- [x] Follows service boundaries
- [x] Matches FastAPI conventions
- [x] Infrastructure components documented

### Hook 3: Security & Privacy
- [x] Auth level stated (superadmin only)
- [x] PHI-safe slow query previews
- [x] Host names truncated
- [x] Audit trail

### Hook 4: Performance & Scalability
- [x] Parallel component collection
- [x] < 800ms target
- [x] No caching (intentional)

### Hook 5: Observability
- [x] Structured logging
- [x] Overall status flag
- [x] Component-level status details

### Hook 6: Testability
- [x] Test cases for each component state
- [x] Mocking strategy for each infrastructure service
- [x] Acceptance criteria

**Overall Status:** PASS

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
