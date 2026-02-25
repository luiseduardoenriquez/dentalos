# Plan de Pagos (Payment Plan) — Frontend Spec

## Overview

**Screen:** Modal wizard for creating an installment payment plan against an invoice. Configures total amount, number of installments, frequency, and start date. Generates a preview schedule table with per-installment amounts that can be individually edited. Each installment can later be marked paid.

**Route:** Modal — no dedicated route. Triggered from `/billing/invoices/{id}`

**Priority:** Medium

**Backend Specs:** `specs/billing/B-10.md`, `specs/billing/B-11.md`

**Dependencies:** `specs/frontend/billing/invoice-detail.md`, `specs/frontend/billing/payment-record.md`

---

## User Flow

**Entry Points:**
- "Crear plan de pagos" button on invoice detail action panel (visible when invoice is sent/overdue and has balance)
- "Plan de pagos" option in invoice row actions menu

**Exit Points:**
- Save plan → modal closes, invoice detail shows plan section, success toast
- Cancel → modal closes, no changes
- Escape key → closes with discard confirmation if plan configured

**User Story:**
> As a receptionist or clinic_owner, I want to set up an installment plan for a patient's invoice so that I can offer flexible payment options and track each installment separately.

**Roles with access:** clinic_owner, receptionist

---

## Layout Structure

```
+------------------------------------------------+
|  Crear Plan de Pagos              [×]           |
+------------------------------------------------+
|  Factura FAC-0042  |  Saldo: $600.000          |
+------------------------------------------------+
|                                                |
|  PASO 1: Configuración del plan                |
|                                                |
|  Monto total del plan *                        |
|  [ $600.000                                ]   |
|                                                |
|  Número de cuotas *    Frecuencia *            |
|  [ 6          ]       [ Mensual ▼         ]   |
|                                                |
|  Fecha de primera cuota *                      |
|  [ 01/03/2026                              ]   |
|                                                |
|  [Generar cronograma]                          |
|                                                |
|  PASO 2: Cronograma generado (editable)        |
|  +--------------------------------------------+|
|  | # | Fecha       | Monto    | Estado         ||
|  |---|-------------|----------|----------------||
|  | 1 | 01/03/2026  | $100.000 | Pendiente      ||
|  | 2 | 01/04/2026  | $100.000 | Pendiente      ||
|  | 3 | 01/05/2026  | $100.000 | Pendiente      ||
|  | 4 | 01/06/2026  | $100.000 | Pendiente      ||
|  | 5 | 01/07/2026  | $100.000 | Pendiente      ||
|  | 6 | 01/08/2026  | $100.000 | Pendiente      ||
|  +--------------------------------------------+|
|  Total plan: $600.000 ✓                        |
|                                                |
|  [Cancelar]              [Guardar plan]        |
+------------------------------------------------+
```

**Sections:**
1. Modal header — title + close button
2. Invoice summary bar — invoice number, current balance
3. Step 1: Plan configuration — amount, installments, frequency, start date, generate button
4. Step 2: Editable schedule table — auto-generated installments; amounts individually editable
5. Plan total validation — shows sum of installments vs. plan total (green if equal, red if mismatch)
6. Action buttons — Cancel, Guardar plan

---

## UI Components

### Component 1: PlanConfigurationForm

**Type:** Inline form (not wizard steps — single scrollable modal)

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| total_amount | Currency input | Pre-filled with invoice balance; editable |
| num_installments | Number input (stepper) | 2–48, default 3 |
| frequency | Select dropdown | Semanal / Quincenal / Mensual |
| start_date | Date picker | Default: first day of next month |

**"Generar cronograma" button:**
- Appears after all 4 fields are filled
- On click: computes schedule client-side (equal installments, rounding remainder to last)
- Renders ScheduleTable below

### Component 2: ScheduleTable

**Type:** Editable table (useFieldArray)

**Columns:**

| Column | Header | Editable? | Notes |
|--------|--------|-----------|-------|
| # | Cuota | No | Sequential 1-N |
| date | Fecha | Yes (date picker per row) | Pre-computed, adjustable |
| amount | Monto | Yes (currency input) | Auto-distributed; sum must equal total |
| status | Estado | No | Always "Pendiente" on creation |

**Editing behavior:**
- Editing an amount in one row does NOT auto-adjust others (manual rebalancing)
- Sum validation: if sum ≠ total_amount, warning row appears: "La suma de cuotas ($X) no coincide con el total del plan ($Y). Ajusta los montos."
- Dates are pre-computed based on frequency; changing start date recalculates all dates (re-generate)

### Component 3: PlanTotalValidation

**Type:** Summary row below schedule table

**Content:**
- "Total del plan: $600.000" (gray)
- "Suma de cuotas: $600.000 ✓" (green if matches)
- "Suma de cuotas: $580.000 ✗ Diferencia: $20.000" (red if mismatch)
- Validation prevents saving if sum ≠ total_amount

### Component 4: InstallmentTracker (post-creation, on invoice detail)

**Type:** Read-only table with per-row "Pagar" button

**Note:** After plan is created and saved, the invoice detail page shows this component (not in the modal). Each installment row has a "Registrar pago" button that opens the PaymentRecordModal pre-filled with that installment's amount.

---

## Form Fields

| Field | Type | Required | Validation | Error Message | Default |
|-------|------|----------|------------|---------------|---------|
| total_amount | Currency | Yes | > 0 and ≤ invoice balance | "El monto no puede superar el saldo de la factura" | Invoice balance |
| num_installments | Integer | Yes | 2–48 | "Entre 2 y 48 cuotas" | 3 |
| frequency | Select | Yes | One of: weekly/biweekly/monthly | "Selecciona una frecuencia" | monthly |
| start_date | Date | Yes | ≥ today | "La fecha de inicio debe ser hoy o posterior" | Next 1st of month |
| installments[].amount | Currency | Yes | > 0 | "Monto inválido" | Auto-computed |
| installments[].date | Date | Yes | ≥ start_date | "Fecha inválida" | Auto-computed |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Create payment plan | `/api/v1/billing/invoices/{id}/payment-plans` | POST | `specs/billing/B-10.md` | — |
| List installments | `/api/v1/billing/payment-plans/{planId}/installments` | GET | `specs/billing/B-11.md` | 2min |
| Pay installment | `/api/v1/billing/installments/{id}/pay` | POST | `specs/billing/B-11.md` | — |

**Create Plan Request Body:**
```json
{
  "total_amount": 600000,
  "installments": [
    { "due_date": "2026-03-01", "amount": 100000 },
    { "due_date": "2026-04-01", "amount": 100000 }
  ]
}
```

### State Management

**Local State (useState):**
- `scheduleGenerated: boolean` — controls schedule table visibility
- `isSubmitting: boolean`

**Global State (Zustand):**
- None

**Server State (TanStack Query):**
- Mutation: `useMutation(createPaymentPlan)` — on success, invalidate `['invoice', invoiceId]`
- Toast: "Plan de pagos creado. N cuotas programadas."

**Form State (React Hook Form + useFieldArray):**
- Root fields: `total_amount`, `num_installments`, `frequency`, `start_date`
- `useFieldArray('installments')` — dynamic schedule rows

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Fill config + click "Generar" | Button click | Schedule computed client-side, table renders below | Table fades in (200ms) |
| Change start_date after generating | Date change | Schedule dates recalculate (amounts stay) | Table dates update |
| Edit installment amount | Type in row | Sum validation updates | PlanTotalValidation card changes color |
| Edit installment date | Change row date picker | Individual date changes | No auto-recalculation of other dates |
| Rebalance amounts | — | User must edit manually; no auto-rebalance | Warning if sum ≠ total |
| Save plan | Click "Guardar plan" | POST to API; modal closes | Spinner → success toast → invoice detail refreshes |
| Cancel | Click "Cancelar" | If schedule generated: confirmation dialog | Dialog: "¿Descartar el plan?" |

### Animations/Transitions

- Schedule table: fade in + slide down (200ms) after "Generar" clicked
- Total validation row: color transition (150ms) when amounts change
- Modal open/close: standard fade + scale

---

## Loading & Error States

### Loading State
- "Guardar plan" button: spinner + "Guardando..." text
- No skeleton (modal content is form-driven)

### Error State
- Inline Zod validation errors below each config field
- Sum mismatch: red warning row in PlanTotalValidation (prevents submission)
- API error: toast "Error al crear el plan. Intenta de nuevo."
- Network error: toast "Error de conexión."

### Empty State
- Schedule not yet generated: area below config shows placeholder "Configura los campos y haz clic en 'Generar cronograma' para ver el plan."

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Modal is full-screen bottom sheet. Config fields stack vertically. Schedule table horizontal scroll. Buttons full width stacked. |
| Tablet (640-1024px) | Modal 560px wide, centered. num_installments and frequency side-by-side. Schedule table full width. |
| Desktop (> 1024px) | Modal 600px wide, centered. Full layout as shown. |

---

## Accessibility

- **Focus order:** Amount → num installments → frequency → start date → "Generar" button → schedule table rows → Cancel → Guardar plan
- **Screen reader:** `role="dialog"` with `aria-labelledby`. PlanTotalValidation has `aria-live="polite"`. Schedule table: `role="table"` with proper headers and `aria-label="Cronograma de pagos"`.
- **Keyboard navigation:** Tab through config fields, Enter to generate. In schedule table, Tab through editable cells. Escape closes modal.
- **Color contrast:** Red mismatch warning and green match both meet WCAG AA.
- **Language:** All labels, errors, status values in es-419.

---

## Design Tokens

**Colors:**
- Schedule table header: `bg-gray-50`
- Plan total match: `text-green-600 font-semibold`
- Plan total mismatch: `text-red-600 font-semibold`
- Mismatch warning row: `bg-red-50 border border-red-200 rounded-lg p-3`
- Installment status badge: `bg-gray-100 text-gray-600` (Pendiente)
- Step headings: `text-sm font-semibold text-gray-700 uppercase tracking-wide`

**Typography:**
- Modal title: `text-lg font-bold text-gray-900`
- Config field labels: `text-sm font-medium text-gray-700`
- Schedule amounts: `text-sm font-mono`
- Total validation: `text-sm font-semibold`

**Spacing:**
- Modal padding: `p-6`
- Config fields gap: `gap-4`
- Between steps: `mt-6`
- Schedule table cell: `py-2 px-3`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod`
- `@tanstack/react-query`
- `@radix-ui/react-dialog`
- `lucide-react` — Calendar, CheckCircle, XCircle, AlertTriangle

**File Location:**
- Component: `src/components/billing/PaymentPlanModal.tsx`
- Sub-components: `src/components/billing/ScheduleTable.tsx`, `src/components/billing/PlanTotalValidation.tsx`
- Schema: `src/lib/schemas/payment-plan.schema.ts`
- Hook: `src/hooks/useCreatePaymentPlan.ts`

**Hooks Used:**
- `useFieldArray('installments')` — dynamic schedule rows
- `useWatch(['total_amount', 'num_installments', 'frequency', 'start_date'])` — generate button enable state
- `useMutation(createPaymentPlan)`

**Schedule Generation Logic:**
```typescript
function generateSchedule(total: number, n: number, freq: Frequency, startDate: Date) {
  const base = Math.floor(total / n);
  const remainder = total - base * n;
  return Array.from({ length: n }, (_, i) => ({
    date: addFrequency(startDate, freq, i),
    amount: i === n - 1 ? base + remainder : base,
  }));
}
```

---

## Test Cases

### Happy Path
1. Create 6-month plan
   - **Given:** Invoice balance $600.000
   - **When:** User sets total=$600.000, n=6, monthly, start=01/03/2026, clicks generate, saves
   - **Then:** 6 installments of $100.000 created; invoice detail shows plan section with 6 rows

2. Plan with uneven division (rounding)
   - **Given:** Balance $100.003
   - **When:** 3 installments, monthly
   - **Then:** Schedule shows $33.334, $33.334, $33.335 (remainder to last). Total validation green.

### Edge Cases
1. Edit installment amount causing mismatch
   - **Given:** Generated 3×$100.000 plan
   - **When:** User changes first installment to $150.000
   - **Then:** Total validation shows red "Suma $350.000 ≠ Plan $300.000". "Guardar plan" disabled.

### Error Cases
1. API error on save
   - **Given:** Network issue
   - **When:** User clicks "Guardar plan"
   - **Then:** Error toast. Modal stays open with data intact.

---

## Acceptance Criteria

- [ ] Config form: total amount, num installments (2-48), frequency (weekly/biweekly/monthly), start date
- [ ] "Generar cronograma" computes equal installments client-side (remainder to last)
- [ ] Editable schedule table: date + amount per installment
- [ ] Plan total validation: green if sum matches, red if mismatch (blocks save)
- [ ] Save creates plan via API; success toast + invoice detail refreshes
- [ ] Cancel with discard confirmation if schedule generated
- [ ] Invoice detail shows installment tracker table after plan created
- [ ] Each installment has "Registrar pago" button → opens PaymentRecordModal
- [ ] Responsive: bottom sheet mobile, centered modal tablet/desktop
- [ ] Accessibility: dialog role, aria-live on validation, keyboard navigation
- [ ] Spanish (es-419) labels and messages

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
