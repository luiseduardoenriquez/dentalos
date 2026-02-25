# Local Development Environment Spec

## Overview

**Feature:** Complete local development environment for DentalOS, including Docker Compose infrastructure stack, development servers, environment configuration, database seeding, and developer tooling.

**Domain:** infra

**Priority:** Critical

**Dependencies:** I-04 (database-architecture.md), I-05 (caching-strategy.md), I-06 (background-processing.md)

**Spec ID:** I-09

---

## 1. Docker Compose Stack

All infrastructure services run in Docker. Application servers (FastAPI, Next.js) run natively for hot-reload performance.

### 1.1 docker-compose.yml

```yaml
# docker-compose.yml
version: "3.9"

services:
  # ─── PostgreSQL 16 ──────────────────────────────────
  postgres:
    image: postgres:16-alpine
    container_name: dentalos-postgres
    environment:
      POSTGRES_DB: dentalos_dev
      POSTGRES_USER: dentalos
      POSTGRES_PASSWORD: dentalos_dev_password
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=es_CO.UTF-8"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/db/init.sql:/docker-entrypoint-initdb.d/01-init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dentalos -d dentalos_dev"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # ─── Redis 7 ────────────────────────────────────────
  redis:
    image: redis:7-alpine
    container_name: dentalos-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # ─── RabbitMQ 3 (with Management UI) ───────────────
  rabbitmq:
    image: rabbitmq:3-management-alpine
    container_name: dentalos-rabbitmq
    environment:
      RABBITMQ_DEFAULT_USER: dentalos
      RABBITMQ_DEFAULT_PASS: dentalos_dev_password
      RABBITMQ_DEFAULT_VHOST: dentalos
    ports:
      - "5672:5672"    # AMQP protocol
      - "15672:15672"  # Management UI
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "check_running"]
      interval: 30s
      timeout: 10s
      retries: 5
    restart: unless-stopped

  # ─── MinIO (S3-compatible Object Storage) ──────────
  minio:
    image: minio/minio:latest
    container_name: dentalos-minio
    environment:
      MINIO_ROOT_USER: dentalos_minio
      MINIO_ROOT_PASSWORD: dentalos_minio_password
    ports:
      - "9000:9000"    # S3 API
      - "9001:9001"    # MinIO Console
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 30s
      timeout: 10s
      retries: 5
    restart: unless-stopped

  # ─── MinIO Bucket Setup (init container) ───────────
  minio-setup:
    image: minio/mc:latest
    container_name: dentalos-minio-setup
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
        mc alias set local http://minio:9000 dentalos_minio dentalos_minio_password;
        mc mb --ignore-existing local/dentalos-dev;
        mc mb --ignore-existing local/dentalos-dev-xrays;
        mc mb --ignore-existing local/dentalos-dev-documents;
        mc mb --ignore-existing local/dentalos-dev-avatars;
        mc anonymous set download local/dentalos-dev-avatars;
        echo 'MinIO buckets created successfully';
      "

volumes:
  postgres_data:
  redis_data:
  rabbitmq_data:
  minio_data:
```

### 1.2 Service Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| PostgreSQL | `localhost:5432` | `dentalos` / `dentalos_dev_password` |
| Redis | `localhost:6379` | No auth (dev only) |
| RabbitMQ AMQP | `localhost:5672` | `dentalos` / `dentalos_dev_password` |
| RabbitMQ Management UI | `http://localhost:15672` | `dentalos` / `dentalos_dev_password` |
| MinIO S3 API | `http://localhost:9000` | `dentalos_minio` / `dentalos_minio_password` |
| MinIO Console | `http://localhost:9001` | `dentalos_minio` / `dentalos_minio_password` |

---

## 2. Application Development Servers

### 2.1 FastAPI Backend (port 8000)

```bash
# Start from backend/ directory
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info
```

**Hot reload** watches all `.py` files under `backend/app/`. Changes take effect in 1-2 seconds.

**Requirements:**

- Python 3.12+
- Virtual environment: `python -m venv .venv && source .venv/bin/activate`
- Dependencies: `pip install -r requirements.txt -r requirements-dev.txt`

### 2.2 Next.js Frontend (port 3000)

```bash
# Start from frontend/ directory
cd frontend
npm run dev
```

Runs `next dev` on port 3000 with Turbopack for fast compilation. Hot module replacement is automatic.

**Requirements:**

- Node.js 20 LTS
- Dependencies: `npm install`

### 2.3 Background Worker (optional for local development)

```bash
# Start RabbitMQ consumer worker
cd backend
python -m app.worker.main
```

For most local development, the worker is not needed. Queue jobs can be processed synchronously using the `SYNC_QUEUE=true` environment variable.

---

## 3. Environment Variables

### 3.1 .env.example (Backend)

```bash
# ═══════════════════════════════════════════════════════
# DentalOS Backend Environment Variables
# Copy this file to .env and fill in the values
# ═══════════════════════════════════════════════════════

# ─── Application ──────────────────────────────────────
ENVIRONMENT=development
DEBUG=true
APP_NAME=DentalOS
APP_VERSION=0.1.0
LOG_LEVEL=DEBUG
ALLOWED_HOSTS=localhost,127.0.0.1

# ─── Server ───────────────────────────────────────────
HOST=0.0.0.0
PORT=8000
WORKERS=1

# ─── Database (PostgreSQL) ────────────────────────────
DATABASE_URL=postgresql+asyncpg://dentalos:dentalos_dev_password@localhost:5432/dentalos_dev
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_ECHO=false

# ─── Redis ────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=300

# ─── RabbitMQ ─────────────────────────────────────────
RABBITMQ_URL=amqp://dentalos:dentalos_dev_password@localhost:5672/dentalos
SYNC_QUEUE=true

# ─── Authentication (JWT) ─────────────────────────────
SECRET_KEY=dev-secret-key-change-in-production-immediately
JWT_SECRET=dev-jwt-secret-change-in-production-immediately
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# ─── CORS ─────────────────────────────────────────────
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=true

# ─── File Storage (MinIO / S3) ────────────────────────
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=dentalos_minio
S3_SECRET_KEY=dentalos_minio_password
S3_BUCKET_NAME=dentalos-dev
S3_REGION=us-east-1
S3_PUBLIC_URL=http://localhost:9000/dentalos-dev

# ─── Email (development: console output) ─────────────
EMAIL_BACKEND=console
SENDGRID_API_KEY=
EMAIL_FROM_ADDRESS=noreply@dentalos.dev
EMAIL_FROM_NAME=DentalOS

# ─── WhatsApp Business API ───────────────────────────
WHATSAPP_ENABLED=false
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_VERIFY_TOKEN=

# ─── Twilio SMS ──────────────────────────────────────
TWILIO_ENABLED=false
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# ─── Sentry (Error Tracking) ─────────────────────────
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.0
SENTRY_ENVIRONMENT=development

# ─── Superadmin ───────────────────────────────────────
SUPERADMIN_EMAIL=admin@dentalos.dev
SUPERADMIN_PASSWORD=SuperAdmin123!Dev
```

### 3.2 .env.local (Frontend)

```bash
# ═══════════════════════════════════════════════════════
# DentalOS Frontend Environment Variables
# ═══════════════════════════════════════════════════════

NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=DentalOS
NEXT_PUBLIC_APP_ENV=development

# ─── S3 / MinIO (for direct upload signed URLs) ──────
NEXT_PUBLIC_S3_PUBLIC_URL=http://localhost:9000/dentalos-dev

# ─── Feature Flags ───────────────────────────────────
NEXT_PUBLIC_ENABLE_ODONTOGRAM_ANATOMIC=true
NEXT_PUBLIC_ENABLE_PATIENT_PORTAL=false
NEXT_PUBLIC_ENABLE_WHATSAPP=false
NEXT_PUBLIC_ENABLE_OFFLINE_MODE=false
```

---

## 4. Database Setup Scripts

### 4.1 Initial Database Setup

```sql
-- scripts/db/init.sql
-- Executed automatically by PostgreSQL container on first run

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- Trigram index for fuzzy search
CREATE EXTENSION IF NOT EXISTS "unaccent";      -- Accent-insensitive search (critical for Spanish)

-- Create the shared public tables
-- (Tenants, Plans, Superadmin users live in the public schema)
```

### 4.2 Migration Runner

```bash
# Run all migrations (public schema + all tenant schemas)
make db-migrate

# Create a new migration
make db-revision MSG="add_patient_allergies_field"

# Rollback one migration
make db-downgrade

# Show current migration state
make db-current
```

**Under the hood (Alembic):**

```bash
# Public schema migrations
cd backend && alembic -c alembic.ini upgrade head

# Tenant schema migrations (iterates all active tenants)
cd backend && python -m app.db.migrate_all_tenants
```

### 4.3 Seed CIE-10 and CUPS Dental Codes

```bash
make db-seed-catalogs
```

This runs `scripts/db/seed_catalogs.py`, which:

1. **CIE-10 dental codes** -- Inserts ~200 dental-relevant ICD-10 codes into `public.cie10_codes`:
   - K00-K14: Diseases of oral cavity, salivary glands, and jaws
   - S02.5: Fracture of tooth
   - Common dental diagnoses with Spanish descriptions

2. **CUPS dental codes** -- Inserts ~150 dental procedure codes into `public.cups_codes`:
   - 232xxx: Odontology procedures (Colombian CUPS classification)
   - Common procedures: restorations, extractions, endodontics, orthodontics, implants
   - Spanish descriptions and default prices in COP

3. **Medication catalog** -- Inserts ~50 dental-relevant medications into `public.medications`:
   - Analgesics (ibuprofeno, acetaminofen, diclofenaco)
   - Antibiotics (amoxicilina, clindamicina, metronidazol)
   - Anesthetics (lidocaina, mepivacaina, articaina)
   - Anti-inflammatories, antiseptics

### 4.4 Provision Test Tenant with Sample Data

```bash
make db-seed-dev
```

This runs `scripts/db/seed_dev_data.py`, which creates:

**Test Tenant:**

| Field | Value |
|-------|-------|
| Name | Clinica Dental Sonrisa |
| Slug | sonrisa |
| Country | CO (Colombia) |
| Plan | professional |
| Schema | `tenant_sonrisa` |
| Odontogram mode | classic |

**Test Users (one per role):**

| Role | Email | Password | Name |
|------|-------|----------|------|
| clinic_owner | owner@sonrisa.co | DevPassword123! | Carlos Martinez |
| doctor | doctor@sonrisa.co | DevPassword123! | Ana Ramirez |
| assistant | assistant@sonrisa.co | DevPassword123! | Laura Gomez |
| receptionist | receptionist@sonrisa.co | DevPassword123! | Pedro Diaz |

**Superadmin:**

| Email | Password |
|-------|----------|
| admin@dentalos.dev | SuperAdmin123!Dev |

### 4.5 Seed Sample Data (20 Patients)

The `make db-seed-dev` command also creates 20 sample patients with realistic Colombian data:

**Per patient, the seed generates:**

- Full demographic profile (names from `faker` with `es_CO` locale)
- Cedula de ciudadania (CC) document number
- Phone numbers (+57 format)
- Addresses in Colombian cities (Bogota, Medellin, Cali, Barranquilla)
- Random allergies (penicilina, latex, aspirina) for 30% of patients
- Medical conditions (diabetes, hipertension, asma) for 20% of patients

**Odontogram data (for 15 of 20 patients):**

- 3-8 random dental conditions per patient
- Conditions distributed across teeth using FDI notation
- Mix of: caries, resina, amalgama, corona, ausente, endodoncia, sellante
- Historical entries (backdated 1-12 months) to show timeline

**Appointments (40 total):**

- 20 past appointments (completed, various types)
- 10 upcoming appointments (scheduled, next 2 weeks)
- 5 cancelled appointments
- 5 no-show appointments

**Clinical records (30 total):**

- 10 examination records
- 8 evolution notes
- 7 procedure records (linked to CUPS codes)
- 5 diagnosis records (linked to CIE-10 codes)

**Treatment plans (5 total):**

- 2 active plans (with 3-5 items each, some completed)
- 1 completed plan
- 1 draft plan
- 1 plan with patient approval and signature

**Invoices (10 total):**

- 3 paid invoices
- 3 sent/pending invoices
- 2 draft invoices
- 2 overdue invoices
- Payment records for paid invoices

---

## 5. Makefile / Developer Commands

### 5.1 Makefile

```makefile
# ═══════════════════════════════════════════════════════
# DentalOS Development Makefile
# ═══════════════════════════════════════════════════════

.PHONY: help setup start stop restart logs status \
        db-migrate db-seed-catalogs db-seed-dev db-reset \
        backend frontend worker \
        test test-unit test-integration test-cov \
        lint format typecheck \
        clean

# ─── Help ─────────────────────────────────────────────
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}'

# ─── Setup (first time) ──────────────────────────────
setup: ## First-time setup: install deps, start infra, seed data
	@echo "Setting up DentalOS development environment..."
	docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	cd backend && python -m venv .venv && \
		source .venv/bin/activate && \
		pip install -r requirements.txt -r requirements-dev.txt
	cd frontend && npm install
	$(MAKE) db-migrate
	$(MAKE) db-seed-catalogs
	$(MAKE) db-seed-dev
	@echo ""
	@echo "Setup complete. Run 'make start' to start development servers."

# ─── Infrastructure ───────────────────────────────────
start: ## Start Docker infrastructure (postgres, redis, rabbitmq, minio)
	docker compose up -d
	@echo "Infrastructure started. Services:"
	@echo "  PostgreSQL:    localhost:5432"
	@echo "  Redis:         localhost:6379"
	@echo "  RabbitMQ:      localhost:5672  (UI: http://localhost:15672)"
	@echo "  MinIO:         localhost:9000  (Console: http://localhost:9001)"

stop: ## Stop Docker infrastructure
	docker compose down

restart: ## Restart Docker infrastructure
	docker compose restart

logs: ## Tail Docker container logs
	docker compose logs -f --tail=100

status: ## Show Docker container status
	docker compose ps

# ─── Database ─────────────────────────────────────────
db-migrate: ## Run all database migrations (public + tenant schemas)
	cd backend && alembic upgrade head
	cd backend && python -m app.db.migrate_all_tenants

db-revision: ## Create new migration (usage: make db-revision MSG="description")
	cd backend && alembic revision --autogenerate -m "$(MSG)"

db-downgrade: ## Rollback one migration
	cd backend && alembic downgrade -1

db-current: ## Show current migration state
	cd backend && alembic current

db-seed-catalogs: ## Seed CIE-10, CUPS codes, and medication catalog
	cd backend && python -m scripts.db.seed_catalogs

db-seed-dev: ## Seed test tenant, users, and 20 sample patients
	cd backend && python -m scripts.db.seed_dev_data

db-reset: ## Drop and recreate database (DESTRUCTIVE)
	@echo "WARNING: This will destroy all local data. Press Ctrl+C to cancel."
	@sleep 3
	docker compose exec postgres psql -U dentalos -c "DROP DATABASE IF EXISTS dentalos_dev;"
	docker compose exec postgres psql -U dentalos -c "CREATE DATABASE dentalos_dev;"
	$(MAKE) db-migrate
	$(MAKE) db-seed-catalogs
	$(MAKE) db-seed-dev
	@echo "Database reset complete."

# ─── Application Servers ─────────────────────────────
backend: ## Start FastAPI dev server (port 8000)
	cd backend && source .venv/bin/activate && \
		uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Start Next.js dev server (port 3000)
	cd frontend && npm run dev

worker: ## Start RabbitMQ background worker
	cd backend && source .venv/bin/activate && \
		python -m app.worker.main

dev: ## Start backend + frontend in parallel (requires tmux or run in separate terminals)
	@echo "Starting backend and frontend..."
	@echo "Run in separate terminals:"
	@echo "  Terminal 1: make backend"
	@echo "  Terminal 2: make frontend"

# ─── Testing ─────────────────────────────────────────
test: ## Run all backend tests
	cd backend && pytest

test-unit: ## Run backend unit tests only
	cd backend && pytest -m unit

test-integration: ## Run backend integration tests only
	cd backend && pytest -m integration

test-cov: ## Run tests with HTML coverage report
	cd backend && pytest --cov-report=html && open htmlcov/index.html

test-file: ## Run specific test file (usage: make test-file FILE=tests/path/to/test.py)
	cd backend && pytest $(FILE) -v

test-frontend: ## Run frontend Vitest tests
	cd frontend && npx vitest run

test-e2e: ## Run Playwright E2E tests
	cd frontend && npx playwright test

# ─── Code Quality ────────────────────────────────────
lint: ## Run all linters (backend + frontend)
	cd backend && ruff check app/ tests/
	cd frontend && npx eslint src/ --max-warnings 0

format: ## Auto-format all code
	cd backend && ruff format app/ tests/
	cd frontend && npx prettier --write "src/**/*.{ts,tsx,css}"

typecheck: ## Run type checkers
	cd backend && mypy app/ --config-file pyproject.toml
	cd frontend && npx tsc --noEmit

quality: lint typecheck ## Run all quality checks (lint + typecheck)

# ─── Cleanup ─────────────────────────────────────────
clean: ## Remove generated files, caches, volumes
	docker compose down -v
	rm -rf backend/.venv backend/__pycache__ backend/.pytest_cache backend/htmlcov
	rm -rf frontend/node_modules frontend/.next
	@echo "Clean complete. Run 'make setup' to start fresh."
```

---

## 6. scripts/dev.sh (Alternative to Makefile)

For developers who prefer a shell script over Make:

```bash
#!/usr/bin/env bash
# scripts/dev.sh -- DentalOS development helper
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
    echo -e "${CYAN}DentalOS Development Helper${NC}"
    echo ""
    echo "Usage: ./scripts/dev.sh <command>"
    echo ""
    echo "Commands:"
    echo "  setup          First-time setup"
    echo "  up             Start infrastructure"
    echo "  down           Stop infrastructure"
    echo "  backend        Start FastAPI server"
    echo "  frontend       Start Next.js server"
    echo "  seed           Seed database with dev data"
    echo "  reset-db       Reset database (destructive)"
    echo "  test           Run all tests"
    echo "  lint           Run linters"
    echo "  logs           Tail infrastructure logs"
    echo "  status         Show service status"
}

cmd_setup() {
    echo -e "${GREEN}Setting up DentalOS...${NC}"
    cd "$PROJECT_ROOT"
    docker compose up -d
    sleep 5

    echo -e "${YELLOW}Installing backend dependencies...${NC}"
    cd backend
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt -r requirements-dev.txt

    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    cd "$PROJECT_ROOT/frontend"
    npm install

    echo -e "${YELLOW}Running migrations...${NC}"
    cd "$PROJECT_ROOT"
    make db-migrate
    make db-seed-catalogs
    make db-seed-dev

    echo -e "${GREEN}Setup complete.${NC}"
}

cmd_up() {
    cd "$PROJECT_ROOT"
    docker compose up -d
    echo -e "${GREEN}Infrastructure started.${NC}"
    docker compose ps
}

cmd_down() {
    cd "$PROJECT_ROOT"
    docker compose down
    echo -e "${YELLOW}Infrastructure stopped.${NC}"
}

cmd_backend() {
    cd "$PROJECT_ROOT/backend"
    source .venv/bin/activate
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

cmd_frontend() {
    cd "$PROJECT_ROOT/frontend"
    npm run dev
}

cmd_seed() {
    cd "$PROJECT_ROOT"
    make db-seed-catalogs
    make db-seed-dev
    echo -e "${GREEN}Seed complete.${NC}"
}

cmd_reset_db() {
    echo -e "${RED}WARNING: This will destroy all local data.${NC}"
    read -p "Continue? (y/N) " confirm
    if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
        cd "$PROJECT_ROOT"
        make db-reset
    fi
}

case "${1:-}" in
    setup)      cmd_setup ;;
    up)         cmd_up ;;
    down)       cmd_down ;;
    backend)    cmd_backend ;;
    frontend)   cmd_frontend ;;
    seed)       cmd_seed ;;
    reset-db)   cmd_reset_db ;;
    test)       cd "$PROJECT_ROOT" && make test ;;
    lint)       cd "$PROJECT_ROOT" && make lint ;;
    logs)       cd "$PROJECT_ROOT" && docker compose logs -f --tail=100 ;;
    status)     cd "$PROJECT_ROOT" && docker compose ps ;;
    *)          usage ;;
esac
```

---

## 7. Git Hooks (pre-commit)

### 7.1 .pre-commit-config.yaml

```yaml
# .pre-commit-config.yaml
repos:
  # ─── Python (Backend) ──────────────────────────────
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
        files: ^backend/
      - id: ruff-format
        files: ^backend/

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        files: ^backend/app/
        args: [--config-file=backend/pyproject.toml]
        additional_dependencies:
          - pydantic>=2.0
          - sqlalchemy[asyncio]>=2.0
          - fastapi>=0.111

  # ─── JavaScript/TypeScript (Frontend) ──────────────
  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v9.0.0
    hooks:
      - id: eslint
        files: ^frontend/src/.*\.(ts|tsx)$
        args: [--max-warnings=0]
        additional_dependencies:
          - eslint@9
          - typescript
          - "@typescript-eslint/parser"
          - "@typescript-eslint/eslint-plugin"

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v4.0.0-alpha.8
    hooks:
      - id: prettier
        files: ^frontend/src/.*\.(ts|tsx|css|json)$

  # ─── General ───────────────────────────────────────
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: [--maxkb=500]
      - id: no-commit-to-branch
        args: [--branch, main]
      - id: detect-private-key

  # ─── Commit Message ────────────────────────────────
  - repo: https://github.com/compilerla/conventional-pre-commit
    rev: v3.2.0
    hooks:
      - id: conventional-pre-commit
        stages: [commit-msg]
        args: [feat, fix, refactor, docs, test, chore, ci, perf, style]
```

### 7.2 Installation

```bash
# Install pre-commit (included in requirements-dev.txt)
pip install pre-commit

# Install hooks
pre-commit install
pre-commit install --hook-type commit-msg

# Run all hooks on existing files (first time)
pre-commit run --all-files
```

### 7.3 Python Code Quality Configuration

```toml
# backend/pyproject.toml (relevant sections)

[tool.ruff]
target-version = "py312"
line-length = 100
src = ["app", "tests"]

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "ASYNC", # flake8-async
    "S",    # flake8-bandit (security)
]
ignore = [
    "S101",  # allow assert in tests
]

[tool.ruff.lint.isort]
known-first-party = ["app"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
plugins = ["pydantic.mypy", "sqlalchemy.ext.mypy.plugin"]

[[tool.mypy.overrides]]
module = ["tests.*"]
disallow_untyped_defs = false
```

---

## 8. Quick Start Guide

### 8.1 Prerequisites

| Tool | Version | Installation |
|------|---------|-------------|
| Docker + Docker Compose | >= 24.0 | [docker.com](https://docker.com) |
| Python | 3.12+ | `brew install python@3.12` or pyenv |
| Node.js | 20 LTS | `brew install node@20` or nvm |
| Git | >= 2.40 | `brew install git` |

### 8.2 First-Time Setup

```bash
# 1. Clone repository
git clone git@github.com:your-org/dentalos.git
cd dentalos

# 2. Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local

# 3. Run full setup (installs deps, starts infra, seeds data)
make setup

# 4. Start development servers (two terminals)
# Terminal 1:
make backend

# Terminal 2:
make frontend
```

### 8.3 Daily Development Workflow

```bash
# Start of day
make start              # Start Docker infrastructure
make backend            # Terminal 1: FastAPI on :8000
make frontend           # Terminal 2: Next.js on :3000

# During development
make test               # Run tests
make lint               # Check code quality
make db-migrate         # After model changes

# End of day
make stop               # Stop Docker infrastructure
```

### 8.4 Useful URLs (Local Development)

| Service | URL |
|---------|-----|
| Frontend (Next.js) | http://localhost:3000 |
| Backend API (FastAPI) | http://localhost:8000 |
| API Documentation (Swagger) | http://localhost:8000/docs |
| API Documentation (ReDoc) | http://localhost:8000/redoc |
| RabbitMQ Management | http://localhost:15672 |
| MinIO Console | http://localhost:9001 |

### 8.5 Test Login Credentials

| Role | Email | Password |
|------|-------|----------|
| Superadmin | admin@dentalos.dev | SuperAdmin123!Dev |
| Clinic Owner | owner@sonrisa.co | DevPassword123! |
| Doctor | doctor@sonrisa.co | DevPassword123! |
| Assistant | assistant@sonrisa.co | DevPassword123! |
| Receptionist | receptionist@sonrisa.co | DevPassword123! |

---

## 9. Troubleshooting

### 9.1 Common Issues

| Problem | Solution |
|---------|----------|
| Port 5432 already in use | Stop local PostgreSQL: `brew services stop postgresql` or change port in `docker-compose.yml` |
| Docker containers fail to start | Run `docker compose down -v && docker compose up -d` to reset volumes |
| Alembic migration conflicts | Run `make db-reset` (destructive) or resolve migration head manually |
| Frontend cant reach backend | Verify CORS_ORIGINS in `.env` includes `http://localhost:3000` |
| MinIO bucket not found | Run `docker compose up minio-setup` to recreate buckets |
| Python import errors | Ensure virtual environment is active: `source backend/.venv/bin/activate` |
| Node module errors | Delete and reinstall: `rm -rf frontend/node_modules && cd frontend && npm install` |
| Redis connection refused | Check container: `docker compose ps redis`. Restart: `docker compose restart redis` |

### 9.2 Useful Debug Commands

```bash
# Check all container health
docker compose ps

# Connect to PostgreSQL directly
docker compose exec postgres psql -U dentalos -d dentalos_dev

# List tenant schemas
docker compose exec postgres psql -U dentalos -d dentalos_dev -c \
  "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%';"

# Flush Redis cache
docker compose exec redis redis-cli FLUSHALL

# View RabbitMQ queues
docker compose exec rabbitmq rabbitmqctl list_queues

# Check MinIO buckets
docker compose exec minio mc ls local/
```

---

## Out of Scope

This spec explicitly does NOT cover:

- Production deployment configuration (see `infra/deployment-architecture.md`)
- Staging or preview environment setup
- CI/CD pipeline configuration (see `infra/testing-setup.md` for GitHub Actions)
- Database backup and restore procedures (see `infra/backup-disaster-recovery.md`)
- SSL/TLS certificate setup for local development
- IDE-specific configuration (VSCode, PyCharm, WebStorm)
- Mobile device testing setup for responsive development
- VPN or network configuration for team development

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
