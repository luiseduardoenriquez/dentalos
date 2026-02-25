# Dashboard de Facturación (Billing Dashboard) — Frontend Spec

## Overview

**Screen:** Billing overview dashboard with KPI cards, period selector, and four charts: revenue trend (line), payment methods breakdown (pie), top procedures by revenue (bar), and aging report (stacked bar). Entry point for the billing section.

**Route:** `/billing`

**Priority:** High

**Backend Specs:** `specs/billing/B-13.md`

**Dependencies:** `specs/frontend/billing/invoice-list.md`, `specs/frontend/analytics/revenue-analytics.md`

---

## User Flow

**Entry Points:**
- Sidebar navigation "Facturación" (first item)
- Main dashboard "Ver facturación" link

**Exit Points:**
- KPI card click → `/billing/invoices` (with status filter pre-applied)
- "Ver todas las facturas" link → `/billing/invoices`
- "Ver reporte de comisiones" → `/billing/commissions`
- Chart data point click → filtered invoice list

**User Story:**
> As a clinic_owner, I want a billing overview so that I can understand revenue, outstanding payments, and cash flow at a glance without running manual reports.

**Roles with access:** clinic_owner, receptionist (limited view)

---

## Layout Structure

```
+--------+---------------------------------------------------+
|        |  Header                                           |
|        +---------------------------------------------------+
|        |                                                   |
| Side-  |  "Facturación"      Período: [Este mes ▼]        |
|  bar   |                                                   |
|        |  KPI Cards (4-column):                            |
|        |  [Ingr. este mes] [Saldo pendiente]               |
|        |  [Pagado este mes] [Fact. vencidas]               |
|        |                                                   |
|        |  +---------------------+ +---------------------+ |
|        |  | Tendencia ingresos  | | Métodos de pago      | |
|        |  | (línea, 30 días)    | | (torta)              | |
|        |  +---------------------+ +---------------------+ |
|        |                                                   |
|        |  +---------------------+ +---------------------+ |
|        |  | Top procedimientos  | | Antigüedad de saldos | |
|        |  | por ingreso (barras)| | (barras apiladas)    | |
|        |  +---------------------+ +---------------------+ |
|        |                                                   |
|        |  [Ver todas las facturas →]                       |
|        |  [Ver reporte de comisiones →]                    |
+--------+---------------------------------------------------+
```

**Sections:**
1. Page header — title "Facturación", period selector dropdown
2. KPI cards row — 4 cards with main billing metrics
3. Revenue trend chart — line chart (left) + payment methods pie chart (right)
4. Procedures chart (left) + aging report chart (right)
5. Quick links row — "Ver todas las facturas", "Ver reporte de comisiones"

---

## UI Components

### Component 1: PeriodSelector

**Type:** Dropdown select

**Options:**

| Value | Label |
|-------|-------|
| today | Hoy |
| week | Esta semana |
| month | Este mes (default) |
| quarter | Este trimestre |
| year | Este año |
| custom | Personalizado... |

**Behavior:** Changing period triggers refetch of all dashboard data simultaneously. "Personalizado" opens date range picker popover.

### Component 2: KPICards

**Type:** 4-column card grid

**Cards:**

| Card | Icon | Metric | Color | Clickable |
|------|------|--------|-------|-----------|
| Ingresos del período | TrendingUp | Total revenue (COP) | primary | Yes → invoices?status=paid |
| Saldo pendiente | Clock | Total outstanding balance | orange | Yes → invoices?status=sent,overdue |
| Pagado este período | CheckCircle | Total paid (COP) | green | Yes → invoices?status=paid |
| Facturas vencidas | AlertTriangle | Count of overdue invoices | red | Yes → invoices?status=overdue |

**KPI Card anatomy:**
- Icon (24px, colored)
- Label (sm, gray-500)
- Value (2xl, bold)
- Change indicator: "+X% vs período anterior" (green/red arrow)

### Component 3: RevenueTrendChart

**Type:** Line chart (Recharts `LineChart`)

**Data:** Daily revenue totals for the selected period

**Axes:**
- X: date labels (dd MMM for month view, weekday for week view)
- Y: COP amounts (formatted $XXX.000)

**Lines:**
- "Facturado" (primary blue, solid)
- "Cobrado" (green, dashed)

**Tooltip:** date, facturado amount, cobrado amount

**Legend:** Below chart, two items matching line colors

**Size:** 50% width on desktop, full width on mobile

### Component 4: PaymentMethodsChart

**Type:** Pie / Donut chart (Recharts `PieChart`)

**Data:** Percentage of payments by method in period

**Segments:**
- Efectivo: `primary-400`
- Tarjeta: `primary-600`
- Transferencia: `blue-400`
- Seguro: `green-500`
- Otro: `gray-400`

**Center label:** "N pagos" (total payment count)

**Legend:** Right side (stacked list: color dot + label + %)

**Size:** 50% width on desktop, full width on mobile

### Component 5: TopProceduresChart

**Type:** Horizontal bar chart (Recharts)

**Data:** Top 8 procedures by revenue generated in period

**Axes:**
- Y: procedure names (truncated at 25 chars)
- X: COP revenue

**Tooltip:** Full procedure name, revenue, count of times billed

**Color:** `primary-500` bars

### Component 6: AgingReportChart

**Type:** Stacked bar chart (Recharts)

**Data:** Outstanding balance grouped by aging bucket

**Buckets (X-axis):** 0–30 días, 31–60 días, 61–90 días, 91–120 días, +120 días

**Stack segments:**
- Balance amount per bucket per doctor (or total per bucket if no doctor filter)

**Colors:** green → yellow → orange → red → dark-red (progressive urgency)

**Tooltip:** Bucket label, total outstanding, count of invoices

---

## Form Fields

Not applicable — period selector and optional date range picker are filter controls, not form fields.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Dashboard summary | `/api/v1/billing/dashboard` | GET | `specs/billing/B-13.md` | 5min |
| Revenue trend | `/api/v1/billing/reports/revenue-trend` | GET | `specs/billing/B-13.md` | 5min |
| Payment methods | `/api/v1/billing/reports/payment-methods` | GET | `specs/billing/B-13.md` | 5min |
| Top procedures | `/api/v1/billing/reports/top-procedures` | GET | `specs/billing/B-13.md` | 5min |
| Aging report | `/api/v1/billing/reports/aging` | GET | `specs/billing/B-13.md` | 5min |

**Query Params (all):** `date_from`, `date_to`

**Strategy:** All 5 endpoints called in parallel via `useQueries` or `Promise.all` pattern.

### State Management

**Local State (useState):**
- `period: PeriodPreset` — selected period
- `customRange: { from: Date, to: Date } | null` — if custom selected

**Global State (Zustand):**
- `billingStore.dashboardPeriod` — persist period selection across navigation

**Server State (TanStack Query):**
- 5 separate query keys: `['billing-dashboard', tenantId, dateRange]`, etc.
- Stale time: 5 minutes
- `useQueries` for parallel fetching
- Auto-refresh every 10 minutes (background refetch)

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Change period | Dropdown select | All charts + KPIs refetch | Loading overlay on each chart |
| Click KPI card | Click | Navigate to invoice list with pre-applied filter | Standard navigation |
| Hover chart data point | Mouse hover | Tooltip with details | Recharts tooltip |
| Click aging bar segment | Click | Navigate to invoices filtered by date range + overdue | Standard navigation |
| Click "Ver todas las facturas" | Link click | Navigate to `/billing/invoices` | Standard navigation |

### Animations/Transitions

- KPI values: count-up animation on load (framer-motion, 500ms)
- Charts: Recharts `animationDuration=800` with `animationEasing="ease-out"`
- Period change: charts fade out (100ms) → loading state → fade in with new data (200ms)

---

## Loading & Error States

### Loading State
- KPI cards: 4 skeleton cards (icon circle + 2 text lines)
- Charts: skeleton rectangles matching chart dimensions
- Initial load: all 5 API calls fire simultaneously; each section independent loading state

### Error State
- Per-chart error: small error card within chart area "Error al cargar datos. Reintentar."
- Full page error (all endpoints fail): centered error card with "Error de conexión. Reintentar."

### Empty State
- No invoices in period: KPI cards show $0/0. Charts show empty state within chart area with icon + "Sin datos para el período seleccionado."

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | KPI cards: 2×2 grid. Charts: stacked vertically, each full width. Pie chart legend below chart. Period selector full width at top. |
| Tablet (640-1024px) | KPI cards: 4-column (compact). Revenue + methods charts side-by-side (50/50). Procedures + aging charts stacked. |
| Desktop (> 1024px) | Full layout as described. 2×2 chart grid. 4-column KPI row. |

---

## Accessibility

- **Focus order:** Period selector → KPI cards (in order) → chart containers → quick links
- **Screen reader:** KPI cards have `aria-label="Ingresos del período: $2.100.000 COP. 12% más que el período anterior"`. Charts have `aria-label` describing data and period. Changes announced via `aria-live="polite"` on KPI section.
- **Keyboard navigation:** Tab through KPI cards (all interactive). Charts have keyboard-navigable data tables as fallback (visually hidden, screen-reader accessible).
- **Color contrast:** All KPI values, labels, and chart axis labels meet WCAG AA.
- **Language:** All labels, tooltips, chart axes, legends in es-419.

---

## Design Tokens

**Colors:**
- KPI revenue: `text-primary-700`
- KPI pending (orange): `text-orange-600`
- KPI paid (green): `text-green-700`
- KPI overdue (red): `text-red-600`
- Positive change indicator: `text-green-600 bg-green-50`
- Negative change indicator: `text-red-600 bg-red-50`
- Chart colors (palette): `[#0066CC, #22C55E, #F59E0B, #EF4444, #8B5CF6, #EC4899, #14B8A6, #6B7280]`
- Aging buckets: `['#22C55E', '#EAB308', '#F97316', '#EF4444', '#991B1B']`

**Typography:**
- KPI value: `text-2xl md:text-3xl font-bold`
- KPI label: `text-sm text-gray-500`
- KPI change: `text-xs font-medium`
- Chart title: `text-sm font-semibold text-gray-700`
- Chart axis labels: `text-xs text-gray-500`

**Spacing:**
- KPI grid gap: `gap-4`
- Chart grid gap: `gap-6`
- Section gap: `space-y-6`
- Chart internal padding: `p-5`

**Border Radius:**
- KPI cards: `rounded-xl`
- Chart cards: `rounded-xl`

---

## Implementation Notes

**Dependencies (npm):**
- `recharts` — LineChart, PieChart, BarChart
- `@tanstack/react-query` — `useQueries` for parallel fetching
- `framer-motion` — KPI count-up
- `date-fns` — period date calculations
- `lucide-react` — TrendingUp, Clock, CheckCircle, AlertTriangle

**File Location:**
- Page: `src/app/(dashboard)/billing/page.tsx`
- Components: `src/components/billing/BillingKPICards.tsx`, `src/components/billing/RevenueTrendChart.tsx`, `src/components/billing/PaymentMethodsChart.tsx`, `src/components/billing/TopProceduresChart.tsx`, `src/components/billing/AgingReportChart.tsx`
- Hooks: `src/hooks/useBillingDashboard.ts`
- API: `src/lib/api/billing.ts`

**Hooks Used:**
- `useAuth()` — role-based visibility
- `useQueries([...])` — parallel 5-endpoint fetching
- `useBillingStore()` — period persistence

**Parallel Query Pattern:**
```typescript
const results = useQueries({
  queries: [
    { queryKey: ['billing-dashboard', dateRange], queryFn: fetchDashboard },
    { queryKey: ['revenue-trend', dateRange], queryFn: fetchRevenueTrend },
    { queryKey: ['payment-methods', dateRange], queryFn: fetchPaymentMethods },
    { queryKey: ['top-procedures', dateRange], queryFn: fetchTopProcedures },
    { queryKey: ['aging-report', dateRange], queryFn: fetchAging },
  ],
});
```

---

## Test Cases

### Happy Path
1. View monthly billing dashboard
   - **Given:** Clinic has invoices in current month
   - **When:** User navigates to `/billing`
   - **Then:** All 4 KPIs show, all 4 charts render with data, period selector shows "Este mes"

2. Change period to quarter
   - **Given:** Dashboard loaded with month data
   - **When:** User selects "Este trimestre" in period selector
   - **Then:** All charts and KPIs reload with 3-month data; change indicators update

### Edge Cases
1. Dashboard with no prior period data (new clinic)
   - **Given:** Clinic created this week, no previous period
   - **When:** Dashboard loads
   - **Then:** Change indicators show "—" instead of % change (no comparison data)

2. All invoices in "Borrador" status (no revenue)
   - **Given:** All invoices are drafts
   - **When:** Dashboard loads
   - **Then:** KPIs show $0 revenue, $0 paid. Aging report shows $0. Charts show empty state messages.

### Error Cases
1. Partial chart failure
   - **Given:** Aging report endpoint returns 500
   - **When:** Dashboard loads
   - **Then:** Other 3 charts and KPIs load normally. Aging chart shows error card. Each section is independent.

---

## Acceptance Criteria

- [ ] Period selector: today, week, month (default), quarter, year, custom
- [ ] KPI cards: revenue, outstanding balance, paid, overdue count (with clickable navigation)
- [ ] Change indicators vs. previous period on KPI cards
- [ ] Revenue trend line chart (facturado + cobrado lines)
- [ ] Payment methods donut chart with legend
- [ ] Top procedures horizontal bar chart (top 8)
- [ ] Aging report stacked bar chart (5 buckets, progressive color)
- [ ] All charts use consistent dental theme color palette
- [ ] Tooltips on all charts (Spanish labels)
- [ ] Parallel API fetching (independent loading states per chart)
- [ ] Loading skeletons (KPI cards + chart areas)
- [ ] Empty state within chart areas
- [ ] Period persisted in Zustand across navigation
- [ ] Quick links to invoice list and commissions report
- [ ] Responsive: 2×2 KPI grid on mobile, full layout on desktop
- [ ] Accessibility: aria-labels on KPIs and charts, keyboard navigation
- [ ] Spanish (es-419) all labels

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
