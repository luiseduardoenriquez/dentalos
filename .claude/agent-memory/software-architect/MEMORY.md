# DentalOS — Software Architect Memory

## Project Snapshot
- Multi-tenant dental SaaS (Colombia first, schema-per-tenant)
- Sprint 1-2 (M1) implementation in progress
- All 371 specs written; coding started

## Key Module Locations
- `app/core/database.py` — `engine`, `AsyncSessionLocal`, `get_db()`, `get_tenant_db()`
- `app/core/security.py` — `hash_password()`, `verify_password()`, `create_access_token()`
- `app/core/config.py` — `settings` (pydantic-settings, reads `.env`)
- `app/core/tenant.py` — `TenantContext`, `get_current_tenant_or_raise()`, `validate_schema_name()`
- `app/models/base.py` — `PublicBase` (schema="public"), `TenantBase` (no schema), `TimestampMixin`, `UUIDPrimaryKeyMixin`
- `app/services/tenant_service.py` — `provision_tenant_schema()`, `generate_schema_name()`, `generate_slug()`

## ORM Model Inventory (current)
Public schema models: `Plan`, `Tenant`, `UserTenantMembership`
Tenant schema models: `User`, `UserSession`, `UserInvite`
Patient model: NOT YET — lands in M3 sprint

## Critical Patterns
- All IDs: UUID via `server_default=func.gen_random_uuid()` + `default=uuid.uuid4`
- Money: INTEGER cents (never floats)
- Timestamps: TIMESTAMPTZ, always UTC
- Soft delete: `is_active + deleted_at` columns (clinical data never hard-deleted)
- Tenant schema naming: `tn_{8 hex chars}` (`tn_demodent` used for dev fixed name)
- search_path switching: `SET search_path TO {schema_name}, public` per session

## Alembic Setup
- Two separate alembic configs: `alembic_public/` and `alembic_tenant/`
- Tenant migrations invoked with: `alembic -c alembic_tenant/alembic.ini upgrade head -x schema=tn_xxx`
- `provision_tenant_schema()` in `tenant_service.py` wraps this in a subprocess call

## Scripts
- `scripts/generate_keys.py` — generates RS256 key pair (`keys/private.pem`, `keys/public.pem`)
- `scripts/seed_dev.py` — seeds dev DB with demo plans, tenant, users, memberships, patients

## seed_dev.py Design Decisions
- Fixed schema name `tn_demodent` for repeatability in local dev (unlike prod which uses random hex)
- All seed steps are idempotent (check-before-insert)
- Patients seeded with raw SQL since `Patient` ORM model not yet implemented (M3)
- Patient insert gracefully skips if `patients` table doesn't exist yet
- Reuses `provision_tenant_schema` pattern (CREATE SCHEMA + alembic subprocess)
- `engine.dispose()` called at end to allow clean process exit
- Password: `DemoPass1` for all demo users

## Architecture Notes
- `TenantBase` has no hardcoded schema — relies entirely on `SET search_path` per session
- `PublicBase` has `metadata = MetaData(schema="public")` — tables always land in public
- `UserTenantMembership.user_id` is a plain UUID column with NO DB-level FK (cross-schema)
- `Tenant.owner_user_id` starts NULL and is backfilled after user creation
- JWT RS256 keys must exist at `keys/private.pem` and `keys/public.pem` before app start
