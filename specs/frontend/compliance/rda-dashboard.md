# Panel de Cumplimiento RDA — Frontend Spec

## Overview

**Spec ID:** FE-CO-02

**Screen:** RDA compliance dashboard for Colombia Resolución 1888. Displays the clinic's overall compliance score as a circular gauge, a full requirement checklist grouped by category with pass/fail status per field, a prioritized gap analysis table, and an April 2026 regulatory deadline countdown. Each gap entry links directly to the record or patient that needs fixing.

**Route:** `/compliance/rda`

**Priority:** Critical (regulatory deadline April 2026)

**Backend Specs:**
- `specs/compliance/CO-05.md` — RDA status endpoint (compliance score, requirement checklist, gap list)

**Dependencies:**
- `FE-DS-01` (design tokens)
- `FE-DS-02` (button)
- `FE-DS-10` (card)
- `FE-DS-11` (badge)
- `FE-DS-14` (skeleton)
- `specs/frontend/compliance/rips-generator.md` (FE-CO-01 — sibling page, same sidebar section)

**Country gate:** Only visible for tenants with `country = "CO"`. Other country tenants see a "not available" card at this route with a note about country-specific compliance.

---

## User Flow

**Entry Points:**
- Sidebar: Cumplimiento → "RDA / Resolución 1888"
- Dashboard compliance widget → "Ver cumplimiento"
- Notification: "Tu clínica tiene {N} incumplimientos en RDA" → links here
- Compliance settings banner in clinical forms → "Ver estado RDA"

**Exit Points:**
- "Corregir" / "Ver afectados" links per gap → filtered patient/record list
- "Exportar reporte" → downloads PDF compliance report
- Breadcrumb → `/compliance` or `/dashboard`

**User Story:**
> As a clinic_owner or superadmin, I want to see my clinic's exact compliance level with Colombia's Resolución 1888, understand which specific fields are missing and in how many records, and navigate directly to fix them — so that I can reach full compliance before the April 2026 regulatory deadline.

**Roles with access:** `clinic_owner`, `superadmin`. Other roles redirect to `/dashboard` with toast "No tienes permiso para ver el panel de cumplimiento RDA."

---

## Layout Structure

```
+------------------------------------------+
|        Header (h-16)                     |
+--------+---------------------------------+
|        |  Cumplimiento > RDA             |
|        |  "Cumplimiento RDA —            |
|        |   Resolución 1888"  [Exportar]  |
| Side-  +---------------------------------+
|  bar   |  [Deadline Countdown Banner]    |
|        +---------------------------------+
|        |  [Score Gauge] + [Quick Stats]  |
|        +---------------------------------+
|        |  [Required Fields Checklist]   |
|        +---------------------------------+
|        |  [Gap Analysis Table]          |
+--------+---------------------------------+
```

**Sections:**
1. Page header — title, breadcrumb, "Exportar reporte" button
2. Deadline countdown — April 30, 2026 banner with days remaining
3. Compliance score — circular gauge + 3 quick-stat KPI cards
4. Required fields checklist — accordion by Resolución 1888 category, pass/fail per field
5. Gap analysis table — all gaps sorted by severity with fix links

---

## UI Components

### Component 1: DeadlineCountdown

**Type:** Alert banner — always visible at top of content area

**Design:** Full-width card, color shifts based on days remaining

**Content:**
```
+----------------------------------------------+
| 🕐  Plazo: 30 de abril de 2026               |
|     Quedan 64 días para cumplir con la       |
|     Resolución 1888                          |
+----------------------------------------------+
```

**Color by days remaining:**

| Days remaining | Background | Border | Text |
|---------------|------------|--------|------|
| > 60 days | `bg-amber-50` | `border-amber-200` | `text-amber-800` |
| 30–60 days | `bg-orange-50` | `border-orange-200` | `text-orange-800` |
| < 30 days | `bg-red-50` | `border-red-200` | `text-red-800` |
| 0 days (deadline passed) | `bg-red-100` | `border-red-400` | `text-red-900` bold |

**Computed client-side:**
```typescript
const DEADLINE = new Date('2026-04-30T23:59:59-05:00'); // Colombia TZ
const daysRemaining = Math.ceil((DEADLINE.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
```

**Left:** `Clock` icon + `"Plazo: 30 de abril de 2026"` in `text-sm font-semibold`
**Right:** `"{N} días"` in `text-3xl font-bold` + `"para cumplir"` in `text-xs` below
**Accessibility:** `role="timer"` with `aria-label="Quedan {N} días para el plazo de la Resolución 1888"`. No `aria-live` — static count, not ticking.

---

### Component 2: ComplianceScoreGauge

**Type:** Half-circle SVG gauge

**Dimensions:** Container `w-48 h-24` (half-circle). `viewBox="0 0 200 100"`.

**SVG Implementation:**

```typescript
// Half circle: 180° arc, left to right, top center origin
const RADIUS = 80;
const CIRCUMFERENCE = Math.PI * RADIUS; // = 251.3px for 180°
const strokeDasharray = CIRCUMFERENCE;
const strokeDashoffset = CIRCUMFERENCE * (1 - score / 100); // 0 = full, CIRCUMFERENCE = empty

// Animate on mount: dashOffset from CIRCUMFERENCE to calculated value, 1.5s ease-out
```

**Gauge layers:**
1. Background track arc: `stroke="#E5E7EB"` (gray-200), `strokeWidth=16`, `strokeLinecap="round"`
2. Score arc: color per range (see table), `strokeWidth=16`, `strokeLinecap="round"`, animated
3. Center text (below gauge center point): score percentage `text-4xl font-bold font-mono`
4. Level label: `text-sm font-medium` in matching color

**Score color ranges:**

| Range | Arc color | Hex | Label |
|-------|-----------|-----|-------|
| 0–49% | red | `#EF4444` | "Crítico" |
| 50–69% | orange | `#F97316` | "En progreso" |
| 70–84% | amber | `#F59E0B` | "Aceptable" |
| 85–100% | green | `#10B981` | "Conforme" |

**Accessibility:**
```html
<div role="img" aria-label="Puntaje de cumplimiento RDA: {score}%, nivel: {label}">
```

**States:**
- Loading: gray arc `animate-pulse`, center shows `"--"`
- Loaded: arc animates from 0 to score over 1.5s ease-out on mount

---

### Component 3: QuickStatsRow

**Type:** 3 compact KPI cards beside the gauge

**Layout:** `flex gap-4` — gauge left ~50%, stats cards right ~50% on desktop; stacked on mobile

| Card | Label (es-419) | Value source |
|------|----------------|-------------|
| 1 | Requisitos cumplidos | `"{met} / {total}"` from CO-05 |
| 2 | Expedientes con errores | `"{N} expedientes"` |
| 3 | Campos faltantes | `"{N} campos"` |

**Card style:** `bg-white border border-gray-200 rounded-lg p-4`, metric in `text-2xl font-bold`, label in `text-xs text-gray-500`

---

### Component 4: RequiredFieldsChecklist

**Type:** Accordion — grouped by Resolución 1888 category

**Title:** `"Requisitos de la Resolución 1888"` `text-lg font-semibold`

**Categories and requirements (from CO-05 response):**

| Category | Requirements count |
|----------|--------------------|
| Identificación del Paciente | 5 |
| Anamnesis y Antecedentes | 4 |
| Examen Clínico | 6 |
| Odontograma | 3 |
| Plan de Tratamiento | 4 |
| Consentimiento Informado | 3 |
| Evolución Clínica | 5 |

**Category accordion header:**
```
[ChevronDown] Examen Clínico    [AlertCircle amber] 4/6 cumplidos    [Expand]
```
- Header: `flex items-center justify-between p-4 cursor-pointer`
- Status summary: `"{met}/{total} cumplidos"` in colored text based on category compliance %
- Default behavior: categories with any failing items are **expanded** by default; fully compliant categories are collapsed

**Each requirement row:**
```
[Status icon]  [Requirement description]         [% — N/N]  [Afectados →]
[CheckCircle2] "Nombre completo del paciente"    100%        —
[AlertCircle]  "Diagnóstico codificado CIE-10"   72%         [Ver 8 →]
[XCircle]      "Firma digital del profesional"   0%          [Ver 24 →]
```

**Status icon + row style per compliance %:**

| % compliance | Icon | Icon color | Row style |
|-------------|------|------------|-----------|
| ≥ 90% | `CheckCircle2` | `text-green-500` | `text-gray-700` (normal weight) |
| 50–89% | `AlertCircle` | `text-amber-500` | `text-amber-700` |
| < 50% | `XCircle` | `text-red-500` | `text-red-700 font-medium` |

**"Afectados" link:** `text-teal-600 text-xs underline hover:text-teal-800` → navigates to `/patients?missing_field={field_id}` (pre-filtered patient list showing only patients with this gap). Link hidden when affected_count = 0.

**Requirement description examples (from Resolución 1888):**
- "Nombre completo del paciente en todas las consultas"
- "Número de documento con tipo especificado (CC, TI, CE, etc.)"
- "Fecha de nacimiento registrada"
- "Odontograma actualizado en cada evolución clínica"
- "Firma del paciente en consentimiento informado"
- "Diagnóstico codificado con CIE-10"
- "Procedimientos codificados con CUPS"
- "Anotaciones de evolución con firma digital del profesional"
- "Anamnesis completa registrada en primera consulta"
- "Examen clínico extraoral e intraoral documentado"

**Expand/collapse animation:** `max-height` transition 300ms ease-in-out. Chevron rotates 180°.

---

### Component 5: GapAnalysisTable

**Title:** `"Brechas de Cumplimiento"` + subtitle `"Ordenado por impacto"` `text-sm text-gray-500`

**Columns:**

| Column | Header (es-419) | Width | Content |
|--------|-----------------|-------|---------|
| severity | Severidad | 110px | Badge (see below) |
| gap | Brecha | flex-1 | Description of the missing field/record |
| affected | Expedientes afectados | 150px | `"{N} expedientes"` or `"{N} pacientes"` |
| action | Acción | 100px | "Corregir" outline button |

**Severity badges:**

| Level | Badge classes | Meaning |
|-------|--------------|---------|
| `critico` | `bg-red-100 text-red-700` | Blocks compliance score exceeding 60%. Fix immediately. |
| `alto` | `bg-orange-100 text-orange-700` | Significant compliance impact |
| `medio` | `bg-amber-100 text-amber-700` | Moderate impact, affects score 5–15% |
| `bajo` | `bg-gray-100 text-gray-600` | Best practice / minor impact |

**Sort order:** Default by severity (`critico` first), then by `affected_count` descending within each severity group.

**"Corregir" button:**
- Style: `text-xs text-teal-600 border border-teal-300 px-3 py-1 rounded hover:bg-teal-50`
- Click: navigates to `gap.fix_link` from CO-05 response (e.g., `/patients?missing_field=cie10_missing`)
- Rows with 0 affected: **not shown** (filtered client-side before render)

**"Todo completo" empty state (score = 100%):**
```
+----------------------------------------------+
| 🎉  ¡Tu clínica cumple completamente         |
|     con la Resolución 1888!                  |
|     Todos los requisitos están al día.       |
+----------------------------------------------+
```
`bg-green-50 border border-green-200 rounded-xl p-6 text-center text-green-700`
Icon: `PartyPopper` from Lucide

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Get RDA compliance status | `GET /api/v1/compliance/rda` | GET | `specs/compliance/CO-05.md` | 5min stale |
| Export PDF report | `GET /api/v1/compliance/rda/report.pdf` | GET | `specs/compliance/CO-05.md` | None |

**CO-05 Response shape:**

```typescript
interface RdaComplianceResponse {
  score: number;                   // 0–100 overall compliance score
  score_level: 'critico' | 'en_progreso' | 'aceptable' | 'conforme';
  requirements_met: number;        // e.g., 24
  requirements_total: number;      // e.g., 30
  records_with_errors: number;
  missing_fields_count: number;
  last_updated_at: string;         // ISO datetime
  requirements: RequirementCategory[];
  gaps: GapItem[];
}

interface RequirementCategory {
  id: string;
  name_es: string;                 // "Identificación del Paciente"
  items: RequirementItem[];
}

interface RequirementItem {
  id: string;
  description_es: string;
  compliance_pct: number;          // 0–100
  affected_count: number;
  affected_link: string;           // "/patients?missing_field={id}"
}

interface GapItem {
  description_es: string;
  affected_count: number;
  severity: 'critico' | 'alto' | 'medio' | 'bajo';
  fix_link: string;                // "/patients?missing_field={id}" or specific record URL
}
```

### State Management

**Local State (useState):**
- `expandedCategories: Set<string>` — open accordion categories (initialized with failing category IDs)

**Server State (TanStack Query):**
- Query key: `['rda-compliance', tenantId]`
- Stale time: 5 minutes
- `refetchOnWindowFocus: false`
- PDF export: `useMutation` → triggers blob download via `URL.createObjectURL`

**URL State:**
- `?expanded=identificacion,examen` — persists which categories the user has opened/closed (comma-separated category IDs)

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Page load | Mount | Fetch CO-05; gauge animates to score | 1.5s arc animation; skeletons during load |
| Click category header | Click | Expand/collapse requirement rows | Chevron rotates, max-height transition |
| Click "Afectados" link | Click | Navigate to filtered patients | Standard navigation |
| Click "Corregir" | Click | Navigate to fix_link URL | Standard navigation |
| Click "Exportar reporte" | Click | GET PDF, trigger download | Toast "Generando reporte..." → download |
| Click stats card (future) | — | Not interactive in v1.0 | — |

### Animations/Transitions

- Gauge arc: stroke-dashoffset animates from full-empty to score value in 1.5s ease-out on mount
- Category accordion: `max-height` 300ms ease-in-out; chevron `rotate-180` 200ms
- Page entry: `animate-fade-in` 400ms on the score + checklist sections
- "Exportar" loading: spinner in button replaces Download icon

---

## Loading & Error States

### Loading State

On initial fetch (skeletons match content layout):
- Deadline banner: visible immediately (client-computed, no API needed)
- Gauge: `w-48 h-24 rounded-full bg-gray-200 animate-pulse` circular placeholder
- Quick stats: 3 `h-20 w-32 rounded-lg bg-gray-100 animate-pulse` cards
- Checklist: 7 `h-14 rounded-lg bg-gray-100 animate-pulse mb-2` accordion skeleton items
- Gap table: 5 `h-12 rounded bg-gray-100 animate-pulse mb-2` skeleton rows

### Error State

- CO-05 fetch fails: error card replaces gauge + checklist area
  - Icon: `AlertOctagon` red
  - Message: "No pudimos cargar el reporte de cumplimiento. Intenta de nuevo."
  - Button: "Reintentar" — re-triggers `useQuery` refetch
- PDF export fails: toast error "No se pudo generar el reporte. Intenta de nuevo."

### Empty State (perfect compliance)

Gap table replaced by success banner (see GapAnalysisTable Component above). Checklist shows all `CheckCircle2` green icons. Gauge at 100% green arc.

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Gauge centered full-width (w-full h-auto, smaller SVG). Quick stats stacked below gauge as 3 full-width cards. Checklist full width. Gap table: hide "Expedientes afectados" column, show in expanded sub-row. "Exportar" button full width at top. |
| Tablet (640–1024px) | Gauge + quick stats in `flex gap-6` row (gauge 40%, stats 60%). Full checklist and gap table. All table columns visible. |
| Desktop (> 1024px) | `max-w-5xl` centered content area. Gauge + stats same as tablet. Gap table with all columns. |

**Tablet priority:** High — clinic owners review compliance reports on tablets. All accordion headers min 44px. "Corregir" buttons min 44px height. Chevrons large enough for touch.

---

## Accessibility

- **Focus order:** Deadline countdown → Export button → Score gauge (read-only) → Quick stats → Checklist accordion headers (in category order) → "Afectados" links → Gap table rows → "Corregir" buttons
- **Screen reader:**
  - Deadline banner: `role="timer"` with `aria-label="Quedan {N} días para el plazo de la Resolución 1888"`; static value, not live-updating
  - Score gauge: `role="img"` with `aria-label="Puntaje de cumplimiento RDA: {score}%, nivel: {label}"`
  - Category accordions: `aria-expanded` on trigger button; `aria-controls` pointing to content div
  - Requirement rows: pass/fail icons have `aria-label="Cumplido"` / `"Parcialmente cumplido"` / `"Incumplido"` (not relying on color or icon shape alone)
  - Gap table: `<table>` with proper `<th scope="col">` headers
  - "Afectados" links: `aria-label="Ver {N} expedientes afectados por: {requirement_name}"`
- **Keyboard:** Tab through all interactive elements. Enter/Space on accordion headers. Focus trapped to expanded category sections on open.
- **Color:** Gauge uses arc color + percentage text + text label. Severity badges use color + text label. Pass/fail uses icon + color + text percentage. Never color alone.
- **Language:** All regulatory terminology in es-419. Resolución 1888 category names match official document language.

---

## Design Tokens

**Colors:**
- Gauge critical: `#EF4444` (red-500)
- Gauge en_progreso: `#F97316` (orange-500)
- Gauge aceptable: `#F59E0B` (amber-500)
- Gauge conforme: `#10B981` (green-500)
- Deadline > 60 days: `bg-amber-50 border-amber-200 text-amber-800`
- Deadline 30–60 days: `bg-orange-50 border-orange-200 text-orange-800`
- Deadline < 30 days: `bg-red-50 border-red-200 text-red-800`
- Check pass: `text-green-500`
- Check partial: `text-amber-500`
- Check fail: `text-red-500`
- Category header bg: `bg-gray-50 hover:bg-gray-100 dark:bg-gray-800/50`
- Requirement row hover: `hover:bg-gray-50`
- "Corregir" button: `border-teal-300 text-teal-600 hover:bg-teal-50`
- "Afectados" link: `text-teal-600 hover:text-teal-800`

**Typography:**
- Page heading: `text-2xl font-bold text-gray-900 dark:text-gray-100`
- Score percentage: `text-4xl font-bold font-mono`
- KPI value: `text-2xl font-bold`
- KPI label: `text-xs text-gray-500`
- Category name: `text-sm font-semibold text-gray-800`
- Requirement text: `text-sm text-gray-700`
- Compliance %: `text-xs text-gray-500 tabular-nums`

**Spacing:**
- Page padding: `px-4 py-6 md:px-6 lg:px-8`
- Section gap: `space-y-6`
- Card padding: `p-6`
- Accordion item: `p-4`
- Table cell: `py-3 px-4`

---

## Implementation Notes

**Dependencies (npm):**
- `framer-motion` — accordion max-height transition, gauge arc animation on mount
- `lucide-react` — CheckCircle2, AlertCircle, XCircle, Clock, Download, PartyPopper, ChevronDown, AlertOctagon
- `@tanstack/react-query` — server state
- `date-fns` — deadline countdown computation with `es` locale

**File Location:**
- Page: `src/app/(dashboard)/compliance/rda/page.tsx`
- Components:
  - `src/components/compliance/DeadlineCountdown.tsx`
  - `src/components/compliance/ComplianceScoreGauge.tsx`
  - `src/components/compliance/QuickStatsRow.tsx`
  - `src/components/compliance/RequiredFieldsChecklist.tsx`
  - `src/components/compliance/CategoryAccordion.tsx`
  - `src/components/compliance/GapAnalysisTable.tsx`
- Hook: `src/hooks/useRdaCompliance.ts`
- API: `src/lib/api/compliance.ts`
- Types: `src/types/compliance.ts`

**Hooks Used:**
- `useAuth()` — role check (clinic_owner, superadmin only) + country check (CO only)
- `useQuery(['rda-compliance', tenantId])` — main CO-05 fetch
- `useMutation()` — PDF export download
- `useSearchParams()` — expanded category URL state

**Gauge SVG implementation detail:**

```typescript
// src/components/compliance/ComplianceScoreGauge.tsx
const RADIUS = 80;
const CIRCUMFERENCE = Math.PI * RADIUS; // 180° half-circle

// SVG path: semicircle arc from (-R, 0) to (R, 0) through top
const arcPath = `M ${cx - RADIUS} ${cy} A ${RADIUS} ${RADIUS} 0 0 1 ${cx + RADIUS} ${cy}`;

// Motion value for animated stroke-dashoffset
const dashOffset = CIRCUMFERENCE * (1 - score / 100);
// Animated with framer-motion: initial=CIRCUMFERENCE, animate=dashOffset, transition={duration:1.5, ease:"easeOut"}
```

**Default expanded category IDs:** On mount, after CO-05 loads, automatically expand any category where at least one requirement has `compliance_pct < 90`. This gives clinic owners an immediate view of problem areas without requiring interaction.

---

## Test Cases

### Happy Path

1. Dashboard loads with 72% compliance (aceptable)
   - **Given:** CO-05 returns score=72, level="aceptable", 3 critical gaps, 2 categories with failures
   - **When:** clinic_owner navigates to `/compliance/rda`
   - **Then:** Deadline banner shows days remaining (amber); gauge animates to 72% amber arc; "Aceptable" label shown; 2 failing categories auto-expanded; gap table shows 3 critical rows first

2. Expand passing category (collapsed by default)
   - **Given:** "Identificación del Paciente" has 100% compliance (5/5 met)
   - **When:** User clicks the accordion header
   - **Then:** Requirements reveal showing 5 green CheckCircle2 rows; no "Afectados" links shown

3. Click "Afectados" link
   - **Given:** Requirement "Diagnóstico CIE-10" has 8 affected records
   - **When:** User clicks "Ver 8 →"
   - **Then:** Navigates to `/patients?missing_field=cie10_missing` (from requirement.affected_link)

4. Click "Corregir" in gap table
   - **Given:** Gap "Firma digital del profesional — 24 expedientes" in critical severity
   - **When:** User clicks "Corregir"
   - **Then:** Navigates to gap.fix_link (e.g., `/patients?missing_field=digital_signature`)

5. Export compliance report
   - **Given:** Compliance data loaded
   - **When:** User clicks "Exportar reporte"
   - **Then:** Toast "Generando reporte..." shown; PDF downloads; toast clears

### Edge Cases

1. Score = 100% (full compliance)
   - **Given:** All 30 requirements at 100%
   - **When:** Page loads
   - **Then:** Gauge shows 100% green arc; gap table replaced by celebration banner; all 7 categories collapsed with green summary; "Exportar reporte" still available

2. Deadline passed (after April 30, 2026)
   - **Given:** `daysRemaining <= 0`
   - **When:** Banner computes days
   - **Then:** Banner shows `"El plazo de la Resolución 1888 ha vencido"` in `bg-red-100 border-red-400 font-bold text-red-900`; days counter shows "0 días" or hides

3. Category with 0/N compliance (all failing)
   - **Given:** "Consentimiento Informado" has 0% on all 3 requirements
   - **When:** Page loads
   - **Then:** All 3 rows show XCircle red, `font-medium` text; all 3 have "Afectados" links; category header shows "0/3 cumplidos" in red

4. Non-CO tenant accesses route
   - **Given:** `tenant.country = "MX"`
   - **When:** User navigates to `/compliance/rda`
   - **Then:** Page renders a "not available" card: "El panel RDA es específico para Colombia. Para México, consulta las normas de cumplimiento locales en configuración." No API call made.

### Error Cases

1. CO-05 returns 500
   - **Given:** Backend compliance engine error
   - **When:** Page loads
   - **Then:** Skeleton replaced by error card with "Reintentar" button; deadline countdown still visible (client-only)

2. PDF export fails (network error)
   - **Given:** Export endpoint returns 503
   - **When:** User clicks "Exportar reporte"
   - **Then:** Toast error "No se pudo generar el reporte. Intenta de nuevo."; spinner reverts to Download icon

---

## Acceptance Criteria

- [ ] Accessible only to clinic_owner and superadmin; other roles redirected
- [ ] Country gate: CO only; non-CO tenants see informational card, no API call
- [ ] April 2026 deadline countdown with color-coded urgency (amber > 60 days, orange 30–60, red < 30)
- [ ] Compliance score gauge animates arc from 0 to score on mount (1.5s ease-out)
- [ ] Gauge color matches score range: red / orange / amber / green
- [ ] "Nivel: {label}" below gauge in matching color
- [ ] 3 quick-stat KPI cards: requirements met, expedientes con errores, campos faltantes
- [ ] Checklist accordion with 7 Resolución 1888 categories
- [ ] Categories with failing items auto-expanded on page load
- [ ] Each requirement shows status icon (check/alert/x), description, %, and "Afectados" link
- [ ] "Afectados" link hidden when affected_count = 0
- [ ] Gap analysis table sorted by severity (critico first, then by affected count)
- [ ] Severity badges with correct color coding (red/orange/amber/gray)
- [ ] "Corregir" navigates to fix_link from API response
- [ ] Rows with 0 affected records not shown in gap table
- [ ] 100% compliance: celebration banner + no gap table
- [ ] "Exportar reporte" downloads compliance PDF
- [ ] Loading skeletons for gauge, stats, checklist, and gap table
- [ ] Error state with retry when CO-05 fails
- [ ] URL state: expanded categories survive page refresh
- [ ] Responsive: mobile stacked, tablet/desktop side-by-side gauge + stats
- [ ] All ARIA roles and attributes correct (role=timer, role=img, aria-expanded)
- [ ] All text in es-419 with correct Resolución 1888 regulatory terminology

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec — full Colombia Resolución 1888 compliance dashboard |
