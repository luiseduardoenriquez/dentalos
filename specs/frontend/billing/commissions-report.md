# Reporte de Comisiones (Commissions Report) — Frontend Spec

## Overview

**Screen:** Doctor commissions report page. Shows revenue generated per doctor, commission percentages, and commission amounts for a configurable date range. Includes a bar chart visualization, filterable summary table, and CSV export. Restricted to clinic_owner.

**Route:** `/billing/commissions`

**Priority:** Medium

**Backend Specs:** `specs/billing/B-12.md`

**Dependencies:** `specs/frontend/billing/billing-dashboard.md`, `specs/frontend/settings/clinic-settings.md`

---

## User Flow

**Entry Points:**
- Sidebar "Facturación" → "Comisiones"
- Billing dashboard "Ver reporte de comisiones" link

**Exit Points:**
- Click doctor name → `/settings/team` (team management)
- Export → CSV download, stays on page

**User Story:**
> As a clinic_owner, I want to view commissions earned by each doctor in a period so that I can calculate payroll accurately without manual spreadsheet work.

**Roles with access:** clinic_owner only

---

## Layout Structure

```
+--------+---------------------------------------------------+
|        |  Header                                           |
|        +---------------------------------------------------+
|        |                                                   |
| Side-  |  "Comisiones"               [Exportar CSV]       |
|  bar   |                                                   |
|        |  Filtros: [Fecha: Ene 2026 – Feb 2026] [Doctor▼] |
|        |                                                   |
|        |  Tarjetas resumen:                                |
|        |  [Ingresos totales] [Total comisiones] [Doctores] |
|        |                                                   |
|        |  Gráfica: Comisión por doctor (barras)            |
|        |  +-----------------------------------------------+|
|        |  | ████████ Dr. López  $250.000                  ||
|        |  | ████     Dra. Ruiz  $120.000                  ||
|        |  +-----------------------------------------------+|
|        |                                                   |
|        |  Tabla detalle:                                   |
|        |  | Doctor | Procedimientos | Ingresos | % | $Com ||
|        |  |--------|----------------|----------|---|------||
|        |  | López  | 42             | $1.2M    |20%|$250K ||
|        |  +-----------------------------------------------+|
|        |  Totales: 85 proc | $2.1M | — | $370.000          |
+--------+---------------------------------------------------+
```

**Sections:**
1. Page header — title, Export CSV button
2. Filter bar — date range picker, doctor multi-select filter
3. Summary KPI cards — total revenue, total commissions, number of doctors
4. Bar chart — commission amount per doctor (horizontal bar)
5. Detail table — doctor, procedure count, revenue, commission %, commission amount
6. Table footer — totals row

---

## UI Components

### Component 1: CommissionsFilterBar

**Type:** Horizontal filter group

**Filters:**

| Filter | Type | Default |
|--------|------|---------|
| date_range | Date range picker (month presets + custom) | Current month |
| doctor_id | Multi-select dropdown (list of active doctors) | All doctors |

**Presets:** Mes actual, Mes anterior, Trimestre actual, Año actual, Personalizado

### Component 2: SummaryCards

**Type:** 3-column KPI card row

**Cards:**

| Card | Icon | Value | Subtext |
|------|------|-------|---------|
| Ingresos totales | TrendingUp | $2.100.000 COP | "En el período seleccionado" |
| Total comisiones | DollarSign | $370.000 COP | "Para N doctores" |
| Doctores activos | Users | N | "Con procedimientos en el período" |

### Component 3: CommissionsBarChart

**Type:** Horizontal bar chart (Recharts `BarChart` with `layout="vertical"`)

**Data:** One bar per doctor, value = commission amount (COP)

**Axis:**
- Y-axis: doctor names (short name: "Dr. López")
- X-axis: commission amount in COP (formatted as $XXX.000)

**Tooltip:** On hover: doctor full name, procedures count, revenue, commission %, commission amount

**Colors:** Bars use `var(--color-primary-500)` (dental theme). If doctor filter applied, other bars are `gray-200`.

**No data state:** "Sin datos para el período seleccionado"

### Component 4: CommissionsTable

**Type:** Sortable table (TanStack Table)

**Columns:**

| Column | Header (es-419) | Width | Sortable | Content |
|--------|-----------------|-------|----------|---------|
| doctor | Doctor | flex-1 | Yes | Avatar (sm) + full name (link to team page) |
| procedures_count | Procedimientos | 140px | Yes | Integer count |
| revenue | Ingresos generados | 160px | Yes | COP formatted |
| commission_pct | Comisión (%) | 110px | Yes | "20%" |
| commission_amount | Monto comisión | 160px | Yes | COP formatted (bold) |

**Footer totals row:** Empty | Sum procedures | Sum revenue | "—" | Sum commissions (bold)

**Commission % editing:** Clicking the % column shows an edit icon. Clicking navigates to team settings for that doctor (commission % is configured per doctor in settings, not here).

### Component 5: ExportButton

**Type:** Button (secondary)

**Behavior:** GET export endpoint with current filters; downloads CSV. CSV columns match table columns plus doctor email.

---

## Form Fields

No form fields — filter controls only (date range and doctor select).

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Commissions report | `/api/v1/billing/reports/commissions` | GET | `specs/billing/B-12.md` | 5min |
| Export CSV | `/api/v1/billing/reports/commissions/export` | GET | `specs/billing/B-12.md` | — |
| List doctors (filter) | `/api/v1/users?role=doctor&is_active=true` | GET | `specs/users/U-01.md` | 10min |

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `date_from` | ISO date | Start of reporting period |
| `date_to` | ISO date | End of reporting period |
| `doctor_ids` | uuid[] | Filter to specific doctors (comma-separated) |

**Response shape:**
```json
{
  "period": { "from": "...", "to": "..." },
  "summary": { "total_revenue": 2100000, "total_commissions": 370000, "active_doctors": 2 },
  "doctors": [
    { "id": "...", "name": "Dr. López", "procedures_count": 42, "revenue": 1250000, "commission_pct": 20, "commission_amount": 250000 }
  ]
}
```

### State Management

**Local State (useState):**
- `dateRange: { from: Date, to: Date }`
- `selectedDoctorIds: string[]`

**Global State (Zustand):**
- None

**Server State (TanStack Query):**
- Query key: `['commissions-report', tenantId, dateRange, selectedDoctorIds]`
- Stale time: 5 minutes
- Refetch on filter change

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Change date range | Date picker | Report data refreshes | Loading overlay on chart + table |
| Filter by doctor | Multi-select | Report filtered to selected doctors | Other bars dim in chart |
| Sort table column | Click header | Toggle asc/desc | Arrow indicator |
| Click doctor name | Table row | Navigate to `/settings/team` (doctor section) | Standard navigation |
| Export CSV | Click button | GET export, download | Button spinner → file download |
| Hover chart bar | Mouse hover | Tooltip with full doctor details | Recharts tooltip |

### Animations/Transitions

- Chart bars: animate in on data load (Recharts `animationDuration=600`)
- KPI cards: count-up on load (framer-motion, 400ms)
- Filter change: chart + table overlay fade (150ms) while loading

---

## Loading & Error States

### Loading State
- KPI cards: 3 skeleton cards
- Chart: skeleton rectangle (chart area height, width)
- Table: 5 skeleton rows

### Error State
- API failure: error card spanning full content area "Error al cargar el reporte. Intenta de nuevo." with "Reintentar" button
- Export failure: toast "No se pudo exportar. Intenta de nuevo."

### Empty State
- No doctors with procedures in period: illustration + "Sin procedimientos en el período seleccionado" + "Cambiar período" button (opens date picker)
- Doctor filter with no data: "Ninguno de los doctores seleccionados tiene procedimientos en este período."

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | KPI cards: stacked vertically. Chart hidden (replaced by "Ver gráfica" toggle button). Table horizontal scroll. Export moved to header overflow menu. |
| Tablet (640-1024px) | KPI cards: 3-column. Chart full width. Table with 4 columns (revenue column hidden). |
| Desktop (> 1024px) | Full layout as described. Chart + table below KPIs. |

---

## Accessibility

- **Focus order:** Date range picker → doctor filter → KPI cards (read-only) → chart (description via aria-label) → table headers → table rows → export button
- **Screen reader:** Chart has `aria-label="Gráfica de comisiones por doctor para el período {from} a {to}"`. Table has `role="table"` with proper `scope` on headers. Totals row has `aria-label="Fila de totales"`.
- **Keyboard navigation:** Tab through filter controls and table. Chart not keyboard-interactive (data available in table).
- **Color contrast:** WCAG AA for all text and bar labels.
- **Language:** All labels, headers, tooltips in es-419.

---

## Design Tokens

**Colors:**
- Chart bars: `var(--color-primary-500)` primary, `var(--color-gray-200)` dimmed
- KPI card revenue: `text-primary-700`
- KPI card commission: `text-green-700`
- Totals row: `bg-gray-50 font-semibold`
- Commission amount column: `font-bold text-gray-900`

**Typography:**
- Page title: `text-2xl font-bold text-gray-900`
- KPI value: `text-2xl font-bold`
- KPI subtext: `text-sm text-gray-500`
- Table header: `text-xs font-medium uppercase tracking-wider text-gray-500`

**Spacing:**
- KPI card gap: `gap-4`
- Chart margin bottom: `mb-6`
- Section gap: `space-y-6`

---

## Implementation Notes

**Dependencies (npm):**
- `recharts` — horizontal BarChart
- `@tanstack/react-table` — sortable table
- `@tanstack/react-query` — data fetching
- `date-fns` — date formatting, period presets
- `lucide-react` — TrendingUp, DollarSign, Users, Download
- `framer-motion` — KPI count-up animation

**File Location:**
- Page: `src/app/(dashboard)/billing/commissions/page.tsx`
- Components: `src/components/billing/CommissionsBarChart.tsx`, `src/components/billing/CommissionsTable.tsx`, `src/components/billing/CommissionsFilterBar.tsx`
- Hooks: `src/hooks/useCommissionsReport.ts`
- API: `src/lib/api/billing.ts`

**Hooks Used:**
- `useAuth()` — restrict to clinic_owner
- `useQuery(['commissions-report', ...])` — report data
- `useQuery(['doctors'])` — doctor list for filter

---

## Test Cases

### Happy Path
1. View monthly commissions
   - **Given:** 2 doctors, each with recorded procedures in February 2026
   - **When:** User loads report for February 2026
   - **Then:** 2 bars in chart, 2 rows in table with correct commission amounts, KPI totals correct

2. Filter to one doctor
   - **Given:** Report shows 3 doctors
   - **When:** User selects only "Dr. López" in doctor filter
   - **Then:** Table shows 1 row, chart shows 1 bar, totals recalculate

### Edge Cases
1. Doctor with 0% commission
   - **Given:** A doctor has 0% commission rate
   - **When:** Report loads
   - **Then:** Row shows "0%" and "$0" in commission column. Included in report but visually distinct.

2. No procedures in date range
   - **Given:** User selects a date range with no appointments
   - **When:** Report loads
   - **Then:** Empty state with "Sin procedimientos en el período seleccionado"

### Error Cases
1. API timeout
   - **Given:** Backend slow on large report
   - **When:** Report loads
   - **Then:** After 30s: error state with "Reintentar" button

---

## Acceptance Criteria

- [ ] Date range filter with presets (mes actual, mes anterior, trimestre, año, personalizado)
- [ ] Doctor multi-select filter
- [ ] KPI cards: total revenue, total commissions, active doctors count
- [ ] Horizontal bar chart (Recharts) with commission per doctor; tooltip on hover
- [ ] Commissions table: doctor, procedures count, revenue, commission %, commission amount
- [ ] Table footer totals row
- [ ] Sortable table columns
- [ ] Export CSV (applies current filters)
- [ ] Loading skeletons (cards + chart + table)
- [ ] Empty state for no data period
- [ ] Error state with retry
- [ ] Restricted to clinic_owner (route guard)
- [ ] Responsive: stacked/simplified mobile, full layout desktop
- [ ] Accessibility: aria-label on chart, table ARIA, es-419

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
