# DentalOS — Admin Operations Runbook

**Audience:** Platform engineers and on-call ops team
**Last reviewed:** 2026-02-27
**Production contact:** ops-oncall Slack channel

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Common Operations](#2-common-operations)
3. [Deployment Procedures](#3-deployment-procedures)
4. [Monitoring & Alerting](#4-monitoring--alerting)
5. [Incident Response](#5-incident-response)
6. [Backup & Recovery](#6-backup--recovery)
7. [Security Operations](#7-security-operations)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. System Overview

### Architecture Diagram

```
                             Hetzner Cloud
┌────────────────────────────────────────────────────────────┐
│                                                            │
│   Internet ──► Cloudflare (WAF + CDN)                      │
│                     │                                      │
│                     ▼                                      │
│            Hetzner Load Balancer (TLS termination)         │
│             ├──► frontend:3000   (Next.js 16 standalone)   │
│             └──► backend:8000    (FastAPI + Gunicorn)      │
│                      │                                     │
│          ┌───────────┼────────────────────────┐            │
│          ▼           ▼                        ▼            │
│     postgres:5432  redis:6379          rabbitmq:5672       │
│     (PostgreSQL 16) (Redis 7)         (RabbitMQ 3)        │
│          │                                    │            │
│          │                            ┌───────┘            │
│          │                            ▼                    │
│          │                     workers (4 containers)      │
│          │                     notifications (x2)          │
│          │                     clinical (x2)               │
│          ▼                                                 │
│     minio:9000  (MinIO S3-compatible object storage)       │
│                                                            │
│     prometheus:9090 + grafana:3001  (monitoring stack)     │
└────────────────────────────────────────────────────────────┘
```

### Service URLs and Ports

| Service | Internal host:port | Public URL | Notes |
|---|---|---|---|
| Frontend | `127.0.0.1:3000` | `https://app.dentalos.co` | Via Hetzner LB |
| Backend API | `127.0.0.1:8000` | `https://api.dentalos.co` | Via Hetzner LB |
| PostgreSQL | `127.0.0.1:5432` | — | Localhost only |
| Redis | `127.0.0.1:6379` | — | Localhost only |
| RabbitMQ AMQP | `127.0.0.1:5672` | — | Localhost only |
| RabbitMQ Mgmt | `127.0.0.1:15672` | Via SSH tunnel | See §2 RabbitMQ |
| MinIO S3 | `127.0.0.1:9000` | — | Localhost only |
| MinIO Console | `127.0.0.1:9001` | Via SSH tunnel | |
| Prometheus | `127.0.0.1:9090` | Via SSH tunnel | |
| Grafana | `127.0.0.1:3001` | Via SSH tunnel | |

### Key Directories on Production Server

```
/opt/dentalos/                  # Application root
├── docker-compose.prod.yml     # Production compose file
├── .env                        # Runtime secrets (chmod 600, root-owned)
├── backend/
│   ├── keys/private.pem        # JWT RS256 private key (chmod 400)
│   └── keys/public.pem         # JWT RS256 public key
├── ops/backup/
│   ├── pg_backup.sh            # Full schema backup script
│   ├── pg_restore.sh           # Restore script
│   └── pg_wal_archive.sh       # WAL archiver (configured in postgresql.conf)
└── scripts/db/init.sql         # DB init (runs once on first container start)

/var/backups/dentalos/          # Local backup destination
├── YYYYMMDD_HHMMSS/            # One directory per backup run
│   ├── manifest.json
│   ├── public.dump
│   ├── globals.sql
│   └── tn_<schema>.dump        # One per tenant
└── wal/                        # WAL archive for PITR

/var/log/dentalos/              # Application logs (if log driver writes to disk)
```

### SSH Access

```bash
# Production server
ssh deploy@prod.dentalos.co -i ~/.ssh/dentalos_prod

# Open SSH tunnel to access internal services (RabbitMQ, Grafana, MinIO)
ssh -L 15672:127.0.0.1:15672 \
    -L 3001:127.0.0.1:3001   \
    -L 9001:127.0.0.1:9001   \
    -L 9090:127.0.0.1:9090   \
    deploy@prod.dentalos.co -N
```

---

## 2. Common Operations

### Tenant Provisioning

#### Create a New Tenant

Tenant creation is fully automated through the admin API. The service creates the
`tn_<schema>` schema, seeds it, and saves tenant metadata to `public.tenants` in one
transaction.

```bash
# 1. Obtain an admin JWT (TOTP required in production)
TOKEN=$(curl -s -X POST https://api.dentalos.co/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ops@dentalos.co","password":"<pass>","totp_code":"<6-digit>"}' \
  | jq -r '.access_token')

# 2. Create the tenant
curl -s -X POST https://api.dentalos.co/api/v1/admin/tenants \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Clínica Dental Norte",
    "owner_email": "owner@clinicadentalnorte.co",
    "country_code": "CO",
    "plan_id": "starter",
    "phone": "+573001234567"
  }' | jq .
```

Expected response includes `tenant_id`, `schema_name` (`tn_<slug>`), and `status: "active"`.

#### Seed / Re-seed a Tenant Schema Manually

If automatic seeding failed or needs to be re-run:

```bash
# On the production server, inside the backend container
docker exec -it dentalos-backend-prod bash

# Run the tenant seeding script (adjusts search_path internally)
python -m app.scripts.seed_tenant --schema tn_clinicadentalnorte
```

#### Configure Tenant Settings

```bash
# Update timezone, plan, or country via admin API
curl -s -X PUT https://api.dentalos.co/api/v1/admin/tenants/<tenant_id> \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "timezone": "America/Bogota",
    "country_code": "CO",
    "plan_id": "pro"
  }' | jq .
```

Or directly in the database (use only if the API is unavailable):

```sql
-- Connect to the production database
psql -h 127.0.0.1 -U dentalos -d dentalos

UPDATE public.tenants
SET    timezone = 'America/Bogota',
       plan_id  = 'pro',
       updated_at = now()
WHERE  id = '<tenant_uuid>';
```

#### Activate / Deactivate a Tenant

```bash
# Suspend (sets is_active = false, blocks logins)
curl -s -X POST https://api.dentalos.co/api/v1/admin/tenants/<tenant_id>/suspend \
  -H "Authorization: Bearer $TOKEN" | jq .

# Reactivate via direct DB update (no reactivate endpoint yet)
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "UPDATE public.tenants SET is_active = true, updated_at = now() WHERE id = '<tenant_uuid>';"

# Flush tenant cache after reactivation
redis-cli -a "$REDIS_PASSWORD" KEYS "dentalos:<tenant_short_id>:*" | \
  xargs redis-cli -a "$REDIS_PASSWORD" DEL
```

---

### User Management

#### Create Staff User via Admin API

```bash
curl -s -X POST https://api.dentalos.co/api/v1/users \
  -H "Authorization: Bearer $TENANT_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "doctor@clinica.co",
    "first_name": "Juan",
    "last_name": "Pérez",
    "role": "doctor",
    "password": "<temp-password>"
  }' | jq .
```

#### Reset User Password

```bash
# Trigger password reset email
curl -s -X POST https://api.dentalos.co/api/v1/auth/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{"email": "doctor@clinica.co"}' | jq .

# Or force-reset directly in the DB (last resort, bcrypt hash)
python3 -c "import bcrypt; print(bcrypt.hashpw(b'NewPass123!', bcrypt.gensalt(rounds=12)).decode())"
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SET search_path TO tn_<schema>, public;
   UPDATE users SET password_hash = '<hash>', updated_at = now()
   WHERE email = 'doctor@clinica.co';"
```

#### Lock / Unlock Account

```bash
# Lock (failed_login_attempts >= lockout_threshold triggers auto-lock)
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SET search_path TO tn_<schema>, public;
   UPDATE users SET locked_until = now() + interval '1 year', updated_at = now()
   WHERE email = 'doctor@clinica.co';"

# Unlock
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SET search_path TO tn_<schema>, public;
   UPDATE users SET locked_until = null, failed_login_attempts = 0, updated_at = now()
   WHERE email = 'doctor@clinica.co';"

# Invalidate active sessions in Redis
redis-cli -a "$REDIS_PASSWORD" KEYS "dentalos:*:auth:session:<user_id>" | \
  xargs redis-cli -a "$REDIS_PASSWORD" DEL
```

#### Add User to Multiple Clinics

```bash
# The user must exist in public.users first. Then insert a membership row.
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "INSERT INTO public.user_tenant_memberships (user_id, tenant_id, role, is_active)
   VALUES ('<user_uuid>', '<tenant_uuid>', 'doctor', true);"
```

---

### Database Operations

#### Run Alembic Migrations

DentalOS uses two separate Alembic configurations:
- `alembic.ini` — public schema (shared tables: tenants, plans, superadmins)
- `alembic_tenant/alembic.ini` — per-tenant schemas

```bash
# SSH into the server and enter the backend container
docker exec -it dentalos-backend-prod bash
cd /app

# Migrate the public schema
alembic upgrade head

# Migrate a single tenant schema
alembic -c alembic_tenant/alembic.ini upgrade head -x schema=tn_clinicadentalnorte

# Migrate ALL tenant schemas (run from the server, not the container)
for schema in $(psql -h 127.0.0.1 -U dentalos -d dentalos -t -A \
  -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tn_%';"); do
  echo "Migrating $schema..."
  docker exec dentalos-backend-prod \
    alembic -c alembic_tenant/alembic.ini upgrade head -x schema=$schema
done

# Check current migration state
alembic current
alembic -c alembic_tenant/alembic.ini current -x schema=tn_<schema>
```

#### Create a Manual Database Backup

```bash
# Run the backup script directly (uses env vars from .env)
source /opt/dentalos/.env
/opt/dentalos/ops/backup/pg_backup.sh

# Expected output:
# [2026-02-27T03:00:00+00:00] Starting DentalOS backup...
#   Dumping public schema...
#   Dumping schema: tn_clinicadentalnorte...
#   Dumping globals...
# [2026-02-27T03:02:14+00:00] Backup complete: 5 tenant schemas + public + globals (234M)
#   Location: /var/backups/dentalos/20260227_030000

# Verify backup
cat /var/backups/dentalos/20260227_030000/manifest.json
ls -lh /var/backups/dentalos/20260227_030000/
```

#### Restore from Backup

```bash
# See §6 Backup & Recovery for full restore procedures.

# Restore single tenant (targeted recovery)
/opt/dentalos/ops/backup/pg_restore.sh /var/backups/dentalos/20260227_030000 \
  --schema tn_clinicadentalnorte

# Restore all schemas (disaster recovery)
/opt/dentalos/ops/backup/pg_restore.sh /var/backups/dentalos/20260227_030000
```

#### Check Database Health and Connections

```bash
# Connection count by state
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT state, count(*) FROM pg_stat_activity
   WHERE datname = 'dentalos' GROUP BY state ORDER BY count DESC;"

# Check for long-running queries (> 30 seconds)
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
   FROM pg_stat_activity
   WHERE state != 'idle' AND query_start < now() - interval '30 seconds'
   ORDER BY duration DESC;"

# Kill a blocking query
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT pg_terminate_backend(<pid>);"

# Database sizes
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT schema_name,
          pg_size_pretty(sum(table_size)) AS size
   FROM (
     SELECT table_schema AS schema_name,
            pg_total_relation_size(quote_ident(table_schema) || '.' || quote_ident(table_name)) AS table_size
     FROM information_schema.tables
   ) t
   WHERE schema_name LIKE 'tn_%' OR schema_name = 'public'
   GROUP BY schema_name ORDER BY sum(table_size) DESC;"
```

#### Query Slow Queries Log

```bash
# Enable pg_stat_statements if not already active
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"

# Top 10 slowest queries by mean execution time
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT mean_exec_time::int AS mean_ms,
          calls,
          left(query, 100) AS query_snippet
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC LIMIT 10;"
```

---

### Redis Operations

#### Flush Tenant Cache

```bash
# Flush all keys for a specific tenant (safe; fallback is PostgreSQL)
TENANT_SHORT="abc123"
redis-cli -a "$REDIS_PASSWORD" KEYS "dentalos:${TENANT_SHORT}:*" | \
  xargs redis-cli -a "$REDIS_PASSWORD" DEL

# Flush a specific cache domain
redis-cli -a "$REDIS_PASSWORD" KEYS "dentalos:${TENANT_SHORT}:clinical:odontogram:*" | \
  xargs redis-cli -a "$REDIS_PASSWORD" DEL

# Flush the entire cache (CAUTION: impacts all tenants)
redis-cli -a "$REDIS_PASSWORD" FLUSHDB
```

#### Monitor Cache Hit Rate

```bash
redis-cli -a "$REDIS_PASSWORD" INFO stats | grep -E "keyspace_hits|keyspace_misses"
# keyspace_hits:148293
# keyspace_misses:12047
# Hit rate ≈ hits / (hits + misses)
```

#### Check Memory Usage

```bash
redis-cli -a "$REDIS_PASSWORD" INFO memory | grep -E "used_memory_human|maxmemory_human|mem_fragmentation_ratio"
# used_memory_human:42.31M
# maxmemory_human:256.00M
# mem_fragmentation_ratio:1.12   (> 1.5 indicates fragmentation; restart Redis to compact)
```

---

### RabbitMQ Operations

#### Access Management UI (via SSH tunnel)

```bash
# On your local machine, open the tunnel first (see §1 SSH Access)
open http://localhost:15672
# Default credentials are in .env: RABBITMQ_USER / RABBITMQ_PASSWORD
```

#### Check Queue Depths

```bash
docker exec dentalos-rabbitmq-prod rabbitmqctl list_queues \
  name messages consumers memory --vhost dentalos

# Expected output:
# Listing queues for vhost dentalos
# notifications   0   2   65536
# clinical        0   2   49152
# import          0   1   32768
# maintenance     0   1   32768
```

#### Purge Stuck Messages

```bash
# Purge a specific queue (messages are permanently deleted — use with care)
docker exec dentalos-rabbitmq-prod rabbitmqctl purge_queue notifications --vhost dentalos

# Inspect dead letter queue before purging
docker exec dentalos-rabbitmq-prod rabbitmqctl list_queues \
  name messages --vhost dentalos | grep dlx
```

#### Restart Workers

```bash
# Restart all workers
docker compose -f /opt/dentalos/docker-compose.prod.yml restart \
  worker-notifications worker-clinical worker-import worker-maintenance

# Check worker logs
docker logs dentalos-worker-notifications --tail 100 -f
```

---

## 3. Deployment Procedures

### GitHub Actions Auto-Deploy (Normal Flow)

1. Push a merge to `main` branch.
2. GitHub Actions runs: lint → test → build Docker images → push to registry → SSH deploy.
3. The deploy step on the server runs:
   ```bash
   docker compose -f docker-compose.prod.yml pull
   docker compose -f docker-compose.prod.yml up -d --no-deps backend frontend
   ```
4. Alembic migrations run as a pre-deploy step in the pipeline.
5. Check the Actions tab for status. On failure, Slack alert fires to `#deployments`.

### Manual Deploy (SSH)

Use this only when the GitHub Actions pipeline is broken or a hotfix must bypass CI.

```bash
ssh deploy@prod.dentalos.co

cd /opt/dentalos

# Pull latest images (built and pushed by CI)
docker compose -f docker-compose.prod.yml pull backend frontend

# Run migrations before starting the new containers
docker run --rm --env-file .env \
  --network dentalos-prod \
  dentalos-backend:latest \
  alembic upgrade head

# Restart app containers only (leave postgres/redis/rabbitmq running)
docker compose -f docker-compose.prod.yml up -d --no-deps backend frontend

# Verify health
docker compose -f docker-compose.prod.yml ps
curl -s http://127.0.0.1:8000/api/v1/health | jq .status
```

### Rollback to Previous Version

```bash
ssh deploy@prod.dentalos.co
cd /opt/dentalos

# List recent image tags from the registry
docker images dentalos-backend --format "{{.Tag}}\t{{.CreatedAt}}" | head -10

# Pin to a specific commit SHA tag
docker compose -f docker-compose.prod.yml stop backend frontend

# Edit docker-compose.prod.yml to pin image tags, or use environment variable:
BACKEND_IMAGE=dentalos-backend:sha-abc1234 \
FRONTEND_IMAGE=dentalos-frontend:sha-abc1234 \
docker compose -f docker-compose.prod.yml up -d --no-deps backend frontend

# Monitor logs for errors
docker logs dentalos-backend-prod --tail 200 -f
```

**Note:** If the rolled-back version requires reversing a migration, contact the on-call
engineer. Alembic downgrade is rarely safe — prefer creating a corrective forward migration.

### Blue-Green Switch

The Hetzner Load Balancer routes to two named targets. To switch:

1. Deploy the new version to the "green" target group (separate containers on the same host
   or a second server).
2. Confirm green is healthy: `curl -s http://<green-ip>:8000/api/v1/health`.
3. In Hetzner Cloud Console, update the Load Balancer target to point to green.
4. Monitor for 5 minutes. If errors spike, revert the LB target to blue.
5. Decommission blue after 30 minutes.

---

## 4. Monitoring & Alerting

### Grafana Dashboards

Access via SSH tunnel on `http://localhost:3001` (credentials in `.env: GF_SECURITY_ADMIN_PASSWORD`).

| Dashboard | What it shows |
|---|---|
| **DentalOS Overview** | Request rate, error rate, p95 latency, active tenants |
| **PostgreSQL** | Connections, cache hit ratio, table sizes, replication lag |
| **Redis** | Memory usage, hit rate, eviction rate |
| **RabbitMQ** | Queue depths, message rates, consumer counts |
| **Infrastructure** | CPU, RAM, disk I/O per container |

### Key Metrics to Watch

| Metric | Healthy range | Alert threshold |
|---|---|---|
| API error rate (5xx) | < 0.1% | > 1% for 5 min |
| API p95 latency | < 300ms | > 2s for 5 min |
| DB connection pool used | < 60% | > 80% |
| Redis memory used | < 70% (179MB) | > 85% (218MB) |
| RabbitMQ queue depth (any) | < 100 | > 500 for 2 min |
| Disk usage `/var/backups` | < 70% | > 85% |
| SSL certificate expiry | > 30 days | < 14 days |

### Prometheus Scrape Targets

- Backend metrics: `http://backend:8000/api/v1/metrics` (scrape interval: 15s)
- Add node_exporter for host-level metrics if not already deployed.

### Sentry Error Tracking

- Project: `dentalos-backend` and `dentalos-frontend`
- URL: `https://sentry.io/organizations/dentalos/`
- PHI reminder: Sentry is configured with `send_default_pii = False`. Never add patient
  identifiers to breadcrumbs or exception context.
- Set `SENTRY_TRACES_SAMPLE_RATE=0.1` in production (10% of requests).

### Alert Thresholds and Escalation

| Severity | Condition | Response time | Who |
|---|---|---|---|
| P0 | Full outage, data loss risk | 15 min | On-call + CTO |
| P1 | Partial outage, >10% users affected | 30 min | On-call |
| P2 | Degraded performance, single-tenant issue | 2 h | On-call (business hours) |
| P3 | Non-critical, cosmetic | Next business day | Engineering |

Alerts route via Grafana → PagerDuty → `#ops-alerts` Slack channel.

---

## 5. Incident Response

### Severity Levels

**P0 — Critical:** Full platform down, database unavailable, data loss in progress, security breach.
**P1 — High:** Multiple tenants affected, a core workflow broken (appointments, billing).
**P2 — Medium:** Single tenant affected, non-critical feature broken.
**P3 — Low:** UI glitch, minor performance degradation, cosmetic issue.

### Communication Channels

- Real-time: `#ops-alerts` (automated) and `#ops-incidents` (human updates)
- Status page: update `status.dentalos.co` for P0/P1
- Customer comms: `ops@dentalos.co` → affected clinic owners
- Post-mortems: required for all P0/P1 within 48 hours

### Playbook: Database Connection Pool Exhaustion

**Symptoms:** 503 errors, logs show `asyncpg.TooManyConnectionsError`, Grafana shows
`pg_stat_activity` count near `max_connections`.

```bash
# 1. Check current connections
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# 2. Identify the longest-held idle connections
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT pid, usename, application_name, state, query_start,
          now() - query_start AS duration
   FROM pg_stat_activity WHERE state = 'idle in transaction'
   ORDER BY duration DESC LIMIT 20;"

# 3. Terminate idle-in-transaction connections older than 10 minutes
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'idle in transaction'
     AND query_start < now() - interval '10 minutes';"

# 4. If the pool is still saturated, restart the backend (drops all connections)
docker compose -f /opt/dentalos/docker-compose.prod.yml restart backend

# 5. Long-term: increase pool size in .env (DATABASE_POOL_SIZE) and redeploy
```

### Playbook: RabbitMQ Queue Backup

**Symptoms:** Queue depth > 500, notification emails delayed, workers not consuming.

```bash
# 1. Check consumer count
docker exec dentalos-rabbitmq-prod rabbitmqctl list_queues \
  name messages consumers --vhost dentalos

# 2. Check worker container health
docker compose -f /opt/dentalos/docker-compose.prod.yml ps | grep worker

# 3. Restart workers if they have crashed or stalled
docker compose -f /opt/dentalos/docker-compose.prod.yml restart \
  worker-notifications worker-clinical

# 4. If messages are stuck in a dead letter queue, inspect and replay
docker exec dentalos-rabbitmq-prod rabbitmqctl list_queues \
  name messages --vhost dentalos | grep dlx

# Replay (shovel from DLX back to the main queue) via Management UI or rabbitmqadmin
docker exec dentalos-rabbitmq-prod rabbitmqadmin --vhost=dentalos \
  publish exchange=dentalos.direct routing_key=notifications \
  payload='{"requeue":true}' 2>/dev/null || true

# 5. If the queue cannot drain, purge (data loss — last resort)
docker exec dentalos-rabbitmq-prod rabbitmqctl purge_queue notifications --vhost dentalos
```

### Playbook: Redis OOM (Out of Memory)

**Symptoms:** `OOM command not allowed` in logs, sessions dropping, cache errors.

```bash
# 1. Check memory
redis-cli -a "$REDIS_PASSWORD" INFO memory | grep -E "used_memory_human|maxmemory"

# 2. Identify the largest keys
redis-cli -a "$REDIS_PASSWORD" --memkeys --memkeys-samples 200 | head -20

# 3. Evict large or stale keys manually
redis-cli -a "$REDIS_PASSWORD" KEYS "dentalos:shared:catalog:*" | \
  xargs redis-cli -a "$REDIS_PASSWORD" DEL

# 4. Restart Redis (config already sets allkeys-lru eviction policy; restart resets memory)
docker compose -f /opt/dentalos/docker-compose.prod.yml restart redis

# 5. Increase maxmemory in docker-compose.prod.yml if load justifies it (current: 256mb)
```

### Playbook: High Error Rate

**Symptoms:** Sentry alert, error rate > 1%, 5xx spike in Grafana.

```bash
# 1. Check backend logs for the error pattern
docker logs dentalos-backend-prod --tail 500 | grep -E "ERROR|Exception|Traceback"

# 2. Check for a recent deployment
docker inspect dentalos-backend-prod | jq '.[0].Created'

# 3. If error is tied to a bad deploy, roll back immediately (see §3 Rollback)

# 4. If error is a downstream service (DB, Redis), follow the relevant playbook above

# 5. Isolate a specific tenant causing errors
docker logs dentalos-backend-prod --tail 500 | grep '"tenant_id"' | \
  jq -r '.tenant_id' | sort | uniq -c | sort -rn | head -5
```

### Playbook: SSL Certificate Expiry

```bash
# Check current certificate expiry
echo | openssl s_client -connect api.dentalos.co:443 -servername api.dentalos.co 2>/dev/null \
  | openssl x509 -noout -dates

# Certbot (if used) — force renewal
certbot renew --force-renewal --nginx

# Hetzner-managed cert — renew through Hetzner Cloud Console:
# Load Balancers → <lb-name> → Services → TLS Certificate → Renew
```

---

## 6. Backup & Recovery

### Automated Backup Schedule

| Job | Schedule | Retention | Location |
|---|---|---|---|
| Full schema backup | Daily at 03:00 UTC | 30 days local | `/var/backups/dentalos/` |
| S3 offsite copy | Same (S3 sync in pg_backup.sh) | 90 days | `s3://dentalos-backups/pg-backups/` |
| WAL archiving | Continuous | 7 days local | `/var/backups/dentalos/wal/` |

Crontab entry (as `root` on the production server):

```cron
0 3 * * * /opt/dentalos/ops/backup/pg_backup.sh >> /var/log/dentalos/backup.log 2>&1
```

### Manual Backup

```bash
# Trigger an immediate full backup
source /opt/dentalos/.env
BACKUP_DIR=/var/backups/dentalos \
RETENTION_DAYS=30 \
/opt/dentalos/ops/backup/pg_backup.sh

# Single-tenant backup (e.g., before a risky data migration)
source /opt/dentalos/.env
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_SUBDIR="/var/backups/dentalos/manual_${TIMESTAMP}"
mkdir -p "$BACKUP_SUBDIR"
pg_dump -h 127.0.0.1 -U dentalos -d dentalos \
  --schema=tn_clinicadentalnorte \
  --format=custom --compress=9 \
  --file="${BACKUP_SUBDIR}/tn_clinicadentalnorte.dump"
```

### Restore from Backup

```bash
# Restore a single tenant schema (does NOT touch other tenants)
/opt/dentalos/ops/backup/pg_restore.sh \
  /var/backups/dentalos/20260227_030000 \
  --schema tn_clinicadentalnorte

# Restore the public schema only
/opt/dentalos/ops/backup/pg_restore.sh \
  /var/backups/dentalos/20260227_030000 \
  --schema public

# Full disaster recovery (drops and recreates ALL schemas)
# WARNING: This is destructive. Stop the application first.
docker compose -f /opt/dentalos/docker-compose.prod.yml stop backend frontend
/opt/dentalos/ops/backup/pg_restore.sh /var/backups/dentalos/20260227_030000
docker compose -f /opt/dentalos/docker-compose.prod.yml start backend frontend
```

### Point-in-Time Recovery (PITR)

WAL archiving must be enabled in `postgresql.conf` (see `ops/backup/postgresql.conf.snippet`).

```bash
# 1. Stop PostgreSQL
docker compose -f /opt/dentalos/docker-compose.prod.yml stop postgres

# 2. Restore the base backup from the desired snapshot
/opt/dentalos/ops/backup/pg_restore.sh /var/backups/dentalos/20260226_030000

# 3. Create recovery.conf (PostgreSQL 16 uses recovery_target_time in postgresql.conf)
cat >> /var/lib/postgresql/data/postgresql.conf <<EOF
restore_command = 'cp /var/backups/dentalos/wal/%f %p'
recovery_target_time = '2026-02-27 09:30:00 UTC'
recovery_target_action = 'promote'
EOF

# 4. Create the recovery signal file
touch /var/lib/postgresql/data/recovery.signal

# 5. Start PostgreSQL — it will replay WAL up to the target time
docker compose -f /opt/dentalos/docker-compose.prod.yml start postgres

# 6. Monitor recovery progress
docker logs dentalos-postgres-prod -f | grep -E "recovery|LOG"
```

### Testing Backup Integrity

Run this monthly and after any backup infrastructure change:

```bash
# Restore the latest backup to the staging environment
LATEST=$(ls -td /var/backups/dentalos/2*/ | head -1)
/opt/dentalos/ops/backup/pg_restore.sh "$LATEST" --schema tn_testclinic

# Validate the restored data
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SET search_path TO tn_testclinic, public;
   SELECT count(*) FROM patients;
   SELECT count(*) FROM clinical_records;"

# Compare row counts with production
echo "Production:"
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SET search_path TO tn_clinicadentalnorte, public; SELECT count(*) FROM patients;"
```

---

## 7. Security Operations

### JWT Key Rotation

RS256 key pair lives at `backend/keys/private.pem` and `backend/keys/public.pem`.

```bash
ssh deploy@prod.dentalos.co
cd /opt/dentalos

# 1. Generate new key pair
openssl genrsa -out backend/keys/private_new.pem 4096
openssl rsa -in backend/keys/private_new.pem -pubout -out backend/keys/public_new.pem

# 2. Update jwt_key_id in .env to the new key ID (e.g., "dentalos-key-2")
# This value is embedded in the JWT header as "kid"

# 3. Deploy with both old and new keys in place temporarily
#    (active sessions hold tokens signed by the old key; they expire in 15 min)
cp backend/keys/private.pem backend/keys/private_old.pem
cp backend/keys/private_new.pem backend/keys/private.pem
cp backend/keys/public_new.pem backend/keys/public.pem

# 4. Restart backend
docker compose -f docker-compose.prod.yml restart backend

# 5. After 30 minutes (max refresh token re-issuance window), remove the old key
rm backend/keys/private_old.pem

# 6. Invalidate all refresh tokens in the database (forces all users to re-login)
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "UPDATE public.refresh_tokens SET revoked_at = now() WHERE revoked_at IS NULL;"

# 7. Document the rotation in the security audit log
echo "$(date -Iseconds) JWT key rotated by $(whoami) — new kid: dentalos-key-2" \
  >> /var/log/dentalos/security-audit.log
```

### SSL Certificate Renewal

Certificates are managed by Hetzner Load Balancer or Certbot. Grafana alert fires at < 14 days.

```bash
# Check expiry
echo | openssl s_client -connect api.dentalos.co:443 2>/dev/null | \
  openssl x509 -noout -enddate

# Certbot auto-renewal (should run via systemd timer; verify it is active)
systemctl status certbot.timer
certbot renew --dry-run   # test without renewing

# Force renewal if dry-run succeeds
certbot renew
```

### Security Audit Checklist (Monthly)

```bash
# 1. Review superadmin account list — remove inactive admins
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT email, is_active, totp_enabled, last_login_at FROM public.superadmins ORDER BY last_login_at;"

# 2. Check for tenants with no recent activity (potential churn or abandoned accounts)
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT name, last_activity_at FROM public.tenants
   WHERE last_activity_at < now() - interval '60 days' AND is_active = true;"

# 3. Audit impersonation log entries
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT * FROM public.audit_log WHERE action = 'admin.impersonate'
   ORDER BY created_at DESC LIMIT 50;"

# 4. Scan for failed login spikes (possible brute-force)
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT date_trunc('hour', created_at) AS hour, count(*)
   FROM public.audit_log WHERE action = 'auth.login_failed'
   GROUP BY hour ORDER BY hour DESC LIMIT 48;"

# 5. Verify no direct-to-internet ports are exposed
nmap -sV prod.dentalos.co --open | grep -v "filtered\|closed"
# Expected: only 80 (redirect), 443

# 6. Rotate secrets that are older than 90 days (check .env modification date)
stat /opt/dentalos/.env | grep Modify
```

### PHI Access Review (Quarterly)

```bash
# List all active staff users across all tenants
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT t.name AS clinic, u.email, m.role, m.created_at
   FROM public.user_tenant_memberships m
   JOIN public.tenants t ON t.id = m.tenant_id
   JOIN public.users u ON u.id = m.user_id
   WHERE m.is_active = true
   ORDER BY t.name, m.role;"
```

### IP Allowlist Management

Internal services (RabbitMQ, MinIO, Redis, Prometheus) are bound to `127.0.0.1` and
are only accessible via SSH tunnel. No firewall allowlist is required for them.

For the admin API (`/api/v1/admin/*`) and Grafana, restrict at the Hetzner Firewall:

```bash
# Hetzner CLI — add ops team office IP to admin rule group
hcloud firewall add-rule dentalos-admin \
  --direction in --source-ips "203.0.113.0/24" \
  --protocol tcp --port 8000 --description "Ops office"
```

---

## 8. Troubleshooting

### Backend Won't Start

```bash
# Check container logs for the startup error
docker logs dentalos-backend-prod --tail 100

# Common causes:
# 1. Can't reach PostgreSQL — check postgres container health
docker compose -f /opt/dentalos/docker-compose.prod.yml ps postgres

# 2. Missing or invalid .env variable
docker exec dentalos-backend-prod env | grep -E "DATABASE_URL|REDIS_URL|RABBITMQ_URL"

# 3. JWT key file not found
docker exec dentalos-backend-prod ls /app/keys/

# 4. Port already in use
lsof -i :8000

# 5. Alembic migration failed during startup
docker logs dentalos-backend-prod | grep -i "alembic\|migration"
```

### Frontend 502 Errors

```bash
# 1. Check if the frontend container is running
docker compose -f /opt/dentalos/docker-compose.prod.yml ps frontend

# 2. Check frontend logs
docker logs dentalos-frontend-prod --tail 100

# 3. Verify the backend is reachable from the frontend container
docker exec dentalos-frontend-prod wget -q --spider http://backend:8000/api/v1/health
echo $?   # 0 = success

# 4. Check Hetzner LB target health in the Cloud Console
# Load Balancers → <lb-name> → Targets → check health status

# 5. Verify Next.js can reach the API for SSR
docker logs dentalos-frontend-prod | grep -i "fetch failed\|ECONNREFUSED"
```

### Slow API Responses

```bash
# 1. Check p95 latency in Grafana (DentalOS Overview dashboard)

# 2. Identify slow database queries
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT mean_exec_time::int AS mean_ms, calls, left(query, 120) AS query
   FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# 3. Check Redis latency
redis-cli -a "$REDIS_PASSWORD" --latency-history -i 1

# 4. Look for N+1 queries in backend logs (enable DATABASE_ECHO=true temporarily)
docker exec dentalos-backend-prod bash -c "DATABASE_ECHO=true uvicorn app.main:app" 2>&1 | \
  grep -c "SELECT"  # high count indicates N+1

# 5. Check if workers are blocking the event loop (CPU-bound tasks)
docker stats dentalos-backend-prod --no-stream
```

### Migration Failures

```bash
# 1. Check the error output from the migration command
docker exec dentalos-backend-prod alembic upgrade head 2>&1

# 2. Common issues:
#    - Schema already has the object: migration was partially applied
#      -> Use alembic stamp to mark it as applied without re-running
docker exec dentalos-backend-prod alembic stamp <revision_id>

#    - Tenant schema not found
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tn_%';"

#    - Lock timeout: another process holds a table lock
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT pid, relation::regclass, mode, granted FROM pg_locks
   WHERE NOT granted;"
# Terminate the blocker: SELECT pg_terminate_backend(<pid>);

# 3. Never modify a deployed migration file. Create a new corrective migration.
```

### Worker Not Processing Jobs

```bash
# 1. Check queue depth and consumer count
docker exec dentalos-rabbitmq-prod rabbitmqctl list_queues \
  name messages consumers --vhost dentalos

# 2. Check worker logs for exceptions
docker logs dentalos-worker-notifications --tail 200 | grep -E "ERROR|Exception"

# 3. Verify RabbitMQ connection from the worker
docker exec dentalos-worker-notifications bash -c \
  "python -c \"import pika; pika.BlockingConnection(pika.URLParameters('$RABBITMQ_URL')); print('OK')\""

# 4. Restart workers
docker compose -f /opt/dentalos/docker-compose.prod.yml restart \
  worker-notifications worker-clinical worker-import worker-maintenance

# 5. If a specific message is causing a worker to crash (poison pill),
#    check the DLX queue and purge it after logging the payload for debugging
```

### Tenant Data Isolation Verification

Run this check after any migration or if there is a suspected cross-tenant leak:

```bash
# Verify search_path is always set per request (should see tn_* in all tenant queries)
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT pid, query, query_start
   FROM pg_stat_activity
   WHERE query LIKE '%SET search_path%' AND state = 'active';"

# Confirm no tenant tables exist in the public schema
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SELECT tablename FROM pg_tables
   WHERE schemaname = 'public'
     AND tablename IN ('patients','clinical_records','appointments','odontogram_teeth');"
# Expected: 0 rows

# Spot-check: patient count must be 0 when querying with wrong schema
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SET search_path TO tn_clinicaA, public;
   SELECT count(*) FROM patients;"
# Then verify tn_clinicaB has different count
psql -h 127.0.0.1 -U dentalos -d dentalos -c \
  "SET search_path TO tn_clinicaB, public;
   SELECT count(*) FROM patients;"
```

---

*For code-level issues, consult the specs in `specs/` and the error codes in
`specs/infra/error-handling.md`. For regulatory concerns (RIPS, Colombia Resolución 1888),
see `specs/compliance/`.*
