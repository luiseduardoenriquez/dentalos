# DentalOS Code Reviewer Memory

## Project Conventions (verified)
- All money in integer cents (COP). No floats in DB. `Numeric` only for exchange rates.
- UUID PKs via `gen_random_uuid()`, never auto-increment.
- Soft-delete: `is_active + deleted_at`. Clinical data NEVER hard-deleted (Res. 1888).
- Pydantic v2 schemas: `ConfigDict(from_attributes=True)` on response models.
- Services return plain `dict[str, Any]` — routers wrap in schema classes.
- Async SQLAlchemy 2.0 everywhere. Raw SQL prohibited except approved cases.
- Deferred imports inside methods are the project's accepted pattern for circular dependency avoidance (membership, convenio, referral, loyalty services all do this).
- `selectin` lazy loading is explicitly set on parent→children relationships (e.g., `Invoice.items`, `TreatmentPlan.items`). The reverse (child→parent) defaults to lazy and can trigger greenlet errors in async context.

## Recurring Issues Found
- **Schema/dict key mismatch**: `_invoice_to_dict` returns extra formatted keys (`subtotal_formatted`, `total_formatted`, `amount_paid_formatted`, `balance_formatted`, `currency_code`, `exchange_rate`, `exchange_rate_date`) that are absent from `InvoiceResponse`. Pydantic v2 ignores extra keys silently, so this does NOT raise an error — it just silently drops data the frontend could use.
- **Lazy relationship access in async context**: `TreatmentPlanItem.plan` has no `lazy=` override, so it defaults to lazy loading. Accessing `item.plan` inside an async method (`get_billable_items`) without an explicit join or `selectin` load will trigger a `MissingGreenlet` / `greenlet_spawn` error at runtime in SQLAlchemy 2.0 async mode.
- **Wrong error code reuse**: `BillingErrors.INVOICE_ALREADY_PAID` was reused for the "treatment plan item already invoiced" conflict (409). Should use a more specific code or `BillingErrors.QUOTATION_NOT_FOUND` was also reused for treatment plan not found.
- **Payment method constraint gap**: `Payment` model CHECK constraint only allows `cash, card, transfer, other`. Nequi/Daviplata/Mercado Pago are separate integrations but if they ever pass method strings directly this will fail.

## Key Model Field References
- `TreatmentPlan`: `doctor_id`, `patient_id`, `status`, `is_active`, `items` (selectin)
- `TreatmentPlanItem`: `treatment_plan_id`, `cups_code`, `cups_description`, `tooth_number`, `estimated_cost`, `actual_cost`, `priority_order`, `status`, `plan` (lazy default)
- `InvoiceItem`: `treatment_plan_item_id` (UUID, nullable), `doctor_id` (UUID, nullable) — added in migration 023
- `CashMovement`: `register_id`, `type`, `amount_cents`, `payment_method`, `reference_id`, `reference_type`, `description`, `recorded_by` — all fields matched correctly in payment_service
- `Payment`: `currency` column exists (String(3), server_default COP)

## Migration Chain
- 022_ai_usage_logs → 023_invoice_item_treatment_link (verified chain is correct)
- 15 tenant migrations total as of sprint 23-24 notes; 023 is the newest

## Architecture Notes
- Billing discount waterfall: membership (2a) → convenio (2b) → referral (4a) → loyalty (4b)
- Sequential invoice numbers: `FAC-{YYYY}-{NNNNN}` — uses COUNT with LIKE filter (not sequence, so has race condition under concurrent load)
- Lazy overdue detection: status flips happen on read, not via background job
- Cash register bridge in `record_payment` — correctly reads `CashRegister.status == "open"`
