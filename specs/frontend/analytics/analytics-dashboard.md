# Dashboard de Analiticas (Analytics Dashboard) — Frontend Spec

## Overview

**Screen:** Main analytics dashboard for clinic management. Period selector at top drives all KPI cards and charts simultaneously. KPI cards show new patients, total appointments, revenue, and average revenue per patient. Charts include patient growth (line), appointment type distribution (donut), revenue trend (area), and top 10 procedures (horizontal bar). Responsive layout with mobile-friendly stacking.

**Route:** `/analytics`

**Priority:** High

**Backend Specs:** `specs/analytics/dashboard.md` (AN-01)

**Dependencies:** `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Sidebar "Analiticas" link
- Dashboard → "Ver reportes completos" link
- Admin notification linking to revenue analytics

**Exit Points:**
- "Ver detalle de pacientes" → `/analytics/patients`
- "Ver detalle de citas" → `/analytics/appointments`
- "Ver detalle de ingresos" → `/analytics/revenue`
- "Exportar datos" → triggers CSV download

**User Story:**
> As a clinic_owner | admin, I want to see a summary of my clinic's performance so that I can identify trends and make decisions about my practice.

**Roles with access:** `clinic_owner`, `superadmin`. `doctor` sees filtered view (own data only).

---

## Layout Structure

```
+--------------------------------------------------+
|  Sidebar | "Analiticas"                          |
|          | [Period selector]  [Exportar CSV btn]  |
|          +---------------------------------------+
|          |  [KPI Card 1] [KPI Card 2] [KPI Card 3] [KPI Card 4] |
|          +---------------------------------------+
|          |  [Chart: Patient Growth (line)]       |
|          |  [Chart: Appt Type Donut] [Revenue Trend (area)] |
|          |  [Chart: Top 10 Procedures (horizontal bar)]    |
+------------------------------------------+-------+
```

**Sections:**
1. Page header — title, period selector, export button
2. KPI cards row — 4 metric cards
3. Charts row 1 — patient growth line (full width)
4. Charts row 2 — donut (1/3) + area chart (2/3)
5. Charts row 3 — top 10 procedures horizontal bar (full width)

---

## UI Components

### Component 1: PeriodSelector

**Type:** Segmented control + custom date picker

**Options:**
- `hoy` | `semana` | `mes` | `trimestre` | `año` | `personalizado`

**Design:**
- Segmented control: `flex rounded-lg bg-gray-100 p-1 gap-1`
- Each option: `px-3 py-1.5 text-sm rounded-md font-medium`
- Active: `bg-white shadow-sm text-gray-900`
- Inactive: `text-gray-500 hover:text-gray-700`

**"Personalizado" selected:**
- Opens inline date range picker with "Desde" + "Hasta" date inputs
- Max range: 365 days
- Validation: start ≤ end ≤ today

**Period label for charts:** Each chart has a small `"Periodo: {period description}"` `text-xs text-gray-400` subtitle.

**URL persistence:** Period synced to URL params `?period=mes&from=2026-01-01&to=2026-01-31` for shareable links.

### Component 2: KPICard

**Type:** Metric card

**Layout:**
```
[Icon]  [Label]
        [Main value]  [Trend %]
        [Subtext]
```

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| label | string | Metric name |
| value | string | Formatted main value |
| trend | number | % change vs previous period |
| trendDirection | 'up' \| 'down' \| 'neutral' | Positive/negative context |
| subtext | string | Context line |
| icon | LucideIcon | Icon component |
| isLoading | boolean | Skeleton state |

**KPI Cards defined:**

| # | Label | Value format | Icon | Positive trend? |
|---|-------|-------------|------|-----------------|
| 1 | Nuevos Pacientes | `{N}` | UserPlus | Up |
| 2 | Total Citas | `{N}` | Calendar | Up |
| 3 | Ingresos | `$1.450.000` COP | DollarSign | Up |
| 4 | Ingreso Promedio por Paciente | `$85.000` COP | TrendingUp | Up |

**Trend display:**
- Positive: `+{n}%` `text-green-600` with `ArrowUpRight` icon
- Negative: `-{n}%` `text-red-500` with `ArrowDownRight` icon
- Neutral (0%): `"Sin cambios"` `text-gray-400`

**Loading state:** Skeleton `h-6 w-16 animate-pulse bg-gray-100 rounded` for value, `h-4 w-24` for label.

---

## Chart Specifications

### Chart 1: Crecimiento de Pacientes (Line Chart)

**Type:** Line chart — `recharts LineChart` or `chart.js`
**Full width:** `col-span-full`
**Data:** Monthly new patient count over the selected period
**Lines:**
- "Nuevos pacientes" — `stroke: #0D9488 (teal)` `strokeWidth: 2`
- "Pacientes recurrentes" (optional, toggle) — `stroke: #60A5FA (blue)` `strokeDasharray: 4 4`

**Features:**
- Interactive tooltips: "Febrero 2026: 24 nuevos pacientes"
- X-axis: month names abbreviated in Spanish
- Y-axis: patient count, integer ticks
- Legend below chart
- Responsive: chart height `h-64 md:h-80`
- Dot on data points: `r: 4` on hover shows enlarged dot + tooltip

### Chart 2: Distribucion de Tipos de Cita (Donut Chart)

**Type:** Donut chart
**Width:** `col-span-1 of 3` on desktop, full-width mobile
**Data:** Count of appointments by type (Consulta, Limpieza, Extraccion, etc.)
**Colors:** Palette of 8 colors from design system, cycling for more types
**Center text:** `"Total\n{N}"` — total appointment count
**Legend:** Below chart, 2-column, color dot + type name + count + %
**Tooltip:** Hover segment → shows type name + count + % of total

### Chart 3: Tendencia de Ingresos (Area Chart)

**Type:** Area chart
**Width:** `col-span-2 of 3` on desktop, full-width mobile
**Data:** Revenue per day or week depending on period length
**Series:**
- "Ingresos" — area fill `teal-100`, stroke `teal-600`
- "Presupuesto" (optional, if configured) — dashed line `gray-400`

**Features:**
- Y-axis: COP formatted with abbreviation `$1.4M`, `$850K`
- Gradient fill: `linearGradient` from `teal-200` at top to transparent at bottom
- Period comparison toggle: "Comparar con periodo anterior" checkbox — adds second dashed line for previous period

### Chart 4: Top 10 Procedimientos (Horizontal Bar Chart)

**Type:** Horizontal bar chart
**Full width:** `col-span-full`
**Data:** Top 10 procedures by count in selected period
**Bars:**
- `fill: #0D9488` with hover `fill: #0F766E`
- Bar height: `h-8` with gap
- X-axis: count (integer)
- Y-axis: procedure name (truncated at 30 chars)

**Labels on bars:** Count displayed inside bar if bar wide enough (`text-white text-sm`), outside if narrow (`text-gray-700 text-sm`)

**CUPS code:** Small `text-xs text-gray-400` CUPS code shown below procedure name on Y-axis

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Get dashboard metrics | `/api/v1/analytics/dashboard` | GET | `specs/analytics/dashboard.md` | 5min |
| Export CSV | `/api/v1/analytics/export` | GET | `specs/analytics/export.md` | None |

### Query Parameters

```
?period=mes
&from=2026-02-01
&to=2026-02-25
&doctor_id={uuid}    // optional, for filtered view
```

### State Management

**Local State (useState):**
- `period: 'hoy' | 'semana' | 'mes' | 'trimestre' | 'año' | 'personalizado'`
- `customFrom: string | null`
- `customTo: string | null`

**Global State (Zustand):**
- `analyticsStore.period` — persisted to `sessionStorage` for page refresh persistence

**Server State (TanStack Query):**
- `useQuery({ queryKey: ['analytics-dashboard', period, from, to, doctorId], staleTime: 5 * 60 * 1000 })`

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Select period | Click segment | All data refetches for new period | All charts/KPIs show skeleton briefly |
| Set custom range | Date inputs | Validates range, refetches | Same as above |
| Hover chart datapoint | Mouse/touch | Tooltip appears | Tooltip with formatted data |
| Toggle period comparison | Checkbox | Second line/area added to chart | Previous period data overlay |
| Click "Exportar CSV" | Button | Downloads CSV | "Generando exportacion..." toast |
| Click KPI card | Click | Navigate to detailed analytics page | Standard navigation |

### Chart Interactivity

- **Tooltips:** Follow mouse cursor (desktop) or show on tap (mobile) with formatted values
- **Zoom:** Period selector is primary zoom mechanism — no chart-level zoom
- **Legend:** Click legend items to show/hide corresponding series

---

## Loading & Error States

### Loading State

All KPI cards: skeleton cards `h-24 animate-pulse bg-gray-100 rounded-2xl`
Charts: placeholder `bg-gray-50 border border-gray-100 rounded-2xl` + centered `animate-spin Loader2 text-gray-300`
Loading text below spinner: `"Cargando datos..."` `text-xs text-gray-400`

### Error State

Per-chart error: `"Error al cargar este grafico"` within chart container + `RefreshCw` retry button
Global API error: banner above KPI cards + retry all

### Empty State

Period with no data: Charts show "Sin datos para este periodo" with relevant illustration
- Patient growth: outline of growing plant `text-gray-200 w-16 h-16`
- Message: `"No hay datos para el periodo seleccionado."` `text-sm text-gray-400`
- CTA: `"Selecciona un rango mas amplio"` link

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Period selector scrolls horizontally. KPI cards 2-column grid. Charts full-width stacked. Donut and area charts each full-width. Chart heights reduced `h-48`. |
| Tablet (640-1024px) | KPI cards 2x2 grid. Charts 2-column where specified. Period selector shows all options. |
| Desktop (> 1024px) | KPI cards 4-column row. Charts layout as specified above. `max-w-screen-xl` container. |

**Tablet priority:** High — clinic owners review analytics on tablets. Chart tooltips must work on touch with large enough touch targets.

---

## Accessibility

- **Focus order:** Period selector → Export button → KPI cards (4) → Charts (keyboard-navigable)
- **Screen reader:** Each KPI card `aria-label="Nuevos pacientes: {N}, {trend} vs periodo anterior"`. Period selector: `role="tablist"` + `aria-selected`. Charts: SVG charts need `title` and `desc` elements, or data table alternative accessible via `aria-details`.
- **Color contrast:** Chart colors chosen for sufficient contrast against white backgrounds. Donut chart legend uses text names alongside colors.
- **Data tables:** Each chart has an accessible data table view toggle `"Ver como tabla"` for screen readers.
- **Language:** Period labels, chart axis labels, tooltip values, and KPI labels in es-419.

---

## Design Tokens

**Colors:**
- KPI card icon: `text-teal-600` icon on `bg-teal-50` circle
- Trend positive: `text-green-600`
- Trend negative: `text-red-500`
- Chart primary: `#0D9488` (teal-600)
- Chart secondary: `#60A5FA` (blue-400)
- Chart grid lines: `stroke: #F3F4F6`
- Chart tooltip: `bg-white shadow-lg border border-gray-100 rounded-lg`

**Typography:**
- KPI value: `text-3xl font-bold font-inter text-gray-900`
- KPI label: `text-xs font-semibold uppercase tracking-wide text-gray-400`
- Chart label: `text-xs text-gray-500`
- Chart tooltip: `text-sm font-semibold text-gray-800`

**Spacing:**
- Page: `px-4 md:px-6 py-6`
- KPI grid gap: `gap-4`
- Chart section gap: `gap-4 mt-6`
- Chart card padding: `p-5`

---

## Implementation Notes

**Dependencies (npm):**
- `recharts` — all chart types (LineChart, PieChart, AreaChart, BarChart)
- `lucide-react` — UserPlus, Calendar, DollarSign, TrendingUp, ArrowUpRight, ArrowDownRight, Download, RefreshCw

**File Location:**
- Page: `src/app/(dashboard)/analytics/page.tsx`
- Components: `src/components/analytics/AnalyticsDashboard.tsx`, `src/components/analytics/PeriodSelector.tsx`, `src/components/analytics/KPICard.tsx`, `src/components/analytics/charts/PatientGrowthChart.tsx`, `src/components/analytics/charts/AppointmentTypeDonut.tsx`, `src/components/analytics/charts/RevenueTrendChart.tsx`, `src/components/analytics/charts/TopProceduresChart.tsx`

**Hooks Used:**
- `useQuery(['analytics-dashboard', period, from, to])` — main data fetch
- `useSearchParams` / `useRouter` — URL period persistence

---

## Test Cases

### Happy Path
1. Clinic owner views monthly analytics
   - **Given:** Clinic has 6 months of data
   - **When:** Owner selects "mes" period
   - **Then:** KPIs show current month totals, charts render with correct data and period labels

### Edge Cases
1. Custom range spanning only 1 day
   - **Given:** from = to = today
   - **When:** Period applied
   - **Then:** Charts show single-day data, line chart shows single point, area chart shows single bar

2. Doctor role (filtered view)
   - **Given:** User with role=doctor opens analytics
   - **When:** Data fetched with `doctor_id=me`
   - **Then:** All metrics scoped to that doctor's patients/appointments/revenue

### Error Cases
1. API returns no data for selected period
   - **Given:** Clinic is new, selected period is 2 years ago
   - **When:** Query returns empty dataset
   - **Then:** Empty state shown on each chart, KPI cards show "0" values

---

## Acceptance Criteria

- [ ] Period selector: hoy/semana/mes/trimestre/año/personalizado options
- [ ] Custom date range with validation
- [ ] Period synced to URL params
- [ ] 4 KPI cards with value, trend %, and icon
- [ ] Patient growth line chart with interactive tooltips
- [ ] Appointment type donut chart with legend
- [ ] Revenue trend area chart with optional period comparison
- [ ] Top 10 procedures horizontal bar chart
- [ ] All charts update when period changes
- [ ] Loading skeletons per card and chart
- [ ] Per-chart error states with retry
- [ ] Empty states for no-data periods
- [ ] Export CSV button
- [ ] Responsive: 2-col KPI on mobile, 4-col on desktop
- [ ] Accessibility: KPI aria-labels, chart data table alternatives
- [ ] Spanish (es-419) with proper number/currency formatting

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
