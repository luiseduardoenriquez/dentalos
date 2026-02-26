# DentalOS — Developer Setup

Get the backend + frontend running locally in 5 commands.

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker | 24+ | [docker.com](https://docs.docker.com/get-docker/) |
| Python | 3.12+ | [python.org](https://www.python.org/) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 20+ | [nodejs.org](https://nodejs.org/) |

## Quick Start

```bash
# 1. Start Docker + install Python deps
make setup

# 2. Copy and configure .env (defaults work out of the box)
cp backend/.env.example backend/.env

# 3. Generate keys, run migrations, seed demo data
make onboard

# 4. Start backend (terminal 1)
make backend

# 5. Start frontend (terminal 2)
make frontend
```

Backend: http://localhost:8000 | API docs: http://localhost:8000/docs
Frontend: http://localhost:3000

## Demo Credentials

All accounts use password: `DemoPass1`

| Email | Role |
|-------|------|
| owner@demo.dentalos.co | clinic_owner |
| doctor@demo.dentalos.co | doctor |
| assistant@demo.dentalos.co | assistant |
| receptionist@demo.dentalos.co | receptionist |

Tenant: **Clinica Demo Dental** (`tn_demodent`)

## Useful Commands

```bash
make help                # Show all available targets
make db-reset            # Full wipe: destroys volumes, re-migrates, re-seeds
make db-migrate          # Run public schema migrations only
make db-migrate-tenant SCHEMA=tn_demodent  # Run tenant migrations for a specific schema
make db-seed             # Re-run seed script (idempotent)
make test                # Run all backend tests
make lint                # Lint backend code
make quality             # Lint + typecheck
```

## Architecture Note

DentalOS uses **two Alembic migration chains**:

1. **Public** (`alembic/`) — shared tables: `tenants`, `plans`, `user_tenant_memberships`, catalogs
2. **Tenant** (`alembic_tenant/`) — per-clinic tables: `users`, `patients`, `appointments`, etc.

The seed script (`scripts/seed_dev.py`) handles tenant schema creation and runs tenant migrations automatically. For manual tenant migration, use `make db-migrate-tenant SCHEMA=tn_xxx`.

## Troubleshooting

**`make onboard` fails with connection error**
Docker services aren't ready. Run `docker compose ps` to check, then `docker compose up -d` and wait a few seconds.

**Port already in use**
Kill the conflicting process: `lsof -ti:8000 | xargs kill -9` (backend) or `:3000` (frontend).

**Schema out of sync**
Run `make db-reset` to wipe everything and start fresh. This destroys all data.

**Key generation fails**
Ensure the `backend/keys/` directory exists: `mkdir -p backend/keys`
