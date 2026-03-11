#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# DentalOS — First Deployment Script
#
# Run AFTER setup-server.sh. Builds images, starts services, runs migrations,
# creates the first tenant and admin user.
#
# Usage:
#   cd /opt/dentalos
#   sudo bash scripts/deploy/first-deploy.sh
#
# Prerequisites:
#   - setup-server.sh has been run
#   - .env has been filled in (especially API keys)
#   - JWT keys exist in keys/
#   - docker-compose.prod.yml is in the current directory
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/dentalos}"
cd "${DEPLOY_DIR}"

echo "═══════════════════════════════════════════════════"
echo "  DentalOS — First Deployment"
echo "  Directory: ${DEPLOY_DIR}"
echo "═══════════════════════════════════════════════════"

# ── Preflight checks ─────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    echo "ERROR: .env not found. Run setup-server.sh first."
    exit 1
fi

if [ ! -f "docker-compose.prod.yml" ]; then
    echo "ERROR: docker-compose.prod.yml not found."
    echo "Copy it from the repo: cp /path/to/repo/docker-compose.prod.yml ."
    exit 1
fi

if [ ! -f "keys/private.pem" ]; then
    echo "ERROR: JWT keys not found in keys/. Run setup-server.sh first."
    exit 1
fi

# Check for CHANGE_ME values in critical keys
if grep -q "OPENAI_API_KEY=CHANGE_ME" .env || grep -q "ANTHROPIC_API_KEY=CHANGE_ME" .env; then
    echo "WARNING: AI API keys not set in .env — AI features will not work."
    echo "         Edit .env and set OPENAI_API_KEY and ANTHROPIC_API_KEY."
    echo ""
    read -rp "Continue anyway? [y/N] " response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# ── 1. Copy JWT keys into backend build context ─────────────────────────────
echo "[1/8] Preparing JWT keys for backend image..."
if [ -d "backend/keys" ]; then
    cp -f keys/private.pem backend/keys/private.pem
    cp -f keys/public.pem backend/keys/public.pem
else
    echo "    backend/keys/ not found — keys will be mounted at runtime."
fi

# ── 2. Build Docker images ──────────────────────────────────────────────────
echo "[2/8] Building Docker images (this may take a few minutes)..."
docker compose -f docker-compose.prod.yml build --parallel

# ── 3. Start infrastructure services first ───────────────────────────────────
echo "[3/8] Starting infrastructure services..."
docker compose -f docker-compose.prod.yml up -d postgres redis rabbitmq minio

# Wait for all infra to be healthy
echo "    Waiting for services to be healthy..."
for service in postgres redis rabbitmq minio; do
    echo -n "    ${service}: "
    retries=0
    until docker compose -f docker-compose.prod.yml ps "${service}" | grep -q "healthy"; do
        retries=$((retries + 1))
        if [ ${retries} -gt 30 ]; then
            echo "FAILED (timeout after 60s)"
            echo "Check logs: docker compose -f docker-compose.prod.yml logs ${service}"
            exit 1
        fi
        sleep 2
        echo -n "."
    done
    echo " OK"
done

# ── 4. Run database migrations ──────────────────────────────────────────────
echo "[4/8] Running database migrations..."
# Public schema migrations
docker compose -f docker-compose.prod.yml run --rm --no-deps backend \
    alembic -c alembic_public/alembic.ini upgrade head

# Tenant schema migrations
docker compose -f docker-compose.prod.yml run --rm --no-deps backend \
    alembic -c alembic_tenant/alembic.ini upgrade head

echo "    Migrations complete."

# ── 5. Create MinIO bucket ──────────────────────────────────────────────────
echo "[5/8] Creating S3 bucket in MinIO..."
# Source credentials from .env
MINIO_USER=$(grep MINIO_ROOT_USER .env | cut -d= -f2)
MINIO_PASS=$(grep MINIO_ROOT_PASSWORD .env | cut -d= -f2)
BUCKET_NAME=$(grep S3_BUCKET_NAME .env | cut -d= -f2)
BUCKET_NAME="${BUCKET_NAME:-dentalos-prod}"

# Use MinIO client inside the minio container
docker compose -f docker-compose.prod.yml exec minio \
    mc alias set local http://localhost:9000 "${MINIO_USER}" "${MINIO_PASS}" 2>/dev/null || true
docker compose -f docker-compose.prod.yml exec minio \
    mc mb "local/${BUCKET_NAME}" 2>/dev/null || echo "    Bucket already exists."

echo "    Bucket '${BUCKET_NAME}' ready."

# ── 6. Start application services ───────────────────────────────────────────
echo "[6/8] Starting backend, worker, and frontend..."
docker compose -f docker-compose.prod.yml up -d backend worker frontend

# Wait for backend health
echo -n "    Backend health: "
retries=0
until curl -sf http://127.0.0.1:8000/api/v1/health > /dev/null 2>&1; do
    retries=$((retries + 1))
    if [ ${retries} -gt 30 ]; then
        echo "FAILED"
        echo "Check logs: docker compose -f docker-compose.prod.yml logs backend"
        exit 1
    fi
    sleep 2
    echo -n "."
done
echo " OK"

# ── 7. Seed initial data ────────────────────────────────────────────────────
echo "[7/8] Seeding initial data (plans, catalogs, admin user, beta tenant)..."
docker compose -f docker-compose.prod.yml exec backend \
    python scripts/seed_dev.py

echo "    Seed complete."

# ── 8. Verify all services ──────────────────────────────────────────────────
echo "[8/8] Verifying all services..."
echo ""

ALL_OK=true

# Check each service
for service in postgres redis rabbitmq minio backend worker frontend; do
    status=$(docker compose -f docker-compose.prod.yml ps "${service}" --format "{{.Status}}" 2>/dev/null || echo "not found")
    if echo "${status}" | grep -qi "up"; then
        echo "    [OK] ${service}: ${status}"
    else
        echo "    [!!] ${service}: ${status}"
        ALL_OK=false
    fi
done

echo ""

# API health check
if curl -sf http://127.0.0.1:8000/api/v1/health > /dev/null 2>&1; then
    echo "    [OK] API health check passed"
else
    echo "    [!!] API health check failed"
    ALL_OK=false
fi

# Frontend check
if curl -sf http://127.0.0.1:3000 > /dev/null 2>&1; then
    echo "    [OK] Frontend responding"
else
    echo "    [!!] Frontend not responding"
    ALL_OK=false
fi

# Worker check
WORKER_LOGS=$(docker compose -f docker-compose.prod.yml logs worker --tail 5 2>/dev/null)
if echo "${WORKER_LOGS}" | grep -qi "started\|running\|connected"; then
    echo "    [OK] Worker running"
else
    echo "    [??] Worker status unclear — check: docker compose logs worker"
fi

echo ""
echo "═══════════════════════════════════════════════════"
if [ "${ALL_OK}" = true ]; then
    echo "  Deployment successful!"
else
    echo "  Deployment completed with warnings."
fi
echo ""
echo "  URLs:"
echo "    Frontend: http://127.0.0.1:3000"
echo "    API:      http://127.0.0.1:8000/api/v1/health"
echo "    RabbitMQ: http://127.0.0.1:15672 (via SSH tunnel)"
echo "    MinIO:    http://127.0.0.1:9001 (via SSH tunnel)"
echo ""
echo "  Demo credentials (password: DemoPass1):"
echo "    owner@demo.dentalos.co       — clinic_owner"
echo "    doctor@demo.dentalos.co      — doctor"
echo "    admin@dentalos.app           — superadmin (AdminPass1)"
echo ""
echo "  Next steps:"
echo "    1. Configure SSL: sudo certbot --nginx -d app.dentalos.co"
echo "    2. Set real API keys in .env (OPENAI, ANTHROPIC, SENDGRID, SENTRY)"
echo "    3. Create production tenant & users (replace demo data)"
echo "═══════════════════════════════════════════════════"
