# Incident Response Runbook — DentalOS

**Version:** 1.0
**Last Updated:** 2026-02-27
**Audience:** On-call engineers, team leads, SREs

---

## Table of Contents

1. [Severity Definitions](#1-severity-definitions)
2. [On-Call Escalation Flow](#2-on-call-escalation-flow)
3. [Common Failure Scenarios](#3-common-failure-scenarios)
4. [Diagnostic Commands Reference](#4-diagnostic-commands-reference)
5. [Recovery Procedures](#5-recovery-procedures)
6. [Post-Incident Review Template](#6-post-incident-review-template)

---

## 1. Severity Definitions

| Level | Name | Description | Max Response Time | Auto-Page? |
|-------|------|-------------|-------------------|------------|
| **P1** | CRITICAL | Complete service outage or data loss risk | **15 minutes** | Yes |
| **P2** | HIGH | Major feature degraded, >50% users affected | **30 minutes** | Yes |
| **P3** | MEDIUM | Minor feature degraded, <10% users affected | **2 hours** | No (Slack alert) |
| **P4** | LOW | Cosmetic, informational, no user impact | **Next business day** | No |

### P1 — CRITICAL

Immediate all-hands response required. Wake up the team.

**Examples:**
- Database (PostgreSQL) is down or unreachable
- Authentication is broken — users cannot log in
- Confirmed or suspected data breach / PHI exposure
- Tenant isolation failure — data cross-contamination risk
- Complete API outage (health check returning 5xx)
- SSL/TLS certificate expired (all HTTPS requests failing)

**Immediate actions:**
- Page on-call engineer AND team lead simultaneously
- Open a dedicated incident Slack channel: `#incident-YYYY-MM-DD-p1`
- Begin incident timeline log immediately
- Notify clinic owners if downtime exceeds 10 minutes

### P2 — HIGH

Urgent response during business hours. Page on-call outside hours.

**Examples:**
- Billing module down (invoicing, DIAN integration broken)
- Redis down and DB fallthrough is overloaded
- Error rate exceeds 5% across any endpoint group
- RabbitMQ unreachable — notifications and PDF generation stalled
- Odontogram saves failing for multiple tenants
- Queue backlog > 500 messages and growing

**Immediate actions:**
- Page on-call engineer
- Open Slack thread in `#incidents`
- Assess blast radius (which tenants affected, which features)

### P3 — MEDIUM

Respond within 2 hours. No need to wake anyone up.

**Examples:**
- RabbitMQ backlog growing but workers processing (just slow)
- Slow queries degrading one specific feature for <10% of users
- Single tenant reporting issues not reproducible elsewhere
- Non-critical background job failures (analytics aggregation, archive)
- Memory pressure on one service instance but not all

**Immediate actions:**
- Post in `#incidents` Slack with context
- Assign to next available engineer on shift
- Monitor to ensure it does not escalate to P2

### P4 — LOW

Log it. Fix it in the next sprint or during the next business day.

**Examples:**
- UI cosmetic bug (wrong color, misaligned element)
- Non-critical log noise or spurious warnings
- Deprecated API usage warnings
- Minor documentation discrepancy

---

## 2. On-Call Escalation Flow

```
[Alert Fires]
  Grafana (infra metrics) or Sentry (application errors)
        |
        v
[On-Call Engineer Paged]
  Must acknowledge within 15 minutes
  If no acknowledgment → auto-escalate to team lead
        |
        v
[Acknowledge + Classify Severity]
  Open #incident channel if P1/P2
  Start incident timeline document
        |
        v
[Investigate + Mitigate]
  Use diagnostic commands in Section 4
  Apply recovery procedures from Section 5
  ETA: resolved within 30 min for P1, 60 min for P2
        |
        v
[Not Resolved in 30 min?]
  Escalate to Team Lead immediately
  Team Lead joins investigation
  Consider rollback if recent deploy is suspected
        |
        v
[Incident Resolved]
  Confirm all systems green
  Notify affected tenants if applicable
  Post resolution summary in Slack
        |
        v
[Post-Incident Review]
  Schedule within 48 hours of resolution
  Use template in Section 6
  Document action items with owners and deadlines
```

### Escalation Contacts

| Role | When to Contact | Channel |
|------|----------------|---------|
| On-Call Engineer | First responder for all alerts | PagerDuty / Phone |
| Team Lead | P1 immediately, P2 if not resolved in 30 min | Phone / Slack |
| CTO | Confirmed data breach, prolonged P1 (>1h) | Phone |
| Legal/Compliance | PHI breach, regulatory incident | Phone + Email |

### Incident Communication Template (Slack)

```
**INCIDENT [P1/P2] — [Short Description]**
Started: HH:MM UTC
Affected: [Which tenants/features/endpoints]
Status: Investigating / Mitigating / Resolved
On-call: @engineer
Update ETA: HH:MM UTC
```

---

## 3. Common Failure Scenarios

---

### 3.1 PostgreSQL Down or Unreachable

**Symptoms:**
- Health endpoint returns 503
- All API requests return 500 with `connection refused` or `timeout` errors
- Grafana: `pg_up` metric = 0

**Diagnosis:**

```bash
# Check if container is running
docker compose ps postgres

# Check recent logs
docker compose logs --tail=100 postgres

# Try connecting manually
docker compose exec postgres psql -U dentalos -c "SELECT 1;"

# Check connection pool stats (if Pgbouncer is in use)
docker compose exec postgres psql -U pgbouncer pgbouncer -c "SHOW POOLS;"

# Check for lock contention
docker compose exec postgres psql -U dentalos -c "
SELECT pid, wait_event_type, wait_event, state, query
FROM pg_stat_activity
WHERE wait_event IS NOT NULL;"

# Check for long-running queries
docker compose exec postgres psql -U dentalos -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '30 seconds';"
```

**Recovery:**

```bash
# Restart PostgreSQL container
docker compose restart postgres

# Wait for it to be healthy
docker compose ps postgres
# Should show "healthy" within 30 seconds

# Verify connectivity
curl -s localhost:8000/api/v1/health | jq .

# If container keeps crashing, check disk space
df -h

# Check PostgreSQL data directory for corruption
docker compose exec postgres pg_dumpall --globals-only > /dev/null && echo "OK"
```

**If data corruption is suspected:**
- Do NOT restart repeatedly — this can worsen corruption
- Escalate to team lead immediately (P1)
- Initiate failover to replica if available
- Contact DBA or PostgreSQL specialist

---

### 3.2 Redis Down

**Symptoms:**
- Elevated API latency (fallthrough to DB is slower)
- Session/auth errors for some users
- Grafana: `redis_up` metric = 0
- Logs show: `redis.exceptions.ConnectionError`

**Diagnosis:**

```bash
# Check container status
docker compose ps redis

# Check logs
docker compose logs --tail=50 redis

# Ping Redis manually
docker compose exec redis redis-cli ping
# Expected: PONG

# Check memory usage
docker compose exec redis redis-cli info memory | grep used_memory_human

# Check connected clients
docker compose exec redis redis-cli info clients

# Check slow log
docker compose exec redis redis-cli slowlog get 10
```

**Recovery:**

```bash
# Restart Redis
docker compose restart redis

# Verify connectivity
docker compose exec redis redis-cli ping

# Verify API fallthrough is working (should still return 200, just slower)
curl -s localhost:8000/api/v1/health | jq .

# After restart, warm up critical caches
# Tenant metadata and plan limits will repopulate on first request
```

**Important:** Redis is a performance enhancement, not a hard dependency. If Redis is down:
- Sessions will fall back to DB lookup (slower but functional)
- Tenant resolution will query `public.tenants` on every request
- Monitor DB connection pool — expect higher utilization during Redis outage

---

### 3.3 RabbitMQ Backlog

**Symptoms:**
- Notifications not being sent (email, WhatsApp, SMS)
- PDF generation stalled (clinical records, invoices)
- Grafana: `rabbitmq_queue_messages` growing steadily
- Workers appear running but not keeping up

**Diagnosis:**

```bash
# Check RabbitMQ management UI (if accessible)
# http://localhost:15672 (guest/guest in dev)

# Check container status
docker compose ps rabbitmq

# Check queue depths via CLI
docker compose exec rabbitmq rabbitmqctl list_queues name messages consumers

# Check which consumers are connected
docker compose exec rabbitmq rabbitmqctl list_consumers

# Check worker container logs
docker compose logs --tail=100 worker-notifications
docker compose logs --tail=100 worker-clinical

# Check for dead letter queue accumulation
docker compose exec rabbitmq rabbitmqctl list_queues name messages | grep dlx
```

**Recovery:**

```bash
# Restart workers if they appear stuck
docker compose restart worker-notifications worker-clinical

# If backlog is > 1000 messages and growing, scale up workers temporarily
docker compose up -d --scale worker-notifications=4

# Purge dead letter queue ONLY if messages are confirmed unrecoverable
# WARNING: This deletes messages permanently — get team lead approval first
docker compose exec rabbitmq rabbitmqctl purge_queue dentalos.notifications.dlx

# After stabilization, scale back to normal
docker compose up -d --scale worker-notifications=2
```

**Preventive check:** If backlog persists after worker restart, check whether a single malformed message is causing repeated failures and blocking the queue. Inspect and remove it:

```bash
# Get one message from the queue to inspect (non-destructive)
docker compose exec rabbitmq rabbitmqadmin get queue=notifications count=1
```

---

### 3.4 High Error Rate (>5%)

**Symptoms:**
- Grafana: `http_requests_total{status=~"5.."}` / total > 5%
- Sentry spike in new issues
- Users reporting errors

**Diagnosis:**

```bash
# Check Sentry for the most frequent new errors in the last 15 minutes

# Check application logs with structured output
docker compose logs --tail=200 api | grep '"level":"error"' | jq '{time: .time, error: .error, path: .path, tenant: .tid}'

# Identify top error patterns
docker compose logs --tail=500 api | grep '"level":"error"' | jq -r '.error' | sort | uniq -c | sort -rn | head -20

# Check if error correlates with a recent deployment
git log --oneline -10

# Check health endpoint
curl -s localhost:8000/api/v1/health | jq .

# Check per-endpoint error rates
curl -s localhost:8000/api/v1/metrics | grep 'http_requests_total' | grep -v '#'
```

**Recovery:**

```bash
# If error started after recent deployment → rollback immediately
git log --oneline -3
# Identify previous good commit hash

# Rolling restart to clear any transient state
docker compose restart api

# If errors are isolated to specific endpoints:
# - Check if a migration was applied correctly
# - Check if a schema change broke a query

# If database-related errors:
# Check for failed migrations
docker compose exec api alembic current
docker compose exec api alembic history | head -5

# Rollback last migration if it caused the issue (get team lead approval)
docker compose exec api alembic downgrade -1
```

**Do NOT log PHI when investigating:** Sanitize any log output before sharing in Slack or incident docs.

---

### 3.5 High Latency (p95 > 2s)

**Symptoms:**
- Grafana: `http_request_duration_seconds{quantile="0.95"}` > 2.0
- Users reporting slow page loads
- No increase in error rate (requests succeeding but slow)

**Diagnosis:**

```bash
# Check Prometheus metrics for slowest endpoints
curl -s localhost:8000/api/v1/metrics | grep 'http_request_duration' | grep 'quantile="0.95"' | sort -t= -k2 -rn | head -10

# Check PostgreSQL slow query log
docker compose exec postgres psql -U dentalos -c "
SELECT query, calls, total_exec_time, mean_exec_time, rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;"

# Check DB connection pool saturation
docker compose exec postgres psql -U dentalos -c "
SELECT count(*), state
FROM pg_stat_activity
GROUP BY state;"

# Check if Redis latency is contributing
docker compose exec redis redis-cli --latency -i 1

# Check system resources on the host
docker stats --no-stream

# Check for N+1 query patterns in logs
docker compose logs --tail=200 api | grep '"duration_ms"' | jq 'select(.duration_ms > 500)' | head -20
```

**Recovery:**

```bash
# Kill runaway long-running queries (get team lead approval for production)
docker compose exec postgres psql -U dentalos -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE (now() - query_start) > interval '60 seconds'
AND state = 'active'
AND query NOT LIKE '%pg_stat_activity%';"

# If connection pool exhausted, restart the API to reset connections
docker compose restart api

# If a specific query is the culprit, check for missing index
docker compose exec postgres psql -U dentalos -c "EXPLAIN ANALYZE <slow_query_here>;"

# Flush Redis cache for the affected resource to force fresh data
# (only if stale cache is contributing)
docker compose exec redis redis-cli --scan --pattern "dentalos:*:clinical:*" | xargs docker compose exec redis redis-cli DEL
```

---

### 3.6 Tenant Isolation Failure

**This is a P1 CRITICAL incident. Stop all non-essential work.**

**Symptoms:**
- A tenant reports seeing another clinic's data
- Logs show `search_path` set to wrong schema
- Cross-tenant query returns rows from multiple schemas

**Immediate Response (first 5 minutes):**

1. **Do not attempt to fix silently.** Escalate to team lead and CTO immediately.
2. Identify which tenants may have been exposed.
3. Consider taking the affected tenants offline temporarily to prevent further exposure.
4. Begin evidence preservation — do not restart services until logs are captured.

**Diagnosis:**

```bash
# Capture current application logs BEFORE any restart
docker compose logs --no-log-prefix api > /tmp/incident-api-$(date +%Y%m%d-%H%M%S).log

# Check what search_path was set for recent connections
docker compose exec postgres psql -U dentalos -c "
SELECT pid, usename, application_name, state, query
FROM pg_stat_activity
WHERE query LIKE '%search_path%'
ORDER BY query_start DESC;"

# Check audit log for cross-tenant access patterns
docker compose exec postgres psql -U dentalos -c "
SELECT *
FROM public.audit_log
WHERE created_at > now() - interval '1 hour'
AND (details::text LIKE '%search_path%' OR details::text LIKE '%wrong_tenant%')
ORDER BY created_at DESC
LIMIT 50;"

# Verify tenant schema isolation manually
docker compose exec postgres psql -U dentalos -c "
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name LIKE 'tn_%'
ORDER BY schema_name;"
```

**Containment:**

```bash
# If isolation breach is confirmed, revoke all active sessions immediately
docker compose exec redis redis-cli --scan --pattern "dentalos:*:auth:session:*" | xargs docker compose exec redis redis-cli DEL

# Force all users to re-authenticate
# This ensures no compromised sessions remain active

# Block affected tenant(s) temporarily if needed
# Set tenant to inactive in public schema (emergency only, coordinate with team lead)
docker compose exec postgres psql -U dentalos -c "
UPDATE public.tenants SET is_active = false WHERE id = '<affected_tenant_id>';"
```

**Post-containment:**
- Notify affected clinic owners as soon as scope is confirmed
- Engage Legal/Compliance team
- Prepare regulatory notification if PHI was exposed (Colombia Ley 1581/2012)

---

### 3.7 Disk Space Low

**Symptoms:**
- Grafana: `node_filesystem_avail_bytes` < 10% of total
- PostgreSQL logging `could not write to file` errors
- Docker failing to pull images or write logs

**Diagnosis:**

```bash
# Check overall disk usage
df -h

# Find largest directories
du -sh /* 2>/dev/null | sort -rh | head -20
du -sh /var/lib/docker/* 2>/dev/null | sort -rh | head -10

# Check Docker disk usage specifically
docker system df

# Check PostgreSQL data directory size
docker compose exec postgres du -sh /var/lib/postgresql/data/

# Check log file sizes
du -sh /var/log/ 2>/dev/null
docker compose logs --no-log-prefix api 2>&1 | wc -c
```

**Recovery:**

```bash
# Remove unused Docker resources (SAFE — only removes stopped containers, dangling images)
docker system prune -f

# Remove unused volumes (WARNING — confirm no data loss first)
docker volume ls -f dangling=true
docker volume prune -f

# Rotate and compress application logs
logrotate -f /etc/logrotate.d/dentalos 2>/dev/null || true

# Remove old deployment artifacts
find /tmp -name "*.tar.gz" -mtime +7 -delete
find /tmp -name "deploy-*" -mtime +3 -delete

# If PostgreSQL WAL is consuming space, check retention settings
docker compose exec postgres psql -U dentalos -c "SHOW wal_keep_size;"

# Vacuum and analyze to reclaim space from dead tuples
docker compose exec postgres psql -U dentalos -c "VACUUM ANALYZE;"
```

---

## 4. Diagnostic Commands Reference

### Service Health

```bash
# Check overall service health
curl -s localhost:8000/api/v1/health | jq .

# Check detailed health (requires internal access)
curl -s localhost:8000/api/v1/health/detailed | jq .

# Check Prometheus metrics for dentalos-specific metrics
curl -s localhost:8000/api/v1/metrics | grep dentalos_

# Check specific metric
curl -s localhost:8000/api/v1/metrics | grep 'http_requests_total'
curl -s localhost:8000/api/v1/metrics | grep 'http_request_duration_seconds'
```

### Container Status

```bash
# Check all container statuses
docker compose ps

# Check resource usage (CPU, memory) for all containers
docker stats --no-stream

# Check recent events across all containers
docker compose events --since 1h

# Follow logs for all services
docker compose logs -f

# Follow logs for specific service
docker compose logs --tail=100 -f api
docker compose logs --tail=100 -f postgres
docker compose logs --tail=100 -f redis
docker compose logs --tail=100 -f rabbitmq
```

### PostgreSQL

```bash
# Check PostgreSQL logs
docker compose logs --tail=100 postgres

# Connect to PostgreSQL
docker compose exec postgres psql -U dentalos

# Check active connections
docker compose exec postgres psql -U dentalos -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# Check database sizes
docker compose exec postgres psql -U dentalos -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database ORDER BY pg_database_size(datname) DESC;"

# Check tenant schema sizes
docker compose exec postgres psql -U dentalos -c "SELECT schemaname, pg_size_pretty(sum(pg_total_relation_size(schemaname||'.'||tablename))::bigint) FROM pg_tables WHERE schemaname LIKE 'tn_%' GROUP BY schemaname ORDER BY 2 DESC;"

# Check replication lag (if replica exists)
docker compose exec postgres psql -U dentalos -c "SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;"

# List locks
docker compose exec postgres psql -U dentalos -c "SELECT locktype, relation::regclass, mode, granted FROM pg_locks WHERE NOT granted;"
```

### Redis

```bash
# Check Redis logs
docker compose logs --tail=100 redis

# Connect to Redis CLI
docker compose exec redis redis-cli

# Check all stats
docker compose exec redis redis-cli info all

# Check memory stats
docker compose exec redis redis-cli info memory

# Check hit/miss ratio
docker compose exec redis redis-cli info stats | grep -E 'keyspace_hits|keyspace_misses'

# Count keys by pattern
docker compose exec redis redis-cli --scan --pattern "dentalos:*" | wc -l
docker compose exec redis redis-cli --scan --pattern "dentalos:*:auth:*" | wc -l

# Check latency
docker compose exec redis redis-cli --latency -i 1
```

### RabbitMQ

```bash
# Check RabbitMQ logs
docker compose logs --tail=100 rabbitmq

# List all queues with message counts
docker compose exec rabbitmq rabbitmqctl list_queues name messages consumers ready unacknowledged

# Check queue details
docker compose exec rabbitmq rabbitmqctl list_queues name messages_ready messages_unacknowledged

# Check exchange bindings
docker compose exec rabbitmq rabbitmqctl list_bindings

# Check connections
docker compose exec rabbitmq rabbitmqctl list_connections

# Check channels
docker compose exec rabbitmq rabbitmqctl list_channels
```

### Application Logs (structured JSON)

```bash
# All errors in the last 200 lines
docker compose logs --tail=200 api | grep '"level":"error"' | jq '{time: .time, error: .error, path: .path}'

# Errors for a specific tenant (do not log PHI)
docker compose logs --tail=500 api | grep '"level":"error"' | jq 'select(.tid == "tn_<tenant_id>")'

# Slow requests (>500ms)
docker compose logs --tail=500 api | jq 'select(.duration_ms > 500) | {path: .path, duration_ms: .duration_ms, method: .method}'

# Count errors by endpoint
docker compose logs --tail=1000 api | grep '"level":"error"' | jq -r '.path' | sort | uniq -c | sort -rn | head -20

# Check for authentication failures
docker compose logs --tail=200 api | grep '"level":"warning"' | jq 'select(.error | test("AUTH"))'
```

---

## 5. Recovery Procedures

### 5.1 Rolling Restart (API)

Use when the API is degraded but not completely down. Minimizes downtime.

```bash
# With multiple API replicas (production):
# Restart one instance at a time
docker compose up -d --no-deps --scale api=1 api
# Wait for health check to pass
sleep 10
curl -s localhost:8000/api/v1/health | jq .
# Scale back up
docker compose up -d --scale api=2

# Single instance (dev/staging):
docker compose restart api
sleep 5
curl -s localhost:8000/api/v1/health | jq .
```

### 5.2 Database Failover

Use when primary PostgreSQL is unrecoverable and a replica is available.

```bash
# Step 1: Confirm primary is down
docker compose exec postgres psql -U dentalos -c "SELECT 1;" 2>&1

# Step 2: Promote replica to primary (if Patroni or similar HA tool is configured)
# This step depends on your HA setup — document the specific commands here

# Step 3: Update application connection string
# Edit docker-compose.yml or environment variable:
# DATABASE_URL=postgresql+asyncpg://dentalos:<pass>@<replica_host>:5432/dentalos

# Step 4: Restart API to pick up new connection
docker compose up -d --no-deps api

# Step 5: Verify connectivity
curl -s localhost:8000/api/v1/health | jq .

# Step 6: Verify a sample tenant schema is accessible
docker compose exec postgres psql -U dentalos -c "SET search_path TO tn_<sample_schema>, public; SELECT count(*) FROM patients;"
```

### 5.3 Cache Flush (Redis)

Use when stale cache data is causing incorrect behavior.

```bash
# Flush all DentalOS keys (safe — data persists in PostgreSQL)
docker compose exec redis redis-cli --scan --pattern "dentalos:*" | xargs -r docker compose exec -T redis redis-cli DEL

# Flush specific domain cache
# Tenant metadata:
docker compose exec redis redis-cli --scan --pattern "dentalos:*:config:*" | xargs -r docker compose exec -T redis redis-cli DEL

# Auth sessions (forces all users to re-login — use with caution):
docker compose exec redis redis-cli --scan --pattern "dentalos:*:auth:*" | xargs -r docker compose exec -T redis redis-cli DEL

# Odontogram cache:
docker compose exec redis redis-cli --scan --pattern "dentalos:*:clinical:odontogram:*" | xargs -r docker compose exec -T redis redis-cli DEL

# Appointment slots:
docker compose exec redis redis-cli --scan --pattern "dentalos:*:appointment:slots:*" | xargs -r docker compose exec -T redis redis-cli DEL

# Nuclear option — flush entire Redis DB (forces re-login for all users)
# Get team lead approval before doing this in production
docker compose exec redis redis-cli FLUSHALL
```

### 5.4 Queue Purge

Use when a queue is clogged with unprocessable messages causing worker stalls.

```bash
# Check queue depths first
docker compose exec rabbitmq rabbitmqctl list_queues name messages

# Purge a specific queue (WARNING: messages are permanently deleted)
# Only do this for dead letter queues or after confirming messages are unrecoverable
# Get team lead approval first

# Purge dead letter queue only:
docker compose exec rabbitmq rabbitmqctl purge_queue dentalos.notifications.dlx
docker compose exec rabbitmq rabbitmqctl purge_queue dentalos.clinical.dlx

# Purge main queue (last resort — this drops pending notifications, PDF jobs, etc.):
docker compose exec rabbitmq rabbitmqctl purge_queue notifications

# After purge, restart workers to ensure clean state
docker compose restart worker-notifications worker-clinical
```

### 5.5 Application Rollback

Use when a deployment causes a P1/P2 incident.

```bash
# Identify the last known good commit
git log --oneline -10

# Rollback to previous image (if using Docker image tags)
# Edit docker-compose.yml to pin to previous image tag
# Example: api:v1.2.3 → api:v1.2.2

# OR: Rebuild from previous commit
git checkout <last_good_commit_hash>
docker compose build api
docker compose up -d --no-deps api

# If a migration was applied, roll it back first
docker compose exec api alembic current
docker compose exec api alembic downgrade -1

# Verify rollback worked
curl -s localhost:8000/api/v1/health | jq .
```

---

## 6. Post-Incident Review Template

Conduct the review within 48 hours of resolution. Blameless. Focus on systems and processes, not individuals.

---

```markdown
# Post-Incident Review

**Incident ID:** INC-YYYY-MM-DD-001
**Date of Review:** YYYY-MM-DD
**Facilitator:** [Name]
**Attendees:** [List]

---

## Incident Summary

| Field | Value |
|-------|-------|
| **Severity** | P1 / P2 / P3 |
| **Start Time** | YYYY-MM-DD HH:MM UTC |
| **End Time** | YYYY-MM-DD HH:MM UTC |
| **Total Duration** | X hours Y minutes |
| **Detection Method** | Grafana alert / Sentry / User report |
| **Time to Detect** | X minutes after incident started |
| **Time to Acknowledge** | X minutes after alert fired |
| **Time to Mitigate** | X minutes after acknowledgment |
| **Time to Resolve** | X minutes after mitigation |

---

## Impact

- **Tenants Affected:** [Number and names if appropriate, no PHI]
- **Users Affected:** [Estimated count]
- **Features Affected:** [List]
- **Data Loss:** Yes / No (if yes, describe scope without PHI)
- **Revenue Impact:** [Estimate if applicable]
- **Regulatory Implications:** [None / Under review / Reportable]

---

## Incident Timeline

| Time (UTC) | Event |
|-----------|-------|
| HH:MM | Alert fired in Grafana / Sentry |
| HH:MM | On-call engineer acknowledged |
| HH:MM | Severity classified as P[1/2/3] |
| HH:MM | Initial diagnosis: [summary] |
| HH:MM | Mitigation applied: [what was done] |
| HH:MM | Partial recovery observed |
| HH:MM | Full resolution confirmed |
| HH:MM | Tenants notified |

---

## Root Cause Analysis

**What failed:**
[Describe the technical failure — be specific]

**Why it failed:**
[Describe the underlying cause — not "human error" but what systemic condition made this possible]

**Why it was not caught earlier:**
[What monitoring/testing/review gap allowed this to reach production]

---

## What Went Well

- [List things that worked: fast detection, good runbook, team communication, etc.]

---

## What Went Poorly

- [List gaps: slow detection, missing runbook step, alert too noisy, unclear ownership, etc.]

---

## Action Items

| # | Action | Owner | Due Date | Priority |
|---|--------|-------|----------|----------|
| 1 | [Specific, measurable action] | @engineer | YYYY-MM-DD | P1/P2/P3 |
| 2 | Add/update Grafana alert for [condition] | @engineer | YYYY-MM-DD | P2 |
| 3 | Write runbook entry for [scenario] | @engineer | YYYY-MM-DD | P3 |
| 4 | Add test coverage for [failure mode] | @engineer | YYYY-MM-DD | P2 |

---

## Metrics (for tracking over time)

- MTTD (Mean Time to Detect): X minutes
- MTTA (Mean Time to Acknowledge): X minutes
- MTTM (Mean Time to Mitigate): X minutes
- MTTR (Mean Time to Resolve): X minutes
```

---

## Appendix: Alert Thresholds Reference

| Metric | Warning | Critical | Alert Type |
|--------|---------|----------|------------|
| Error rate | > 1% | > 5% | P2 at critical |
| p95 latency | > 1s | > 2s | P2 at critical |
| DB connections | > 80% pool | > 95% pool | P2 at critical |
| Redis memory | > 70% | > 90% | P3 / P2 |
| Queue depth (notifications) | > 100 | > 500 | P3 / P2 |
| Queue depth (clinical) | > 50 | > 200 | P3 / P2 |
| Disk usage | > 75% | > 90% | P3 / P2 |
| CPU (sustained 5min) | > 70% | > 90% | P3 / P2 |

---

*This runbook should be reviewed and updated after every P1/P2 incident. If a scenario you encountered is not covered here, add it before closing the post-incident review.*
