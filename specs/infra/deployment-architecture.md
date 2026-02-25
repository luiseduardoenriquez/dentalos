# Deployment Architecture Spec

> **Spec ID:** I-14
> **Status:** Draft
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Hetzner Cloud deployment architecture for DentalOS. Defines server topology, load balancing, CI/CD pipeline, blue-green deployment, rollback procedures, SSL certificates, and network security groups. The initial architecture targets a lean, cost-effective setup for the Colombia launch that can scale horizontally as the user base grows.

**Domain:** infra

**Priority:** Critical

**Dependencies:** I-15 (monitoring-observability), I-16 (backup-DR), I-10 (security-policy), I-11 (audit-logging)

---

## 1. Infrastructure Overview

### Server Topology (Production)

```
Internet
    │
    ▼
[Hetzner Load Balancer LB11]  ← SSL termination, $6/month
    │
    ├──────────────────────────┐
    ▼                          ▼
[App Server 1 — CX41]     [App Server 2 — CX41]   ← €17/month each
FastAPI + Gunicorn          FastAPI + Gunicorn
Next.js (SSR)              Next.js (SSR)
ClamAV daemon              ClamAV daemon
    │                          │
    └──────────┬───────────────┘
               │ Hetzner Private Network (10.0.0.0/16)
               │
    ┌──────────┼──────────────────────┐
    │          │                      │
    ▼          ▼                      ▼
[DB Server]  [Worker Server]    [Redis Server]
Managed PG   CX31 (€11/mo)     CX21 (€6/mo)
CPX31        RabbitMQ           Redis 7.x
(€19/mo)     Celery Workers      (or Managed Redis)
             ClamAV update cron
```

### Server Specifications

| Server | Type | vCPU | RAM | SSD | Cost/Month | Purpose |
|--------|------|------|-----|-----|-----------|---------|
| App Server 1 | CX41 | 8 | 16GB | 160GB | €17 | Primary app server |
| App Server 2 | CX41 | 8 | 16GB | 160GB | €17 | Secondary app server |
| Worker Server | CPX31 | 4 | 8GB | 160GB | €13 | Queue workers, background tasks |
| PostgreSQL | CPX31 Managed | 2 | 8GB | 80GB | €19 | Managed PostgreSQL 16 |
| Redis | CX21 | 2 | 4GB | 40GB | €6 | Redis 7.x (or Managed €15/mo) |
| Load Balancer | LB11 | — | — | — | €6 | Hetzner Load Balancer |

**Total monthly infrastructure cost: ~€78/month (~$85 USD)**

**Object Storage:** Hetzner Object Storage ~€5/TB/month (starts near-zero)

### Hetzner Datacenter: Falkenstein (FSN1), Germany

Primary for Europe proximity to LATAM traffic routes (lower latency than US East for Colombia/Mexico). Future: add FSN1 for Europe, consider HEL1 for lower latency to specific markets.

---

## 2. Network Architecture

### Private Network

All internal services communicate over Hetzner's private network (10.0.0.0/16). No public exposure for database, Redis, or RabbitMQ.

```
Private Network: 10.0.0.0/16
├── 10.0.0.1  — App Server 1
├── 10.0.0.2  — App Server 2
├── 10.0.0.10 — Worker Server
├── 10.0.0.20 — PostgreSQL (Hetzner Managed)
├── 10.0.0.30 — Redis
└── 10.0.0.40 — (future expansion)
```

### Firewall Rules (Hetzner Firewall)

**Load Balancer (public-facing):**

| Direction | Protocol | Port | Source | Description |
|-----------|---------|------|--------|-------------|
| Inbound | TCP | 80 | 0.0.0.0/0 | HTTP (redirect to HTTPS) |
| Inbound | TCP | 443 | 0.0.0.0/0 | HTTPS |
| Inbound | ICMP | — | 0.0.0.0/0 | Ping for health checks |

**App Servers (restricted to LB and private network):**

| Direction | Protocol | Port | Source | Description |
|-----------|---------|------|--------|-------------|
| Inbound | TCP | 8000 | LB + private | FastAPI Gunicorn |
| Inbound | TCP | 3000 | LB + private | Next.js SSR |
| Inbound | TCP | 22 | Ops IP only | SSH (bastion IP only) |
| Inbound | All | — | 10.0.0.0/16 | Private network |
| Outbound | All | — | 0.0.0.0/0 | Egress (API calls, S3) |

**Database Server (private network only):**

| Direction | Protocol | Port | Source | Description |
|-----------|---------|------|--------|-------------|
| Inbound | TCP | 5432 | 10.0.0.0/16 | PostgreSQL |

**Redis (private network only):**

| Direction | Protocol | Port | Source | Description |
|-----------|---------|------|--------|-------------|
| Inbound | TCP | 6379 | 10.0.0.0/16 | Redis |

---

## 3. Application Stack per Server

### App Server Process Layout

```
App Server (CX41)
├── systemd services:
│   ├── dentalos-api.service
│   │   └── gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
│   │       --bind 0.0.0.0:8000 --timeout 120 --graceful-timeout 60
│   ├── dentalos-frontend.service
│   │   └── node /app/frontend/server.js (Next.js standalone build)
│   │       PORT=3000
│   └── clamav.service (clamd daemon)
├── nginx (reverse proxy + static files)
│   ├── Upstream: localhost:8000 (FastAPI)
│   └── Upstream: localhost:3000 (Next.js)
└── certbot (SSL renewal)
```

### Gunicorn Configuration

```python
# gunicorn.conf.py
workers = 4               # 2 * vCPU + 1 (CX41 has 8 vCPU → 4 workers for headroom)
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:8000"
timeout = 120
graceful_timeout = 60
keepalive = 5
max_requests = 1000       # Restart workers periodically to prevent memory leaks
max_requests_jitter = 200
preload_app = True
accesslog = "/var/log/dentalos/gunicorn-access.log"
errorlog = "/var/log/dentalos/gunicorn-error.log"
loglevel = "info"
```

### Worker Server Process Layout

```
Worker Server (CPX31)
├── systemd services:
│   ├── dentalos-worker-email.service
│   │   └── python -m app.workers.email_worker --concurrency 4
│   ├── dentalos-worker-whatsapp.service
│   │   └── python -m app.workers.whatsapp_worker --concurrency 4
│   ├── dentalos-worker-sms.service
│   │   └── python -m app.workers.sms_worker --concurrency 2
│   ├── dentalos-worker-dian.service
│   │   └── python -m app.workers.dian_worker --concurrency 2
│   ├── dentalos-worker-files.service
│   │   └── python -m app.workers.file_worker --concurrency 4
│   ├── dentalos-worker-general.service
│   │   └── python -m app.workers.general_worker --concurrency 8
│   ├── rabbitmq.service (RabbitMQ 3.x)
│   └── freshclam.service (ClamAV updates, runs every 6h)
└── cron jobs:
    ├── 0 3 * * * → pg_basebackup (WAL archival, see I-16)
    ├── 0 7 * * * → check_resolution_expiry (DIAN)
    └── 0 * * * * → renew_expiring_watch_channels (Google Calendar)
```

---

## 4. Load Balancer Configuration

### Hetzner LB11

```yaml
# Hetzner Load Balancer configuration (via Hetzner Cloud API / Terraform)
name: dentalos-lb
location: fsn1
algorithm:
  type: round_robin
health_check:
  protocol: http
  port: 8000
  path: /api/v1/health
  interval: 15        # seconds
  timeout: 10         # seconds
  healthy_threshold: 2
  unhealthy_threshold: 3
services:
  - protocol: http
    listen_port: 80
    destination_port: 8000
    health_check: true
    proxyprotocol: true
  - protocol: https
    listen_port: 443
    destination_port: 8000
    health_check: true
    proxyprotocol: true
    ssl:
      certificate_id: [Let_Encrypt_cert_ID]
      redirect_http: true
targets:
  - type: server
    server_id: [app-server-1-id]
  - type: server
    server_id: [app-server-2-id]
```

### Health Check Endpoint

```python
from fastapi import APIRouter
from app.db.connection import check_db_health
from app.core.redis import check_redis_health
from app.integrations.rabbitmq import check_rabbitmq_health
import time

router = APIRouter()

@router.get("/api/v1/health")
async def health_check():
    """
    Load balancer health check endpoint.
    Returns 200 if all critical services are healthy.
    Returns 503 if any critical service is degraded.
    """
    start = time.time()

    checks = {}
    overall_healthy = True

    # Database check
    db_ok = await check_db_health()
    checks["database"] = "healthy" if db_ok else "degraded"
    if not db_ok:
        overall_healthy = False

    # Redis check
    redis_ok = await check_redis_health()
    checks["redis"] = "healthy" if redis_ok else "degraded"

    # RabbitMQ check (non-critical — don't fail health check)
    rmq_ok = await check_rabbitmq_health()
    checks["rabbitmq"] = "healthy" if rmq_ok else "degraded"

    duration_ms = round((time.time() - start) * 1000)

    status_code = 200 if overall_healthy else 503
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "checks": checks,
        "uptime": get_uptime_seconds(),
        "version": settings.APP_VERSION,
        "duration_ms": duration_ms,
    }, status_code
```

---

## 5. CI/CD Pipeline (GitHub Actions)

### Pipeline Overview

```
Developer pushes to feature branch
    │
    ▼
Pull Request opened
    │
    ▼
CI Pipeline:
├── Lint (ruff, eslint)
├── Type check (mypy, tsc)
├── Unit tests (pytest, jest)
├── Integration tests (pytest + test DB)
├── Security scan (pip-audit, npm audit, trivy)
└── Build Docker images

PR merged to main
    │
    ▼
CD Pipeline:
├── Build production Docker images
├── Push to Hetzner Registry (registry.hetzner.cloud)
├── Deploy to staging
├── Run smoke tests against staging
└── Deploy to production (blue-green)
```

### Docker Image Structure

```dockerfile
# Dockerfile.api
FROM python:3.12-slim AS base
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    clamav-daemon \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash dentalos
USER dentalos

EXPOSE 8000
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app.main:app"]
```

```yaml
# .github/workflows/deploy.yml (excerpt)
name: Deploy Production

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build API image
        run: |
          docker build -t registry.hetzner.cloud/dentalos/api:${{ github.sha }} \
            -f Dockerfile.api .

      - name: Push to registry
        run: |
          echo "${{ secrets.HETZNER_REGISTRY_TOKEN }}" | \
            docker login registry.hetzner.cloud -u ${{ secrets.HETZNER_REGISTRY_USER }} --password-stdin
          docker push registry.hetzner.cloud/dentalos/api:${{ github.sha }}
          # Also tag as latest
          docker tag registry.hetzner.cloud/dentalos/api:${{ github.sha }} \
            registry.hetzner.cloud/dentalos/api:latest
          docker push registry.hetzner.cloud/dentalos/api:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.APP_SERVER_1_IP }}
          username: deploy
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            /opt/dentalos/scripts/deploy.sh ${{ github.sha }}
```

---

## 6. Blue-Green Deployment

### Deployment Script

```bash
#!/bin/bash
# /opt/dentalos/scripts/deploy.sh
# Blue-green deployment for zero-downtime updates

set -euo pipefail

NEW_IMAGE_TAG="${1:-latest}"
REGISTRY="registry.hetzner.cloud/dentalos"
CURRENT_SLOT=$(cat /opt/dentalos/current_slot || echo "blue")

if [ "$CURRENT_SLOT" == "blue" ]; then
    NEW_SLOT="green"
    NEW_PORT=8001
    OLD_PORT=8000
else
    NEW_SLOT="blue"
    NEW_PORT=8000
    OLD_PORT=8001
fi

echo "Deploying ${NEW_IMAGE_TAG} to ${NEW_SLOT} slot (port ${NEW_PORT})"

# 1. Pull new image
docker pull "${REGISTRY}/api:${NEW_IMAGE_TAG}"

# 2. Start new container on alternate port
docker run -d \
    --name "dentalos-api-${NEW_SLOT}" \
    --env-file /opt/dentalos/.env \
    -p "127.0.0.1:${NEW_PORT}:8000" \
    --restart=unless-stopped \
    "${REGISTRY}/api:${NEW_IMAGE_TAG}"

# 3. Wait for health check to pass (up to 60 seconds)
for i in $(seq 1 12); do
    sleep 5
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:${NEW_PORT}/api/v1/health)
    if [ "$STATUS" == "200" ]; then
        echo "Health check passed on ${NEW_SLOT}"
        break
    fi
    if [ $i -eq 12 ]; then
        echo "Health check failed — rolling back"
        docker stop "dentalos-api-${NEW_SLOT}"
        docker rm "dentalos-api-${NEW_SLOT}"
        exit 1
    fi
done

# 4. Switch nginx upstream to new slot
sed -i "s/proxy_pass http:\/\/127.0.0.1:${OLD_PORT}/proxy_pass http:\/\/127.0.0.1:${NEW_PORT}/" \
    /etc/nginx/sites-enabled/dentalos
nginx -s reload

# 5. Wait for old connections to drain (30 seconds)
sleep 30

# 6. Stop old container
OLD_CONTAINER="dentalos-api-${CURRENT_SLOT}"
if docker ps -q -f name="${OLD_CONTAINER}" | grep -q .; then
    docker stop "${OLD_CONTAINER}"
    docker rm "${OLD_CONTAINER}"
fi

# 7. Update current slot tracker
echo "${NEW_SLOT}" > /opt/dentalos/current_slot

# 8. Clean old images (keep last 3)
docker images "${REGISTRY}/api" --format "{{.Tag}}" | \
    sort -r | tail -n +4 | \
    xargs -I {} docker rmi "${REGISTRY}/api:{}" 2>/dev/null || true

echo "Deployment complete: ${NEW_IMAGE_TAG} running on ${NEW_SLOT} (port ${NEW_PORT})"
```

---

## 7. Rollback Procedure

### Automatic Rollback

During deployment, if the health check fails, the deploy script automatically removes the new container and the old slot continues serving traffic.

### Manual Rollback

To manually roll back to a previous image:

```bash
# Get recent image tags from Hetzner registry
docker images registry.hetzner.cloud/dentalos/api --format "{{.Tag}}: {{.CreatedAt}}"

# Roll back to specific tag
/opt/dentalos/scripts/deploy.sh abc123def456  # Previous commit SHA
```

### Database Rollback

For schema migrations that need rollback:

```bash
# List applied migrations
alembic history --verbose

# Downgrade one step
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade abc123
```

Migrations are written to be reversible. All column drops use a soft delete approach first (rename + keep for one release cycle) before permanent removal.

---

## 8. SSL Certificate Management

### Let's Encrypt via Certbot

SSL certificates are managed at the Hetzner Load Balancer level:

```bash
# Hetzner supports Let's Encrypt certificates natively via CLI:
hcloud certificate create \
    --name dentalos-ssl \
    --type managed \
    --domain app.dentalos.app \
    --domain portal.dentalos.app \
    --domain api.dentalos.app

# Renewal is automatic via Hetzner (managed certificates auto-renew)
```

For custom tenant domains (future feature), certificates are provisioned per domain via Let's Encrypt wildcard with DNS-01 challenge.

---

## 9. Nginx Configuration

```nginx
# /etc/nginx/sites-enabled/dentalos
# Nginx as reverse proxy on app servers

upstream dentalos_api {
    server 127.0.0.1:8000;  # Active slot (updated by deploy script)
    keepalive 16;
}

upstream dentalos_frontend {
    server 127.0.0.1:3000;
    keepalive 8;
}

server {
    listen 8000;
    server_name _;

    # API
    location /api/ {
        proxy_pass http://dentalos_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_read_timeout 120s;
        proxy_send_timeout 60s;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # Webhooks (no timeout on incoming webhooks)
    location /api/v1/webhooks/ {
        proxy_pass http://dentalos_api;
        proxy_read_timeout 30s;
        client_max_body_size 10m;
    }

    # Frontend
    location / {
        proxy_pass http://dentalos_frontend;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static files cached by nginx
    location /_next/static/ {
        proxy_pass http://dentalos_frontend;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## 10. Database Connection Pooling

### PgBouncer (on App Servers)

With 2 app servers × 4 Gunicorn workers × 10 SQLAlchemy pool connections = 80 potential DB connections. Managed PostgreSQL (Hetzner CPX31) supports ~200 connections. PgBouncer is used to pool connections:

```ini
# /etc/pgbouncer/pgbouncer.ini
[databases]
dentalos = host=10.0.0.20 port=5432 dbname=dentalos

[pgbouncer]
listen_port = 5432
listen_addr = 127.0.0.1
auth_type = scram-sha-256
pool_mode = transaction       # Transaction pooling for async FastAPI
max_client_conn = 200
default_pool_size = 25        # Connections to actual DB
min_pool_size = 5
reserve_pool_size = 5
server_idle_timeout = 600
```

### SQLAlchemy Async Pool Settings

```python
# app/db/connection.py
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,   # Recycle connections every 30 minutes
    pool_pre_ping=True,  # Test connections before use
    echo=settings.DEBUG,
)
```

---

## 11. Scaling Strategy

### Vertical Scaling (Short Term)

When a single app server is at >70% CPU or >80% RAM:
1. Upgrade CX41 → CX51 (16 vCPU, 32GB RAM, €34/month)
2. Increase Gunicorn workers to 8

### Horizontal Scaling (Medium Term)

The current setup supports horizontal scaling by:
1. Adding more CX41 app servers to the load balancer (no code changes required)
2. Redis must be upgraded to Hetzner Managed Redis or Redis Cluster
3. PostgreSQL connection pool managed via PgBouncer (already in place)

### Auto-Scaling (Future)

Hetzner does not support native auto-scaling. For auto-scaling capability, migrate to Kubernetes (Hetzner K8s via Hetzner Cloud Controller Manager) when the tenant count justifies it.

---

## 12. Environment Variables Management

All secrets managed via systemd unit file `EnvironmentFile`:

```bash
# /opt/dentalos/.env (mode 0600, owned by dentalos user)
DATABASE_URL=postgresql+asyncpg://user:pass@10.0.0.20:5432/dentalos
REDIS_URL=redis://10.0.0.30:6379/0
RABBITMQ_URL=amqp://user:pass@10.0.0.10:5672/
JWT_SECRET_KEY=...
# etc.
```

---

## Out of Scope

- Kubernetes orchestration — added when scale requires it
- Terraform IaC for infrastructure provisioning — future improvement
- Multi-region deployment — single region for v1 Colombia launch
- CDN for static assets — Next.js static files served by Nginx; CDN added if latency becomes an issue
- Hetzner Bare Metal servers — VPS is sufficient for current scale

---

## Acceptance Criteria

**This architecture is complete when:**

- [ ] Both app servers behind load balancer respond to health checks
- [ ] Blue-green deployment script runs without downtime (verified with load test)
- [ ] SSL certificate auto-renews via Hetzner managed certificate
- [ ] Firewall rules block direct DB/Redis access from internet
- [ ] PgBouncer connection pooling reduces DB connection count
- [ ] GitHub Actions CI/CD deploys to both app servers on main push
- [ ] Rollback to previous image tag completes within 5 minutes
- [ ] Health check endpoint returns `status: healthy` with db/redis/rabbitmq checks

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
