# Registrar Pago (Record Payment) — Frontend Spec

## Overview

**Screen:** Modal dialog for recording a payment against an invoice. Pre-fills with outstanding balance. Supports full and partial payments, multiple payment methods, and shows a live running balance preview. Triggered from invoice detail page.

**Route:** Modal — no dedicated route. Triggered from `/billing/invoices/{id}`

**Priority:** High

**Backend Specs:** `specs/billing/B-07.md`

**Dependencies:** `specs/frontend/billing/invoice-detail.md`

---

## User Flow

**Entry Points:**
- "Registrar pago" button on invoice detail action panel
- "Registrar pago" option in invoice row actions menu (from invoice list)

**Exit Points:**
- Submit payment → modal closes, invoice detail refreshes (balance + payments list update), success toast
- Cancel → modal closes, no changes
- Escape key → modal closes (with discard confirmation if amount entered)

**User Story:**
> As a receptionist, I want to record a payment against an invoice so that the outstanding balance is updated and the payment method is tracked.

**Roles with access:** clinic_owner, receptionist

---

## Layout Structure

```
+------------------------------------------+
|  Registrar Pago          [×]              |
+------------------------------------------+
|  Factura: FAC-0042  |  Total: $130.000   |
|  Ya pagado: $50.000 |  Saldo: $80.000    |
+------------------------------------------+
|                                           |
|  Monto a pagar *                          |
|  [   $80.000                          ]   |
|                                           |
|  ○ Pago parcial (permite monto menor)     |
|                                           |
|  Método de pago *                         |
|  [ Efectivo ▼                         ]   |
|                                           |
|  Fecha de pago *                          |
|  [ 25/02/2026                         ]   |
|                                           |
|  Número de referencia                     |
|  [ (opcional)                         ]   |
|                                           |
|  Notas internas                           |
|  [ (opcional)                         ]   |
|                                           |
|  +--------------------------------------+ |
|  | Nuevo saldo:  $0                     | |
|  | Estado factura: Pagada ✓             | |
|  +--------------------------------------+ |
|                                           |
|  [Cancelar]          [Registrar pago]     |
+------------------------------------------+
```

**Sections:**
1. Modal header — title "Registrar Pago" + close button
2. Invoice summary bar — invoice number, total, already paid, current balance
3. Amount field — pre-filled with balance; partial payment toggle
4. Payment method dropdown — cash, card, transfer, insurance, other
5. Date field — defaults to today
6. Reference number field — optional (required for transfer/card)
7. Internal notes field — optional
8. Running balance preview — live card showing new balance + resulting invoice status
9. Action buttons — Cancel, Registrar pago

---

## UI Components

### Component 1: InvoiceSummaryBar

**Type:** Summary card (read-only, inside modal)

**Content per row:**
- Factura: `FAC-0042` (monospace)
- Total facturado: `$130.000`
- Ya pagado: `$50.000` (green)
- Saldo pendiente: `$80.000` (red if > 0)

### Component 2: AmountInput

**Type:** Currency input

**Behavior:**
- Pre-filled with current outstanding balance
- If `isPartialPayment = false`, field is pre-filled and user can edit but saving validates amount ≤ balance
- If `isPartialPayment = true`, field allows any amount > 0 and ≤ balance
- Real-time updates BalancePreviewCard as user types

### Component 3: PartialPaymentToggle

**Type:** Checkbox + label

**Label:** "Pago parcial (el monto puede ser menor al saldo pendiente)"

**Default:** unchecked (full payment assumed)

**Behavior:** When checked, amount field allows any value ≤ balance. When unchecked, amount auto-fills full balance and is locked (still editable if user wants to correct).

### Component 4: PaymentMethodDropdown

**Type:** Select / Combobox

**Options:**

| Value | Label | Icon |
|-------|-------|------|
| cash | Efectivo | Banknote |
| card | Tarjeta débito/crédito | CreditCard |
| transfer | Transferencia bancaria | ArrowRightLeft |
| insurance | Seguro médico | Shield |
| other | Otro | MoreHorizontal |

**Default:** cash (most common in dental clinics)

**Behavior:** Selecting "Transferencia bancaria" or "Tarjeta" makes reference number field required.

### Component 5: BalancePreviewCard

**Type:** Info card (live computed, `aria-live="polite"`)

**Content:**
- "Nuevo saldo pendiente: $XX.000" (red if > 0, green if 0)
- "Estado resultante: Pagada ✓" (green) or "Enviada / Pago parcial" (blue)

**Updates:** Real-time as user changes amount field.

---

## Form Fields

| Field | Type | Required | Validation | Error Message | Placeholder / Default |
|-------|------|----------|------------|---------------|----------------------|
| amount | Currency number | Yes | > 0 and ≤ balance | "El monto debe ser mayor a $0 y no superar el saldo ($X)" | Balance amount |
| payment_method | Select | Yes | One of: cash/card/transfer/insurance/other | "Selecciona un método de pago" | "Efectivo" (default) |
| payment_date | Date | Yes | Valid date, not in future | "Fecha inválida" | Today (default) |
| reference_number | Text | Conditional (required if card/transfer) | Max 100 chars | "Número de referencia requerido para este método" | "" |
| notes | Textarea | No | Max 300 chars | — | "Notas internas (opcional)..." |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Record payment | `/api/v1/billing/invoices/{id}/payments` | POST | `specs/billing/B-07.md` | — |

**Request Body:**
```json
{
  "amount": 80000,
  "payment_method": "cash",
  "payment_date": "2026-02-25",
  "reference_number": null,
  "notes": null
}
```

**Response:** Updated invoice object with new status + payments array.

### State Management

**Local State (useState):**
- `isPartialPayment: boolean` — partial payment toggle
- `isSubmitting: boolean` — prevent double-submit
- `computedBalance: number` — live calculated balance for preview card

**Global State (Zustand):**
- None

**Server State (TanStack Query):**
- Mutation: `useMutation(recordPayment)`
- On success: `invalidateQueries(['invoice', invoiceId])` and `['invoice-payments', invoiceId]`
- Toast: "Pago de $XX.000 registrado correctamente"

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Open modal | "Registrar pago" button | Modal slides up (mobile) or appears centered (desktop) | Overlay + focus trap |
| Change amount | Type in amount field | Balance preview card updates in real time | Live number update with aria-live |
| Toggle partial payment | Click checkbox | Amount field behavior changes | Checkbox state, field lock/unlock |
| Change payment method | Select dropdown | Reference field required/optional state changes | Field required indicator updates |
| Submit payment | Click "Registrar pago" | POST payment, modal closes | Button spinner → success toast + invoice detail refreshes |
| Cancel | Click "Cancelar" or "×" | If amount was entered: confirmation dialog. If empty: close immediately | Dialog: "¿Descartar el pago sin guardar?" |
| Escape key | Key press | Same as cancel behavior | — |

### Animations/Transitions

- Modal open: fade in overlay + scale up modal (200ms)
- Modal close: reverse animation (150ms)
- Balance preview card: smooth number transition (150ms CSS transition on number)
- Error messages: fade in below field (150ms)

---

## Loading & Error States

### Loading State
- Submit button: shows spinner + "Registrando..." text, disabled state
- No skeleton needed (modal content is simple form)

### Error State
- Inline validation errors below each field
- API error (400): toast "Error al registrar el pago. Verifica los datos."
- Concurrency error (409 — invoice already fully paid): toast "Esta factura ya fue pagada en su totalidad." + modal closes
- Network error: toast "Error de conexión. Intenta de nuevo." + button returns to normal state

### Empty State
- Not applicable (modal always has invoice context)

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Modal is bottom sheet (slides up from bottom, 90% viewport height, scrollable). Buttons stack vertically (full width). |
| Tablet (640-1024px) | Modal centered, 480px wide. Standard layout. |
| Desktop (> 1024px) | Modal centered, 500px wide. Standard layout. |

**Tablet priority:** High — receptionists record payments on tablets at front desk.

---

## Accessibility

- **Focus order:** Modal opens → focus trapped inside. First focus: amount input. Tab: amount → partial toggle → method dropdown → date → reference → notes → Cancel → Registrar pago.
- **Screen reader:** `role="dialog"` with `aria-labelledby="modal-title"` and `aria-describedby="invoice-summary"`. Balance preview has `aria-live="polite"`. Success/error toasts have `aria-live="assertive"`.
- **Keyboard navigation:** Tab through all fields. Escape closes modal (with confirmation if dirty). Enter submits form if focus is on submit button.
- **Color contrast:** All text WCAG AA. Red balance amount and green confirmed amounts both meet contrast ratios.
- **Language:** All labels, errors, confirmations in es-419.

---

## Design Tokens

**Colors:**
- Modal overlay: `bg-black/50`
- Modal background: `bg-white rounded-2xl`
- Invoice summary bar: `bg-gray-50 rounded-xl p-4`
- Balance pending (>0): `text-red-600 font-bold`
- Balance zero: `text-green-600 font-bold`
- Preview card: `bg-blue-50 rounded-lg p-4 border border-blue-100`
- Partial toggle: standard checkbox with `text-primary-600`

**Typography:**
- Invoice number in summary: `font-mono text-sm font-medium`
- Amount input: `text-xl font-semibold` (large, prominent)
- Preview balance: `text-lg font-bold`
- Field labels: `text-sm font-medium text-gray-700`

**Spacing:**
- Modal padding: `p-6`
- Field gap: `space-y-4`
- Summary bar: `mb-5`
- Button row: `mt-6 flex gap-3 justify-end`

**Border Radius:**
- Modal: `rounded-2xl`
- Amount input: `rounded-lg` (larger than standard — prominent)
- Preview card: `rounded-lg`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod` — form validation
- `@radix-ui/react-dialog` — modal with focus trap + overlay
- `@tanstack/react-query` — mutation
- `lucide-react` — Banknote, CreditCard, ArrowRightLeft, Shield, X

**File Location:**
- Component: `src/components/billing/PaymentRecordModal.tsx`
- Schema: `src/lib/schemas/payment.schema.ts`
- Hook: `src/hooks/useRecordPayment.ts`
- API: `src/lib/api/billing.ts`

**Hooks Used:**
- `useAuth()` — tenant context
- `useMutation(recordPayment)` — payment submission
- `useWatch(['amount'])` — live balance preview computation

**Balance Preview Logic:**
```typescript
const computedBalance = useMemo(() => {
  const entered = parseFloat(amountValue) || 0;
  return Math.max(0, invoice.balance - entered);
}, [amountValue, invoice.balance]);

const resultingStatus = computedBalance === 0 ? 'paid'
  : computedBalance < invoice.total ? 'partial'
  : 'sent';
```

---

## Test Cases

### Happy Path
1. Record full payment in cash
   - **Given:** Invoice FAC-0042 has $80.000 balance
   - **When:** Modal opens, amount pre-filled $80.000, method = Efectivo, date = today, click "Registrar pago"
   - **Then:** Modal closes, invoice status → "Pagada", balance $0 (green), toast "Pago de $80.000 registrado correctamente"

2. Record partial payment
   - **Given:** Invoice has $200.000 balance
   - **When:** User toggles "Pago parcial", enters $100.000, method = Tarjeta, reference "TRX-9981"
   - **Then:** Balance preview shows $100.000 remaining, status preview shows "Pago parcial". After submit: invoice shows 2 payments, balance $100.000.

### Edge Cases
1. Amount exceeds balance
   - **Given:** Balance is $50.000
   - **When:** User enters $75.000
   - **Then:** Inline error "El monto no puede superar el saldo pendiente ($50.000)"

2. Transfer without reference
   - **Given:** User selects "Transferencia bancaria"
   - **When:** Submits without reference number
   - **Then:** Inline error "Número de referencia requerido para este método"

### Error Cases
1. Invoice already paid (concurrent edit)
   - **Given:** Another user paid the invoice while modal was open
   - **When:** User submits payment
   - **Then:** 409 error → toast "Esta factura ya fue pagada en su totalidad." Modal closes.

---

## Acceptance Criteria

- [ ] Modal triggered from invoice detail action panel
- [ ] Invoice summary bar: number, total, paid, balance
- [ ] Amount field pre-filled with balance (editable)
- [ ] Partial payment toggle (checkbox): allows amount < balance
- [ ] Payment method dropdown: cash (default), card, transfer, insurance, other
- [ ] Date field (defaults to today, not future)
- [ ] Reference number field (required for card/transfer)
- [ ] Notes textarea (optional)
- [ ] Live balance preview card with resulting status
- [ ] Zod validation with inline errors
- [ ] Submit: POST payment → modal closes → invoice detail refreshes → success toast
- [ ] Cancel with confirmation if form dirty
- [ ] Focus trap within modal
- [ ] Bottom sheet on mobile, centered modal on tablet/desktop
- [ ] Accessibility: role="dialog", aria-live for balance, keyboard navigation
- [ ] Spanish (es-419) labels

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
