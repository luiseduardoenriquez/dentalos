# DentalOS — Software Architect Memory

## Project Snapshot
- Multi-tenant dental SaaS (Colombia first, schema-per-tenant)
- ~80% backend implemented; Sprint 23-24 GAP features added
- All 371 specs written; active coding in progress

## Key Module Locations
- `app/core/database.py` — `engine`, `AsyncSessionLocal`, `get_db()`, `get_tenant_db()`
- `app/core/security.py` — `hash_password()`, `verify_password()`, `create_access_token()`
- `app/core/config.py` — `settings` (pydantic-settings, reads `.env`)
- `app/core/tenant.py` — `TenantContext`, `get_current_tenant_or_raise()`, `validate_schema_name()`
- `app/core/error_codes.py` — all error code constants (CashRegisterErrors, ExpenseErrors, etc.)
- `app/core/exceptions.py` — `DentalOSError`, `ResourceNotFoundError`, `ResourceConflictError`, `BusinessValidationError`
- `app/models/base.py` — `PublicBase` (schema="public"), `TenantBase` (no schema), `TimestampMixin`, `UUIDPrimaryKeyMixin`
- `app/models/tenant/__init__.py` — registry of all tenant-scoped models (imports + `__all__`)
- `app/api/v1/router.py` — main router; new routers added at bottom in sprint comment blocks

## Critical Patterns

### Model Pattern
- Inherit: `UUIDPrimaryKeyMixin, TimestampMixin, TenantBase` (MRO order matters)
- Money: INTEGER cents (never floats). Timestamps: TIMESTAMPTZ UTC.
- Soft delete: `is_active BOOLEAN server_default="true"` + `deleted_at TIMESTAMPTZ nullable`
- Use `server_default` (string literals) for DB-level defaults, not Python `default`
- Relationships: `relationship(back_populates=...)` with `selectinload` for eager loading in async

### Service Pattern
- Stateless class + module-level singleton: `some_service = SomeService()`
- All methods: `async def method(self, *, db: AsyncSession, ...) -> dict[str, Any]`
- Private `_to_dict()` helpers: serialize UUID fields as `str(obj.uuid_field)`
- Private `_get_X()` raises `ResourceNotFoundError(error=..., resource_name=...)`
- Business conflicts: `DentalOSError(error=..., message=..., status_code=409)`
- Logger: `logging.getLogger("dentalos.{domain}")` — NEVER log PHI

### Router Pattern
- `require_permission("{domain}:{read|write}")` on every endpoint
- Return `ResponseSchema(**service_result)` — never return raw dicts from handlers
- `GET /resource` list endpoints return paginated dict; router wraps in response schema

### Schema Pattern
- Request: `BaseModel` with `Field` constraints
- Response: `ConfigDict(from_attributes=True)` for ORM compat; UUID → `str`

## Cross-Service Dependency Pattern
To avoid circular imports when service A calls service B:
- Import service B **inside the method body** (deferred import), not at module level
- Example: `expense_service.create_expense()` imports `cash_register_service` inside the function

## Alembic Setup
- Two separate alembic configs: `alembic_public/` and `alembic_tenant/`
- Tenant migrations: `alembic -c alembic_tenant/alembic.ini upgrade head -x schema=tn_xxx`
- `provision_tenant_schema()` in `tenant_service.py` wraps this in a subprocess call

## Architecture Notes
- `TenantBase` has no hardcoded schema — relies on `SET search_path` per session
- `PublicBase` has `metadata = MetaData(schema="public")`
- `UserTenantMembership.user_id` is plain UUID with NO DB-level FK (cross-schema constraint)
- JWT RS256 keys must exist at `keys/private.pem` and `keys/public.pem` before app start

## Sprint 23-24 VP-06/VP-07 Implementation (2026-03-02)
- VP-06 EPS: `models/tenant/eps_verification.py` (EPSVerification), `schemas/eps_verification.py`, `services/eps_verification_service.py`, `api/v1/patients/eps_router.py`
- VP-07 RETHUS: `schemas/rethus.py`, `services/rethus_verification_service.py`, `api/v1/users/rethus_router.py`
- User model: added `rethus_number`, `rethus_verification_status`, `rethus_verified_at` columns
- User schemas: RETHUS fields added to both `UserProfileResponse` and `UserTeamMemberResponse`
- Integration adapters: `integrations/rethus/service.py` + `mock_service.py` (datos.gov.co Socrata)
- ADRES adapter was already fully implemented; only needed `mock_service.py` reference
- RETHUS `RETHUSVerificationResponse.full_name` is the PHI field (NOT `professional_name`)
- EPS cache key: `dentalos:{tid_short}:eps:verification:{patient_id}` TTL 24h
- Still needed: Alembic migration for eps_verifications + rethus columns, FE badges, auto-verify worker

## Sprint 23-24 GAP-02/GAP-03 Implementation (2026-03-02)
- GAP-02 Cash Register: `models/cash_register.py`, `schemas/cash_register.py`, `services/cash_register_service.py`, `api/v1/cash_registers/router.py`
- GAP-03 Expenses: `models/expense.py`, `schemas/expense.py`, `services/expense_service.py`, `api/v1/expenses/router.py`
- Profit/Loss: `GET /expenses/profit-loss` queries `Payment.amount` grouped by `payment_method` for revenue side
- Auto-register hook: when creating an expense, if a cash register is open, a `CashMovement(type="expense")` is auto-created

## Sprint 23-24 Frontend Implementation (2026-03-02)

### Pages created (batch 1 — cash/expenses/analytics)
- `/billing/cash-register/page.tsx` — Open/close register, KPI cards, CashMovementList, DailyReport toggle
- `/billing/expenses/page.tsx` — Expense list with category/date filters + Pagination
- `/billing/expenses/new/page.tsx` — ExpenseForm wrapper page
- `/billing/tasks/page.tsx` — TaskQueue with type+status filters (covers GAP-05, GAP-06, GAP-08 FE items)
- `/analytics/profit-loss/page.tsx` — P&L with date range, 3 KPI cards, horizontal bar charts, summary table

### Components created batch 1 (frontend/components/billing/)
- `CashMovementList.tsx`, `CashRegisterPanel.tsx`, `DailyReport.tsx`, `ExpenseForm.tsx`, `TaskQueue.tsx`, `PaymentQRDisplay.tsx`

### Pages created (batch 2 — VP-06/07/08/20/05 FE)
- `(dashboard)/settings/postop-templates/page.tsx` — PostopTemplateList + PostopTemplateForm in-page create/edit flow
- `(dashboard)/settings/referral-program/page.tsx` — Program stats, toggle on/off, conversion rate progress bar
- `portal/referral/page.tsx` — ReferralShareCard + rewards link + "how it works" steps
- `portal/referral/rewards/page.tsx` — Rewards history table; pending balance banner; mobile+desktop layouts
- `portal/invoices/[id]/pay/page.tsx` — Invoice detail + NequiPayButton + DaviplataPayButton side by side; handles paid/cancelled states
- `portal/postop/page.tsx` — Expandable post-op instruction list; channel badge; procedure type badge

### Components created batch 2
- `components/patients/EPSVerificationBadge.tsx` — Inline badge; useMutation trigger; TanStack Query with `setQueryData` on success
- `components/users/RETHUSBadge.tsx` — RETHUS status badge; inline RETHUS number input when none exists; 4 status colors
- `components/portal/ReferralShareCard.tsx` — Code display + clipboard copy + WhatsApp share + QR via api.qrserver.com + stats
- `components/portal/NequiPayButton.tsx` — POST to `/portal/invoices/{id}/pay/nequi`; renders `PaymentQRDisplay` on success; exports `PaymentQRDisplay` for re-use
- `components/portal/DaviplataPayButton.tsx` — Same as Nequi; imports `PaymentQRDisplay` from NequiPayButton (shared); Davivienda red #E11D48
- `components/postop/PostopTemplateForm.tsx` — Controlled form; inline validation; create+edit mode; exports `PostopTemplate` type
- `components/postop/SendPostopButton.tsx` — "ghost" and "default" variants; 2.5s success state; reusable across procedure completion screens
- `components/postop/PostopTemplateList.tsx` — Click-outside menu ref; deactivate mutation; default star indicator; inactive section collapsible

### Analytics layout: P&G tab added to `/analytics/layout.tsx`

### Frontend patterns confirmed
- `TableWrapper` always wraps `<Table>` (horizontal scroll)
- `import * as React from "react"` (star import)
- `useQuery` staleTime 15_000–60_000ms; `retry: false` when 404 is expected
- `useMutation` + `queryClient.invalidateQueries` for write-then-refresh
- Portal pages live under `portal/` (not `(portal)/`) — confirmed from existing layout.tsx
- QR codes: use `api.qrserver.com` public API (no npm dep needed)
- `PaymentQRDisplay` re-exported from NequiPayButton.tsx so Daviplata can import it without circular dep

## Sprint 25-26 VP-14 Multi-Currency Billing (2026-03-03)
- Integration adapters: `integrations/exchange_rates/` — base.py (ABC), banco_republica.py (prod), mock_service.py
- Banco de la Republica: datos.gov.co Socrata API, X-App-Token auth, field "valor" for TRM rate
- Mock rates: USD/COP=4150, EUR/COP=4520, MXN/COP=240 (derive cross via COP)
- Schema: `schemas/exchange_rate.py` — CurrencyInfo, ExchangeRateResponse, ExchangeRatesListResponse
- Service: `services/exchange_rate_service.py` — singleton `exchange_rate_service`, auto-fallback prod->mock
- Cache: `dentalos:shared:exchange_rates:{from}_{to}` TTL 3600s, uses `get_cached`/`set_cached` from `app.core.cache`
- Router: `api/v1/billing/exchange_rate_router.py` — GET /billing/exchange-rates, billing:read
- Config: `exchange_rate_api_url`, `exchange_rate_api_key` in settings
- Error codes: ExchangeRateErrors in error_codes.py (already existed)
- Supported currencies: COP, USD, EUR, MXN

## Common Pitfalls
- `backend/app/models/tenant/__init__.py` is modified by linters between reads — use Bash write fallback when Edit tool fails
- `selectinload` must come from `sqlalchemy.orm` for eager loading in async sessions
- `func.date()` for date-casting TIMESTAMPTZ to DATE in WHERE clauses (PostgreSQL)
- Close register endpoint: resolve register_id from `get_current()` rather than asking client to pass it
