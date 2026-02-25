# Analiticas de Pacientes (Patient Analytics) — Frontend Spec

## Overview

**Screen:** Patient analytics page with charts and metrics focused on patient demographics, growth, retention, and referral sources. Summary KPI cards at top. Charts: new patients trend (bar), retention rate (line), age distribution (histogram), gender (donut), referral sources (horizontal bar). Date range filter applies to all.

**Route:** `/analytics/patients`

**Priority:** Medium

**Backend Specs:** `specs/analytics/patient-stats.md` (AN-02)

**Dependencies:** `specs/frontend/analytics/analytics-dashboard.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Analytics dashboard → "Ver detalle de pacientes" link / KPI card click
- Sidebar under Analytics section

**Exit Points:**
- "Ver perfil del paciente" links in charts → `/patients/{id}`
- Breadcrumb → `/analytics`

**User Story:**
> As a clinic_owner, I want to understand my patient demographics and growth trends so that I can tailor my services and marketing to better serve my community.

**Roles with access:** `clinic_owner`, `superadmin`

---

## Layout Structure

```
+--------------------------------------------------+
|  Sidebar | Breadcrumb: Analiticas > Pacientes    |
|          | "Analiticas de Pacientes"              |
|          | [Date range filter]                    |
|          +---------------------------------------+
|          |  [Summary KPI Row: 3 cards]           |
|          +---------------------------------------+
|          |  [Chart: New Patients Trend (bar)]    |
|          +---------------------------------------+
|          |  [Chart: Retention Rate (line)] | [Age Dist. (histogram)] |
|          +---------------------------------------+
|          |  [Chart: Gender Donut] | [Referral Sources (h-bar)] |
+------------------------------------------+-------+
```

---

## UI Components

### Component 1: DateRangeFilter

**Type:** Date range selector (simplified vs main analytics — just start + end date inputs)

**Design:**
- `"Desde"` date input + `"Hasta"` date input in a `flex gap-3` row
- "Ultimos 30 dias" | "Ultimos 3 meses" | "Este año" quick preset chips
- "Aplicar" button triggers refetch

### Component 2: SummaryKPICards (3 cards)

| Card | Label | Value | Icon |
|------|-------|-------|------|
| 1 | Total Pacientes Activos | `{N}` | Users |
| 2 | Promedio Visitas / Paciente | `{N.N}` | CalendarCheck |
| 3 | Grupo de Edad Mas Comun | `"25-35 años"` | BarChart2 |

Each card: `bg-white rounded-2xl p-5 shadow-sm border border-gray-100` — same pattern as analytics dashboard KPI cards.

---

## Chart Specifications

### Chart 1: Nuevos Pacientes por Mes (Bar Chart)

**Type:** Vertical bar chart (monthly)
**Full width**
**Data:** Count of newly registered patients per month
**Bar:** `fill: #0D9488` with `fill-opacity: 0.85` hover `1.0`
**X-axis:** Month abbreviation in Spanish (ene, feb, mar...) + year if spanning multiple years
**Y-axis:** Patient count, integer ticks starting from 0
**Tooltip:** `"Febrero 2026: 24 nuevos pacientes"`
**Average line:** Dashed horizontal line at period average `stroke: #F59E0B` with legend label "Promedio: {N}"
**Height:** `h-64`

### Chart 2: Tasa de Retencion (Line Chart)

**Type:** Line chart — monthly retention rate %
**Width:** Left half (6/12 col on desktop, full width mobile)
**Definition shown:** Small info tooltip on chart title `"Pacientes que regresaron dentro de 90 dias de su ultima visita"`
**Lines:**
- "Retencion" — `stroke: #0D9488`
- Benchmark line at 60% — dashed `stroke: #9CA3AF` with legend "Meta: 60%"
**Y-axis:** 0-100% formatted as `"{n}%"`
**Tooltip:** `"Ene 2026: 72% de retencion"` with green/red indicator relative to 60% benchmark
**Height:** `h-56`

### Chart 3: Distribucion por Edad (Histogram)

**Type:** Histogram (vertical bar chart with age buckets)
**Width:** Right half (6/12 col on desktop, full width mobile)
**Age buckets:** 0-10, 11-18, 19-25, 26-35, 36-45, 46-55, 56-65, 65+
**Bar fill:** Gradient: darker for more common age groups (conditional formatting)
**Highlighted bar:** Most common group has `fill: #0D9488` others `fill: #99F6E4` (teal-200)
**X-axis:** Age range labels
**Y-axis:** Patient count
**Tooltip:** `"26-35 años: 87 pacientes (28%)"` `text-sm`
**Height:** `h-56`

### Chart 4: Distribucion por Genero (Donut Chart)

**Type:** Donut chart
**Width:** Left quarter (3/12 col) on desktop, full width mobile
**Segments:**

| Segment | Label | Color |
|---------|-------|-------|
| Masculino | Masculino | `#60A5FA` (blue) |
| Femenino | Femenino | `#F472B6` (pink) |
| Otro | Otro | `#A78BFA` (violet) |
| No especificado | No especificado | `#D1D5DB` (gray) |

**Center text:** `"Pacientes"` label + total count
**Legend:** Below chart, 2 columns, each: color dot + label + `{N} ({%})`
**Height:** `h-48` for donut

### Chart 5: Fuentes de Referencia (Horizontal Bar Chart)

**Type:** Horizontal bar chart
**Width:** Right three-quarters (9/12 col) on desktop, full width mobile
**Data:** Patient acquisition sources
**Sources (examples):**
- Recomendacion de paciente
- Google / Busqueda en internet
- Redes sociales
- Instagram
- WhatsApp
- Llamada directa
- Sin informacion

**Bar:** `fill: #0D9488` `h-7` with count label on right
**X-axis:** Count
**Y-axis:** Source name
**Height:** `h-64` (auto-adjusts for N sources)
**"Sin informacion"** shown last, dimmed `opacity-50`

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Get patient analytics | `/api/v1/analytics/patients` | GET | `specs/analytics/patient-stats.md` | 5min |

### Query Parameters

```
?from=2025-01-01
&to=2026-02-25
```

### State Management

**Local State:**
- `dateFrom: string`
- `dateTo: string`

**Server State (TanStack Query):**
- `useQuery({ queryKey: ['patient-analytics', from, to], staleTime: 5 * 60 * 1000 })`

---

## Interactions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Apply date range | Click "Aplicar" | Refetch all data | All charts skeleton briefly |
| Click age histogram bar | Click | Filter patient list → `/patients?age_from={min}&age_to={max}` | Navigation |
| Click referral source bar | Click | Filter patient list → `/patients?referral={source}` | Navigation |
| Hover any chart | Mouse/touch | Tooltip shown | Tooltip overlay |

---

## Loading & Error States

### Loading State
- Summary cards: `h-20 animate-pulse bg-gray-100 rounded-2xl` × 3
- Charts: `h-64 animate-pulse bg-gray-50 rounded-2xl` for each

### Error State
- Per-chart: inline "Error al cargar" + retry
- Global: banner + retry all

### Empty State
- New clinic with no patients: "Aun no hay datos de pacientes" with clinic stethoscope illustration + "Registra tus primeros pacientes" link to `/patients/new`

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Summary cards 1 column. All charts full-width stacked. Date filter inputs stacked. |
| Tablet (640-1024px) | Summary cards 3 columns. Retention + Age side by side. Gender + Referral side by side. |
| Desktop (> 1024px) | Full layout as described. |

---

## Accessibility

- **Screen reader:** Chart summary via `aria-label` on chart containers with key statistics (e.g., "Nuevos pacientes: promedio 24 por mes, mes mas alto: enero 2026 con 35"). Data table alternative accessible via toggle.
- **Keyboard:** Date inputs keyboard-navigable. Chart bars/segments reachable via Tab with tooltip on focus.
- **Color:** Gender donut uses text labels alongside colors. Histogram uses pattern fills as fallback for color-blind users.
- **Language:** All labels, axis values, tooltips in es-419.

---

## Design Tokens

Same as analytics dashboard. Additional:
- Benchmark line: `stroke: #9CA3AF` dashed
- Average line: `stroke: #F59E0B` dashed
- Retention above benchmark: `text-green-600` in tooltip
- Retention below benchmark: `text-red-500` in tooltip
- Most common age bar: `fill: #0D9488`
- Other age bars: `fill: #99F6E4`

---

## Implementation Notes

**Dependencies (npm):**
- `recharts` — BarChart, LineChart, PieChart, ResponsiveContainer

**File Location:**
- Page: `src/app/(dashboard)/analytics/patients/page.tsx`
- Components: `src/components/analytics/PatientAnalytics.tsx`, chart subcomponents in `src/components/analytics/charts/`

---

## Acceptance Criteria

- [ ] Date range filter with presets and custom range
- [ ] 3 summary KPI cards with active patients, avg visits, and most common age group
- [ ] New patients by month bar chart with average reference line
- [ ] Retention rate line chart with 60% benchmark line
- [ ] Age distribution histogram with highlighted most-common bucket
- [ ] Gender donut chart with legend and percentages
- [ ] Referral sources horizontal bar chart
- [ ] Chart bars clickable to filter patient list
- [ ] Loading skeletons and empty states
- [ ] Responsive layout for mobile, tablet, desktop
- [ ] Spanish (es-419) throughout with proper es-CO number formatting

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
