# Mi Cuenta — Portal del Paciente (Portal Invoices) — Frontend Spec

## Overview

**Screen:** Invoice and payment history in patient portal. Simple list showing invoices with dates, amounts, and status. Outstanding balance card at top. Payment link if online payments are enabled by clinic. PDF download per invoice.

**Route:** `/portal/[clinicSlug]/invoices`

**Priority:** Medium

**Backend Specs:** `specs/portal/PP-06.md`

**Dependencies:** `specs/frontend/portal/portal-dashboard.md`

---

## User Flow

**Entry Points:**
- "Ver estado de cuenta" from portal dashboard balance card
- "Mi cuenta" in portal navigation

**Exit Points:**
- Download PDF → browser download
- Pay online link → external payment gateway (Mercado Pago)
- "← Inicio" → dashboard

**User Story:**
> As a patient, I want to see my invoice history and outstanding balance so that I know what I owe my clinic and can pay online if available.

**Roles with access:** patient (portal session)

---

## Layout Structure

```
+------------------------------------------+
|  [Navbar]                                 |
+------------------------------------------+
|  ← Inicio     Mi Cuenta                  |
|                                           |
|  +--------------------------------------+ |
|  | Saldo pendiente                      | |
|  | $80.000 COP                 [Pagar]  | |
|  | (Pagar button only if online enabled)| |
|  +--------------------------------------+ |
|                                           |
|  Historial de facturas                    |
|                                           |
|  +--------------------------------------+ |
|  | FAC-0042                             | |
|  | 12 de febrero de 2026                | |
|  | $130.000        [Pagada ✓]   [PDF↓]  | |
|  +--------------------------------------+ |
|  +--------------------------------------+ |
|  | FAC-0038                             | |
|  | 10 de enero de 2026                  | |
|  | $80.000     [Pendiente ○]    [PDF↓]  | |
|  +--------------------------------------+ |
+------------------------------------------+
```

**Sections:**
1. Page header — back link, title "Mi Cuenta"
2. Outstanding balance card — total owed, "Pagar en línea" button (if online payments enabled)
3. Invoice history list — sorted by date descending; each with amount, status, PDF download

---

## UI Components

### Component 1: OutstandingBalanceCard

**Type:** Prominent card

**States:**
1. **Balance > 0:** Red/orange background, amount, "Pagar en línea" button (if `tenant.online_payments_enabled`)
2. **Balance = 0:** Green background, "Al día ✓", "Gracias por estar al día con tus pagos"

**"Pagar en línea" button:**
- Redirects to Mercado Pago (or configured gateway) checkout
- Opens in new tab
- Shown only if `tenant.online_payments_enabled = true`

### Component 2: InvoiceCard

**Type:** Card (list layout)

**Content:**
- Invoice number (small, gray): FAC-0042
- Date: full date "12 de febrero de 2026" (long format for clarity)
- Amount (large): "$130.000"
- Status badge:

| Status | Label | Color |
|--------|-------|-------|
| paid | Pagada ✓ | green |
| sent / overdue | Pendiente | orange |
| cancelled | Anulada | gray |

- PDF download button: "Descargar PDF" or just download icon (right side)

### Component 3: EmptyInvoiceState

**Type:** Centered illustration card

**Content:** Illustration + "No tienes facturas registradas." + "Si tienes preguntas, escríbenos a través de Mensajes."

---

## Form Fields

No form fields — read-only list + download actions.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Invoice list + balance | `/api/v1/portal/invoices` | GET | `specs/portal/PP-06.md` | 2min |
| Download PDF | `/api/v1/portal/invoices/{id}/pdf` | GET | `specs/portal/PP-06.md` | — |
| Online payment link | `/api/v1/portal/invoices/payment-link` | POST | `specs/portal/PP-06.md` | — |

**Response:**
```json
{
  "outstanding_balance": 80000,
  "online_payments_enabled": true,
  "invoices": [ { "id": "...", "number": "FAC-0042", "date": "...", "amount": 130000, "status": "paid" } ]
}
```

### State Management

**Local State (useState):**
- `downloadingId: string | null`

**Server State (TanStack Query):**
- Query key: `['portal-invoices', patientId]` — stale 2min
- Mutation: `getPaymentLink` — returns redirect URL to payment gateway

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click "Pagar en línea" | Tap | POST payment link → open gateway URL | Button spinner → new tab opens |
| Download PDF | Tap download icon | Fetch PDF blob → browser download | Icon spinner |
| Scroll | Scroll | Infinite scroll or "Cargar más" (10 items per page) | Loading spinner |

---

## Loading & Error States

### Loading State
- Balance card: skeleton
- Invoice list: 3 skeleton cards

### Error State
- Load failure: error card with retry
- PDF download failure: toast "No se pudo descargar la factura."
- Payment link failure: toast "No se pudo iniciar el pago. Intenta de nuevo."

### Empty State
- No invoices: illustration + "No tienes facturas registradas." + messages link

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Full-width cards. Balance card large and prominent. Download is icon-only (no text). |
| Tablet+ | Cards max-width 600px centered. Download button has text. |

---

## Accessibility

- **Screen reader:** Balance card `aria-label="Saldo pendiente: $80.000 pesos colombianos"`. Invoice card `aria-label="Factura {number}, {date}, {amount}, estado: {status}"`. Download button `aria-label="Descargar PDF de {number}"`.
- **Keyboard navigation:** Tab through balance card button → invoice cards → download buttons.
- **Language:** Patient-friendly status names. es-419.

---

## Design Tokens

**Colors:**
- Balance positive: `bg-red-50 border-red-200 text-red-700`
- Balance zero: `bg-green-50 border-green-200 text-green-700`
- Balance amount: `text-3xl font-bold`
- Paid badge: `bg-green-50 text-green-700`
- Pending badge: `bg-orange-50 text-orange-700`

**Spacing:**
- Between invoice cards: `gap-3`
- Card padding: `p-4`
- Balance card padding: `p-6`

---

## Implementation Notes

**File Location:**
- Page: `src/app/(portal)/[clinicSlug]/invoices/page.tsx`
- Components: `src/components/portal/OutstandingBalanceCard.tsx`, `src/components/portal/PortalInvoiceCard.tsx`
- Hooks: `src/hooks/usePortalInvoices.ts`

---

## Test Cases

### Happy Path
1. View balance and invoices
   - **Given:** Patient owes $80.000, has 2 invoices
   - **When:** Navigates to "Mi Cuenta"
   - **Then:** Balance card shows $80.000 in red. 2 invoice cards listed.

2. Online payment (enabled)
   - **Given:** `tenant.online_payments_enabled = true`
   - **When:** Patient taps "Pagar en línea"
   - **Then:** New tab opens Mercado Pago checkout with $80.000 pre-filled

### Edge Cases
1. Balance zero
   - **Given:** All invoices paid
   - **When:** Page loads
   - **Then:** Balance card shows green "Al día ✓"

2. Online payment disabled
   - **Given:** `tenant.online_payments_enabled = false`
   - **When:** Page loads
   - **Then:** Balance card shows amount but NO "Pagar en línea" button. Shows clinic phone: "Para pagar, llama a {clinicPhone}."

---

## Acceptance Criteria

- [ ] Outstanding balance card at top (red if >0, green if 0)
- [ ] "Pagar en línea" button (visible only if `tenant.online_payments_enabled = true`)
- [ ] Invoice list: number, date, amount, status badge, PDF download
- [ ] Invoice sorted by date descending
- [ ] PDF download per invoice (blob download)
- [ ] Payment link opens in new tab
- [ ] Loading skeletons
- [ ] Empty state with messages link
- [ ] Error states with toasts
- [ ] Responsive: mobile-first full width, centered tablet/desktop
- [ ] Accessibility: ARIA labels, keyboard navigation
- [ ] Patient-friendly language, es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
