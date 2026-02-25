# Detalle de Factura (Invoice Detail) — Frontend Spec

## Overview

**Screen:** Full-page view of a single invoice. Shows header info, line items table, payments list, remaining balance, status timeline, and action buttons (send, record payment, download PDF, void). Content adjusts based on invoice status.

**Route:** `/billing/invoices/{id}`

**Priority:** High

**Backend Specs:** `specs/billing/B-02.md`

**Dependencies:** `specs/frontend/billing/invoice-list.md`, `specs/frontend/billing/payment-record.md`

---

## User Flow

**Entry Points:**
- Click invoice row on `/billing/invoices`
- Email link sent to patient
- Patient portal (read-only view)
- "Ver factura" from billing dashboard quick-links

**Exit Points:**
- Click "← Facturas" breadcrumb → `/billing/invoices`
- Click patient name → `/patients/{id}`
- Record payment modal → stays on page, refreshes payments list
- Download PDF → browser download
- Void invoice → confirmation dialog → invoice status changes to "Anulada"

**User Story:**
> As a receptionist, I want to see a full invoice with its payment history so that I can confirm what has been paid and record new payments.

**Roles with access:** clinic_owner, receptionist, doctor (own patients)

---

## Layout Structure

```
+--------+-------------------------------------------------+
|        |  Header                                         |
|        +-------------------------------------------------+
|        |                                                 |
| Side-  |  ← Facturas  /  FAC-0042                       |
|  bar   |                                                 |
|        |  +-------------------+  +--------------------+ |
|        |  | Encabezado        |  | Acciones           | |
|        |  | FAC-0042 [Enviada]|  | [Enviar]           | |
|        |  | Paciente: Ana L.  |  | [Registrar pago]   | |
|        |  | Fecha: 12 Feb     |  | [Descargar PDF]    | |
|        |  | Vence: 26 Feb     |  | [Anular] (owner)   | |
|        |  +-------------------+  +--------------------+ |
|        |                                                 |
|        |  Ítems de Factura                               |
|        |  +-------------------------------------------+ |
|        |  | Descripción | Cant | P.Unit | Total        | |
|        |  | Extracción  | 1    | $80.000 | $80.000     | |
|        |  | Rx Periap.  | 2    | $25.000 | $50.000     | |
|        |  +-------------------------------------------+ |
|        |  Subtotal: $130.000  IVA: $0  Total: $130.000  |
|        |                                                 |
|        |  Pagos Registrados                              |
|        |  +-------------------------------------------+ |
|        |  | Fecha | Método | Referencia | Monto        | |
|        |  | 12 Feb | Efectivo | —       | $50.000      | |
|        |  +-------------------------------------------+ |
|        |  Saldo pendiente: $80.000                       |
|        |                                                 |
|        |  Línea de tiempo de estado                      |
|        |  Creada ──●── Enviada ──○── Pagada              |
|        |                                                 |
+--------+-------------------------------------------------+
```

**Sections:**
1. Breadcrumb — "← Facturas / FAC-0042"
2. Invoice header card — invoice number, status badge, patient link, dates
3. Action panel (right column on desktop) — context-aware action buttons
4. Line items table — description, quantity, unit price, line total; totals footer
5. Payments list — each recorded payment with date, method, reference, amount
6. Balance summary — amounts paid, remaining balance (highlighted if > 0)
7. Status timeline — horizontal progress indicator showing invoice lifecycle

---

## UI Components

### Component 1: InvoiceHeaderCard

**Type:** Card

**Content:**
- Invoice number (large, monospace): `FAC-0042`
- Status badge (large variant): e.g., "Enviada" (blue)
- Patient: full name as link → `/patients/{id}`
- Invoice date, due date (highlighted red if past due and unpaid)
- Created by (doctor/receptionist name)
- Notes (if any, in gray box)

### Component 2: ActionPanel

**Type:** Card with vertical button stack

**Buttons (context-aware):**

| Button | Shows when | Action |
|--------|-----------|--------|
| Enviar | status = draft | Send invoice (email/WhatsApp) → status → sent |
| Reenviar | status = sent/overdue | Resend invoice |
| Registrar pago | status = sent/overdue/partial | Opens PaymentRecordModal |
| Descargar PDF | Always | Triggers PDF download |
| Anular | status ≠ cancelled, paid (owner only) | Confirmation dialog → void |

### Component 3: LineItemsTable

**Type:** Read-only table

**Columns:** Descripción, Cantidad, Precio Unitario, Descuento, Total (line)

**Footer row:** Subtotal | Descuento total | IVA | Total (bold)

### Component 4: PaymentsList

**Type:** Compact table

**Columns:** Fecha, Método de pago, Referencia, Monto

**Payment method icons:** cash (banknote), card (credit-card), transfer (arrow-right-left), insurance (shield)

**"Sin pagos registrados"** empty state if no payments.

### Component 5: BalanceSummary

**Type:** Summary row

**Content:**
- Total factura: $XXX
- Total pagado: $XXX (green)
- Saldo pendiente: $XXX (red if > 0, green if 0)

**Zero balance state:** Shows green "Pagada en su totalidad" with check icon.

### Component 6: StatusTimeline

**Type:** Horizontal stepper

**Steps:** Borrador → Enviada → [Parcialmente pagada] → Pagada / Anulada

Active step highlighted with primary color and icon. Completed steps in green. Future steps in gray.

---

## Form Fields

No inline form fields — payment recording is in a separate modal (see `specs/frontend/billing/payment-record.md`).

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Load invoice | `/api/v1/billing/invoices/{id}` | GET | `specs/billing/B-02.md` | 1min |
| Send invoice | `/api/v1/billing/invoices/{id}/send` | POST | `specs/billing/B-02.md` | — |
| Download PDF | `/api/v1/billing/invoices/{id}/pdf` | GET | `specs/billing/B-02.md` | — |
| Void invoice | `/api/v1/billing/invoices/{id}/void` | POST | `specs/billing/B-02.md` | — |
| List payments | `/api/v1/billing/invoices/{id}/payments` | GET | `specs/billing/B-07.md` | 1min |

### State Management

**Local State (useState):**
- `showVoidDialog: boolean`
- `isSending: boolean`
- `isDownloading: boolean`

**Global State (Zustand):**
- None

**Server State (TanStack Query):**
- Query key: `['invoice', invoiceId]` — stale 1 minute
- Query key: `['invoice-payments', invoiceId]` — stale 1 minute
- Mutation: `sendInvoice`, `voidInvoice` — both invalidate `['invoice', invoiceId]`
- After payment recorded in modal: `invalidateQueries(['invoice-payments', invoiceId])` and `['invoice', invoiceId]`

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click "Enviar" | Button click | POST send; status → sent | Button spinner → "Factura enviada" toast |
| Click "Registrar pago" | Button click | Opens PaymentRecordModal | Modal slides up |
| Payment recorded | Modal success | Payments list refreshes, balance updates | "Pago registrado" toast, modal closes |
| Click "Descargar PDF" | Button click | Fetch PDF blob, trigger browser download | Button spinner → file downloads |
| Click "Anular" | Button click | Void confirmation dialog | Dialog with warning + "Anular factura" confirm button |
| Confirm void | Dialog confirm | POST void; status → cancelled | "Factura anulada" toast, action panel updates |
| Click patient link | Click name | Navigate to `/patients/{id}` | Standard navigation |

### Animations/Transitions

- Status badge: no animation (static)
- StatusTimeline: completed steps animate left-to-right on page load (500ms stagger)
- Payment row added: slide in from top (200ms)
- BalanceSummary numbers: count-up animation when page loads (400ms, framer-motion)

---

## Loading & Error States

### Loading State
- Full page skeleton: header card skeleton (3 text lines), line items table skeleton (3 rows), payments skeleton (2 rows), timeline skeleton (3 dots with lines)

### Error State
- Invoice not found (404): centered "Factura no encontrada" card with "← Volver a facturas" button
- Load failure: error card with "Error al cargar la factura" + "Reintentar" button
- Send failure: error toast "No se pudo enviar la factura. Intenta de nuevo."
- Void failure: error toast + dialog remains open for retry

### Empty State
- No payments: "Sin pagos registrados" with small icon in payments section

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Header card full width. Action panel moves below header (button row, scrollable). Line items table horizontal scroll. Status timeline vertical. |
| Tablet (640-1024px) | Header card + action panel side by side (70/30 split). Line items full width. Timeline horizontal. |
| Desktop (> 1024px) | Two-column layout: left 65% (header, items, payments, timeline), right 35% (sticky action panel). |

**Tablet priority:** High — clinic staff view invoice details on tablets.

---

## Accessibility

- **Focus order:** Breadcrumb → patient link → action buttons (send, pay, download, void) → line items table → payments table → timeline
- **Screen reader:** Invoice number + status announced as heading. Status badge has `aria-label="Estado: Enviada"`. StatusTimeline uses `role="list"` with step items having `aria-current="step"`. Void dialog has `role="alertdialog"` with `aria-describedby` explaining consequences.
- **Keyboard navigation:** Tab through all interactive elements. Enter on action buttons. Escape to close void dialog.
- **Color contrast:** Red balance amount meets WCAG AA. Status badges use text + color.
- **Language:** All section headings, button labels, status names in es-419.

---

## Design Tokens

**Colors:**
- Invoice number: `text-2xl font-mono font-bold text-gray-900`
- Section headings: `text-sm font-semibold text-gray-700 uppercase tracking-wide`
- Balance pending (non-zero): `text-red-600 font-bold`
- Balance zero: `text-green-600 font-semibold`
- Due date overdue: `text-red-600`
- Timeline active: `text-primary-600 bg-primary-50`
- Timeline completed: `text-green-600 bg-green-50`
- Timeline future: `text-gray-400 bg-gray-100`
- Action panel: `bg-white rounded-xl border border-gray-100 p-5 space-y-3`

**Typography:**
- Invoice number: `text-2xl font-mono font-bold`
- Section title: `text-sm font-semibold uppercase tracking-wider text-gray-500 mb-3`
- Table header: `text-xs font-medium text-gray-500 uppercase`
- Payment method: `text-sm text-gray-700 capitalize`

**Spacing:**
- Section gap: `space-y-6`
- Card padding: `p-5 md:p-6`
- Table cell: `py-3 px-4`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-query` — data fetching + mutations
- `lucide-react` — Send, Download, Ban, CreditCard, Banknote, ArrowRightLeft, Shield, CheckCircle
- `framer-motion` — balance count-up, timeline animation, payment row slide-in
- `@radix-ui/react-alert-dialog` — void confirmation dialog

**File Location:**
- Page: `src/app/(dashboard)/billing/invoices/[id]/page.tsx`
- Components: `src/components/billing/InvoiceHeaderCard.tsx`, `src/components/billing/InvoiceActionPanel.tsx`, `src/components/billing/InvoiceLineItemsTable.tsx`, `src/components/billing/PaymentsList.tsx`, `src/components/billing/BalanceSummary.tsx`, `src/components/billing/StatusTimeline.tsx`
- Hooks: `src/hooks/useInvoice.ts`, `src/hooks/useInvoicePayments.ts`
- API: `src/lib/api/billing.ts`

**Hooks Used:**
- `useAuth()` — role-based action visibility (void = clinic_owner only)
- `useQuery(['invoice', id])` — invoice detail
- `useQuery(['invoice-payments', id])` — payments list
- `useMutation(sendInvoice)`, `useMutation(voidInvoice)`

---

## Test Cases

### Happy Path
1. View sent invoice with partial payment
   - **Given:** Invoice FAC-0042 has total $130.000, one payment of $50.000
   - **When:** User navigates to `/billing/invoices/fac-0042-uuid`
   - **Then:** Header shows "Enviada" badge, payments list shows 1 payment, balance shows $80.000 in red

2. Record full payment
   - **Given:** Invoice has $80.000 balance
   - **When:** User clicks "Registrar pago", enters $80.000, submits
   - **Then:** Balance shows $0, status updates to "Pagada", timeline advances to paid step, balance summary shows green "Pagada en su totalidad"

### Edge Cases
1. Overdue invoice
   - **Given:** Due date was yesterday, status is sent
   - **When:** Invoice detail loads
   - **Then:** Due date shown in red, status badge shows "Vencida" in red

2. Already void invoice
   - **Given:** Invoice status is cancelled
   - **When:** User views detail
   - **Then:** Action panel shows only "Descargar PDF". No "Enviar", "Registrar pago", or "Anular" buttons.

### Error Cases
1. PDF download fails
   - **Given:** PDF generation times out
   - **When:** User clicks "Descargar PDF"
   - **Then:** Error toast "No se pudo generar el PDF. Intenta de nuevo."

---

## Acceptance Criteria

- [ ] Invoice header: number, status badge, patient link, dates, created by, notes
- [ ] Action panel with context-aware buttons (send/resend, record payment, download PDF, void)
- [ ] Line items table (read-only): description, quantity, unit price, discount, line total
- [ ] Totals footer: subtotal, IVA, grand total
- [ ] Payments list: date, method icon, reference, amount
- [ ] Balance summary: total, paid, remaining (red if balance > 0, green if zero)
- [ ] Status timeline: horizontal stepper with correct active/completed/future states
- [ ] Void confirmation dialog (clinic_owner only) with warning
- [ ] PDF download (blob response)
- [ ] Loading skeleton matching all sections
- [ ] 404 state: "Factura no encontrada"
- [ ] Responsive: stacked mobile, 70/30 tablet, two-column desktop
- [ ] Accessibility: ARIA, keyboard, screen reader
- [ ] Spanish (es-419) labels

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
