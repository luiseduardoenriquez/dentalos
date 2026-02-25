# Analiticas de Ingresos (Revenue Analytics) — Frontend Spec

## Overview

**Screen:** Revenue analytics page with financial insights. Charts include: revenue trend with previous period comparison (dual line), revenue by doctor (stacked bar), revenue by procedure type (treemap), payment method breakdown (donut). Accounts receivable aging table with 4 buckets. CSV export button for all data.

**Route:** `/analytics/revenue`

**Priority:** High

**Backend Specs:** `specs/analytics/revenue-stats.md` (AN-04)

**Dependencies:** `specs/frontend/analytics/analytics-dashboard.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Analytics dashboard → "Ver detalle de ingresos" link
- Billing section → "Ver analiticas"
- Sidebar under Analytics

**Exit Points:**
- Click invoice in aging table → `/billing/invoices/{id}`
- Click doctor bar → filtered billing view
- Breadcrumb → `/analytics`

**User Story:**
> As a clinic_owner, I want to analyze my revenue trends, understand which doctors and procedures generate the most income, and track overdue invoices so that I can manage my clinic's financial health.

**Roles with access:** `clinic_owner`, `superadmin`

---

## Layout Structure

```
+--------------------------------------------------+
|  Sidebar | Breadcrumb: Analiticas > Ingresos     |
|          | "Analiticas de Ingresos"               |
|          | [Date range filter] [Exportar CSV btn] |
|          +---------------------------------------+
|          |  [KPI: Total] [Cobrado] [Pendiente] [Tasa cobro] |
|          +---------------------------------------+
|          |  [Chart: Revenue Trend (dual line, full width)] |
|          +---------------------------------------+
|          |  [Chart: By Doctor (stacked bar)] | [By Procedure Type (treemap)] |
|          +---------------------------------------+
|          |  [Chart: Payment Method (donut)] | [AR Aging Table] |
+------------------------------------------+-------+
```

---

## UI Components

### KPI Summary Row (4 cards)

| Card | Label | Value | Notes |
|------|-------|-------|-------|
| 1 | Ingresos Totales | `$8.450.000` COP | For selected period |
| 2 | Cobrado | `$7.200.000` COP | Paid invoices |
| 3 | Por Cobrar | `$1.250.000` COP | Unpaid/pending invoices — red if > 20% of total |
| 4 | Tasa de Cobro | `85%` | (Cobrado / Total) × 100 — green ≥ 90%, amber 70-90%, red < 70% |

---

## Chart Specifications

### Chart 1: Tendencia de Ingresos (Dual Line)

**Type:** Line chart — current vs previous period
**Full width**
**Lines:**
- "Periodo actual" — `stroke: #0D9488` teal `strokeWidth: 2.5`
- "Periodo anterior" — `stroke: #9CA3AF` gray `strokeWidth: 1.5 strokeDasharray: 6 3`
**Y-axis:** COP formatted `"$1.2M"` with `Intl.NumberFormat`
**X-axis:** Time labels (day, week, or month depending on period length)
**Tooltip:** Side-by-side comparison: `"Feb 2026: $850.000 | Feb 2025: $680.000 (+25%)"` with delta badge
**Toggle:** "Comparar con periodo anterior" checkbox — enabled by default

**Shaded area between lines:**
- Current above previous: `fill: #99F6E4` (green teal) at 20% opacity
- Current below previous: `fill: #FECACA` (red-100) at 20% opacity

### Chart 2: Ingresos por Doctor (Stacked Bar)

**Type:** Stacked vertical bar chart
**Width:** Left half on desktop, full width on mobile
**Data:** Monthly revenue split by doctor, each doctor a different color segment
**Colors:** Rotate through: teal-600, blue-400, violet-400, amber-400, pink-400, green-400
**X-axis:** Month labels
**Y-axis:** COP formatted
**Legend:** Below chart, each doctor as color dot + name
**Tooltip:** `"Enero 2026 — Dr. Garcia: $350.000, Dra. Lopez: $420.000, Total: $770.000"`
**Click bar segment:** Filter invoices for that doctor-month

### Chart 3: Ingresos por Tipo de Procedimiento (Treemap)

**Type:** Treemap chart
**Width:** Right half on desktop, full width on mobile
**Data:** Revenue by procedure category (Ortodoncia, Endodoncia, Limpieza, Cirugia, etc.)
**Rectangles:**
- Size proportional to revenue
- Color: gradient from `teal-300` (small) to `teal-700` (largest)
- Label inside rectangle: category name + `$XXX.000` (if rectangle large enough)
- Min label threshold: don't show label if rectangle < 5% of total area
**Tooltip:** `"Ortodoncia: $2.450.000 (29% de ingresos)"`
**Empty rectangle:** Categories with 0 revenue not shown

### Chart 4: Metodo de Pago (Donut)

**Type:** Donut chart
**Width:** Left quarter (3/12) on desktop, full width mobile
**Segments:**

| Method | Color |
|--------|-------|
| Efectivo | `#10B981` green |
| Transferencia | `#60A5FA` blue |
| Tarjeta credito | `#8B5CF6` violet |
| Tarjeta debito | `#F472B6` pink |
| Seguro / Convenio | `#F59E0B` amber |
| Cuotas / Plan pago | `#6B7280` gray |

**Center:** `"Formas de Pago"` `text-xs` + total count of transactions
**Legend:** Below, 2 columns — method + % + formatted total amount

---

## Accounts Receivable Aging Table

**Type:** Data table
**Width:** Right three-quarters (9/12) on desktop, full width mobile
**Title:** `"Cuentas por Cobrar — Antigüedad"` `text-base font-semibold`

**Columns:**

| Column | Description |
|--------|-------------|
| Bucket | 0-30 dias, 31-60 dias, 61-90 dias, +90 dias |
| # Facturas | Count of invoices in bucket |
| Monto Total | Sum of outstanding amounts COP |
| % del Total | Percentage of all AR |
| Accion | "Ver facturas →" link |

**Row styling:**

| Bucket | Style |
|--------|-------|
| 0-30 dias | `bg-white` — normal |
| 31-60 dias | `bg-amber-50 text-amber-800` — mild concern |
| 61-90 dias | `bg-orange-50 text-orange-800` — attention |
| +90 dias | `bg-red-50 text-red-800 font-semibold` — critical |

**Summary row:** Total row at bottom: `"Total AR"` + total count + total amount + "100%"

**"Ver facturas →" link per bucket:** Navigates to `/billing/invoices?days_overdue_min={n}&days_overdue_max={m}`

**Progress bars per row:** `h-1.5` bar below monto showing % of total AR visually

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Get revenue analytics | `/api/v1/analytics/revenue` | GET | `specs/analytics/revenue-stats.md` | 5min |
| Export CSV | `/api/v1/analytics/revenue/export` | GET | `specs/analytics/export.md` | None |

### Query Parameters

```
?from=2025-01-01
&to=2026-02-25
&compare=true        // include previous period data
```

### State Management

**Local State (useState):**
- `dateFrom: string`, `dateTo: string`
- `comparePeriod: boolean` — toggle for previous period comparison

**Server State (TanStack Query):**
- `useQuery({ queryKey: ['revenue-analytics', from, to, comparePeriod], staleTime: 5 * 60 * 1000 })`

---

## Interactions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Toggle period comparison | Checkbox | Fetch previous period data, show/hide line | Second line fades in/out |
| Click doctor bar segment | Click | Navigate to filtered invoices | Standard navigation |
| Click treemap rectangle | Click | Navigate to `/billing/invoices?procedure_type={type}` | Standard navigation |
| Click "Ver facturas" in aging table | Click | Navigate to filtered invoices | Standard navigation |
| Click "Exportar CSV" | Click | Download revenue data as CSV | "Generando exportacion..." toast → file download |
| Apply date range | Click "Aplicar" | Refetch all | All charts skeleton |

---

## Loading & Error States

### Loading State
- KPI cards: 4 `h-20 animate-pulse rounded-2xl bg-gray-100`
- Charts: `h-64 animate-pulse bg-gray-50 rounded-2xl`
- Aging table: `5 rows h-10 animate-pulse bg-gray-100 rounded` per row

### Error State
- Per-chart retry inline
- Global error banner above KPIs

### Empty State
- No revenue data: "Sin ingresos registrados para este periodo" + "Crear primera factura" CTA

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | All elements stacked. Treemap smaller `h-48`. Aging table scrolls horizontally (fixed first column). Export button full-width. |
| Tablet (640-1024px) | 2-column for doctor bar + treemap. Donut + aging table side by side. |
| Desktop (> 1024px) | Full layout as described. |

---

## Accessibility

- **Screen reader:** KPI cards `aria-label` with full value + period. Revenue trend chart summary: `"Ingresos actuales {amount}, {delta}% vs periodo anterior"`. Aging table: proper `<table> <thead> <th>` markup with `scope="col"`. Each aging row: `aria-label="0-30 dias: {N} facturas, {amount} pendiente"`.
- **Color coding in aging table:** Both background color AND severity icon (`CheckCircle`, `AlertTriangle`, `AlertOctagon`) used — color not sole indicator.
- **Treemap:** Text labels inside rectangles + tooltip on hover/focus. Tab-navigable rectangles with `role="button"`.
- **Language:** All financial data formatted with `Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP' })`. Labels in es-419.

---

## Design Tokens

**Colors:**
- Revenue trend current: `#0D9488`
- Revenue trend previous: `#9CA3AF` dashed
- Positive delta area: `#99F6E4` at 20% opacity
- Negative delta area: `#FECACA` at 20% opacity
- Aging 0-30: `bg-white`
- Aging 31-60: `bg-amber-50`
- Aging 61-90: `bg-orange-50`
- Aging +90: `bg-red-50 font-semibold`
- Treemap range: `teal-300` → `teal-700`

**Typography:**
- KPI value: `text-3xl font-bold text-gray-900`
- Aging table bucket: `text-sm font-semibold`
- Aging amount: `text-base font-bold`

**Spacing:**
- Export button: positioned `right-0 top-0` absolute within page header, `ml-auto`

---

## Implementation Notes

**Dependencies (npm):**
- `recharts` — LineChart, BarChart (stacked), PieChart, Treemap
- `lucide-react` — TrendingUp, AlertTriangle, CheckCircle, Download

**File Location:**
- Page: `src/app/(dashboard)/analytics/revenue/page.tsx`
- Components: `src/components/analytics/RevenueAnalytics.tsx`, `src/components/analytics/charts/RevenueDualLineChart.tsx`, `src/components/analytics/charts/RevenueByDoctorChart.tsx`, `src/components/analytics/charts/ProcedureTreemap.tsx`, `src/components/analytics/charts/PaymentMethodDonut.tsx`, `src/components/analytics/ARAgingTable.tsx`

**CSV Export Format:**
```
Periodo, Tipo, Doctor, Procedimiento, Monto, Estado, Fecha
2026-02, Factura, Dr. Garcia, Ortodoncia, 450000, Pagado, 2026-02-15
...
```

---

## Acceptance Criteria

- [ ] Date range filter with previous-period comparison toggle
- [ ] 4 KPI cards with color-coded collection rate
- [ ] Revenue trend dual-line chart with delta shading
- [ ] Revenue by doctor stacked bar chart
- [ ] Revenue by procedure type treemap
- [ ] Payment method donut chart with amounts in legend
- [ ] Accounts receivable aging table with 4 buckets and color coding
- [ ] "Ver facturas →" links for each aging bucket
- [ ] "Exportar CSV" downloads all revenue data
- [ ] All charts respond to date range changes
- [ ] Loading skeletons and empty states
- [ ] Responsive: stacked on mobile, multi-column on tablet+
- [ ] Accessibility: proper table markup, color not sole indicator
- [ ] Spanish (es-419) with es-CO currency formatting (COP)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
