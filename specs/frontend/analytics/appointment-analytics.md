# Analiticas de Citas (Appointment Analytics) — Frontend Spec

## Overview

**Screen:** Appointment analytics page with four charts: utilization rate per doctor (horizontal bar), cancellation and no-show rates over time (dual line), peak hours heatmap (7-day x 24-hour grid), and average scheduled vs actual duration comparison (grouped bar). Date range filter applies globally.

**Route:** `/analytics/appointments`

**Priority:** Medium

**Backend Specs:** `specs/analytics/appointment-stats.md` (AN-03)

**Dependencies:** `specs/frontend/analytics/analytics-dashboard.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Analytics dashboard → "Ver detalle de citas" link
- Sidebar under Analytics section

**Exit Points:**
- Click doctor bar → filtered view for that doctor
- Breadcrumb → `/analytics`

**User Story:**
> As a clinic_owner, I want to understand appointment patterns — which hours are busiest, how much time is wasted on no-shows, and how efficiently each doctor uses their schedule — so that I can optimize operations.

**Roles with access:** `clinic_owner`, `superadmin`

---

## Layout Structure

```
+--------------------------------------------------+
|  Sidebar | Breadcrumb: Analiticas > Citas        |
|          | "Analiticas de Citas"                  |
|          | [Date range filter]                    |
|          +---------------------------------------+
|          |  [KPI: Total Citas] [Cancelaciones %] [No asistio %] [Util. promedio %] |
|          +---------------------------------------+
|          |  [Chart: Utilizacion por Doctor (h-bar)] |
|          +---------------------------------------+
|          |  [Chart: Cancelaciones + No-shows (dual line)] |
|          +---------------------------------------+
|          |  [Chart: Heatmap Horarios Pico]       |
|          +---------------------------------------+
|          |  [Chart: Duracion Programada vs Real] |
+------------------------------------------+-------+
```

---

## UI Components

### KPI Summary Row (4 cards)

| Card | Label | Value | Color |
|------|-------|-------|-------|
| 1 | Total Citas | `{N}` | teal |
| 2 | Tasa de Cancelacion | `{n}%` | amber if >15%, red if >25% |
| 3 | Tasa de No Asistencia | `{n}%` | amber if >10%, red if >20% |
| 4 | Utilizacion Promedio | `{n}%` | green if >80%, amber if 60-80%, red if <60% |

---

## Chart Specifications

### Chart 1: Tasa de Utilizacion por Doctor (Horizontal Bar)

**Type:** Horizontal bar chart
**Full width**
**Data:** Each doctor's schedule utilization % (booked time / available time)
**Bars:**
- Color coded: green `#10B981` if ≥ 80%, amber `#F59E0B` if 60-79%, red `#EF4444` if < 60%
- Bar label: `"{Dr. Nombre}: {n}%"` right-aligned on bar
**Reference line:** Vertical dashed line at 80% target `stroke: #9CA3AF`
**X-axis:** 0-100% with `%` suffix
**Y-axis:** Doctor names (truncated at 25 chars)
**Click on bar:** Filter appointments page for that doctor
**Tooltip:** `"Dr. Garcia: 87% de utilizacion — 156 citas de 179 disponibles"`

### Chart 2: Cancelaciones y No Asistencias (Dual Line)

**Type:** Line chart with two lines
**Full width**
**Data:** Weekly cancellation rate % and no-show rate % over selected period
**Lines:**
- "Cancelaciones" — `stroke: #F59E0B` (amber) `strokeWidth: 2`
- "No asistencias" — `stroke: #EF4444` (red) `strokeWidth: 2`
**Y-axis:** 0-50% formatted as `"{n}%"`, right-side label `"Tasa (%)"` rotated
**X-axis:** Week labels "Sem 1", "Sem 2" etc. or month if year view
**Shaded areas:** Fill below each line at 20% opacity matching line color
**Benchmark lines:** Dashed horizontal: `"Meta cancelaciones: 10%"` and `"Meta no asistencias: 5%"`
**Tooltip:** `"Semana 5 (Feb 1-7): Cancelaciones 12%, No asistencias 8%"`
**Legend:** Below chart, interactive — click to show/hide each line

### Chart 3: Horarios Pico — Heatmap

**Type:** Custom heatmap grid
**Full width**
**Grid:** 7 rows (Mon-Sun) × 24 columns (0:00-23:00) — only show 7:00-21:00 (14 cols) for clinic hours
**Cell:** `w-8 h-8 md:w-10 md:h-10 rounded`
**Color intensity:** 0 appointments = `bg-gray-50`, scale to max = `bg-teal-700`

**Color scale:**
- 0: `bg-gray-50`
- 1-25%: `bg-teal-100`
- 26-50%: `bg-teal-300`
- 51-75%: `bg-teal-500`
- 76-100%: `bg-teal-700`

**X-axis header:** Hour labels "7am", "8am" ... "9pm" — `text-xs text-gray-500`
**Y-axis labels:** Day abbreviations "Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom" — `text-xs text-gray-500`

**Tooltip on cell hover:**
- `"Lunes 10:00 AM: 24 citas (alta demanda)"` with color intensity badge

**Color scale legend:** Horizontal gradient bar below chart: "Baja demanda" → "Alta demanda" — `w-48 h-3 rounded-full` gradient + labels at each end

**Mobile:** Cells shrink to `w-6 h-6`, labels abbreviated, horizontally scrollable

### Chart 4: Duracion Programada vs Real (Grouped Bar)

**Type:** Grouped vertical bar chart
**Full width**
**Data:** Average duration scheduled vs actual for top 8 service types
**Bars per group:** 2 bars side by side per service type
- "Programada" — `fill: #99F6E4` (teal-200)
- "Real" — `fill: #0D9488` (teal-600)
**X-axis:** Service type names (rotated 45° on mobile)
**Y-axis:** Minutes `"{n} min"`
**Tooltip:** `"Limpieza — Programado: 30min, Real: 34min (+13%)"`
**Gap indicator:** If real > scheduled by >10%, red `!` icon above bar group with tooltip "Este servicio suele durar mas de lo programado. Considera ajustar la duracion."

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Get appointment analytics | `/api/v1/analytics/appointments` | GET | `specs/analytics/appointment-stats.md` | 5min |

### Query Parameters

```
?from=2025-01-01
&to=2026-02-25
```

### State Management

**Local State (useState):**
- `dateFrom: string`, `dateTo: string`

**Server State (TanStack Query):**
- `useQuery({ queryKey: ['appointment-analytics', from, to], staleTime: 5 * 60 * 1000 })`

---

## Interactions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click doctor utilization bar | Click | Navigate to `/agenda?doctor_id={id}&from={from}&to={to}` | Navigation |
| Click heatmap cell | Click/tap | Tooltip with detailed count | Popover |
| Toggle line chart series | Click legend | Hide/show line | Line fades out |
| Hover duration bar | Hover/touch | Tooltip with scheduled vs real | Tooltip |
| Apply date range | Click "Aplicar" | Refetch all | Charts skeleton |

---

## Loading & Error States

### Loading State
- KPI cards: 4 skeleton cards
- Charts: `h-64 animate-pulse bg-gray-50 rounded-2xl` for each
- Heatmap skeleton: `7×14` grid of `bg-gray-100 rounded animate-pulse` cells

### Error State
- Per-chart retry
- Global error banner

### Empty State
- No appointments in range: "Sin citas en el periodo seleccionado" with CalendarX icon per chart

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | All charts full-width stacked. Heatmap cells `w-6 h-6` with horizontal scroll. Duration chart x-labels rotated 45°. |
| Tablet (640-1024px) | Full layout. Heatmap cells standard size. |
| Desktop (> 1024px) | Same as tablet, wider containers. |

---

## Accessibility

- **Screen reader:** Heatmap: `role="grid"` + each cell `role="gridcell" aria-label="{day} {hour}: {count} citas"`. Charts have data table alternatives. Utilization bars color-coded + percentage text (not color alone).
- **Color blind:** Heatmap uses intensity gradient — also shows numeric count in tooltip. Lines have distinct strokes AND dashed patterns where needed.
- **Language:** es-419 throughout.

---

## Implementation Notes

**Dependencies (npm):**
- `recharts` — BarChart, LineChart, ResponsiveContainer
- Custom heatmap: plain CSS grid + React — no library needed for simple grid

**File Location:**
- Page: `src/app/(dashboard)/analytics/appointments/page.tsx`
- Components: `src/components/analytics/AppointmentAnalytics.tsx`, `src/components/analytics/charts/PeakHoursHeatmap.tsx`, `src/components/analytics/charts/DurationComparisonChart.tsx`

---

## Acceptance Criteria

- [ ] Date range filter applies to all charts simultaneously
- [ ] 4 KPI cards with color-coded thresholds
- [ ] Utilization per doctor horizontal bar with color coding and reference line
- [ ] Cancellation + no-show dual line chart with benchmark lines
- [ ] Peak hours heatmap 7-day × 14-hour grid with color intensity + tooltip
- [ ] Color scale legend for heatmap
- [ ] Scheduled vs actual duration grouped bar chart
- [ ] Gap warning indicator for over-budget service types
- [ ] All charts with loading skeletons and empty states
- [ ] Responsive: mobile-scrollable heatmap, full layout on tablet+
- [ ] Accessibility: grid ARIA on heatmap, data table alternatives
- [ ] Spanish (es-419) throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
