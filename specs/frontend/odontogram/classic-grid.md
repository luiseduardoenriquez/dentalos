# Odontograma Clasico (Cuadricula) — Frontend Spec

## Overview

**Screen:** Classic grid odontogram for Plan Free tenants. Displays 32 teeth in a 4-row rectangular grid, each tooth subdivided into 5 interactive zones. Conditions are applied by clicking zones directly, with a fixed right-hand panel showing tooth detail and condition selector.

**Route:** `/patients/{id}/odontogram` (when `tenant.odontogram_mode = "classic"`)

**Priority:** High

**Backend Specs:**
- `specs/odontogram/OD-01` — Get odontogram (fetch current state)
- `specs/odontogram/OD-02` — Update odontogram (save condition change)
- `specs/odontogram/OD-09` — Get condition catalog

**Dependencies:**
- `specs/frontend/patients/patient-header.md` — patient banner at top
- `specs/frontend/odontogram/condition-panel.md` (FE-OD-03) — condition selector panel
- `specs/frontend/odontogram/history-panel.md` (FE-OD-04) — change history log
- `specs/frontend/odontogram/toolbar.md` (FE-OD-07) — top toolbar

---

## User Flow

**Entry Points:**
- From patient detail page (`/patients/{id}`) — "Odontograma" tab
- Direct URL with patient ID if odontogram_mode is classic for this tenant

**Exit Points:**
- Navigate to another patient tab (historia, tratamientos, citas)
- Navigate back to patient list
- Print view triggered from toolbar

**User Story:**
> As a doctor or assistant, I want to view and annotate a patient's dental conditions on a grid odontogram so that I can quickly register findings during the clinical examination.

**Roles with access:** clinic_owner, doctor, assistant (read + write); receptionist (read-only)

---

## Layout Structure

```
+----------------------------------------------------------+
|  [Toolbar: FE-OD-07]                                     |
+----------------------------------------------------------+
|  [Patient Header Banner]                                  |
+----------------------------------+-----------------------+
|                                  |                       |
|   MAXILAR SUPERIOR               |   [ConditionPanel]    |
|   [ 18 17 16 15 14 13 12 11 ]    |   FE-OD-03            |
|   [ 21 22 23 24 25 26 27 28 ]    |                       |
|                                  |   Selected tooth #    |
|   MAXILAR INFERIOR               |   Zone: Oclusal       |
|   [ 48 47 46 45 44 43 42 41 ]    |   Condition: Caries   |
|   [ 31 32 33 34 35 36 37 38 ]    |   [Notes textarea]    |
|                                  |   [Registrar btn]     |
+----------------------------------+-----------------------+
|   [HistoryLog: FE-OD-04]  |  % sano | N hallazgos       |
+----------------------------------------------------------+
```

**Sections:**
1. Toolbar — mode toggle, zoom, print, snapshot, voice (FE-OD-07)
2. Patient header banner — name, DOB, insurance
3. Grid area — 4 rows of 8 teeth in labeled arch groups
4. Right panel (fixed, 280px) — ConditionPanel (FE-OD-03)
5. Bottom bar — PatientSummary (% sano, total hallazgos) + real-time HistoryLog (FE-OD-04)

---

## UI Components

### Component 1: ToothGridClassic

**Type:** Interactive SVG/div grid

**Design System Ref:** `frontend/design-system/design-system.md` Section 6 (Clinical Components)

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| teeth | Tooth[] | [] | Array of 32 tooth objects with zone conditions |
| selectedToothId | number \| null | null | Currently selected tooth (FDI number) |
| onZoneClick | (toothId, zone) => void | — | Handler when a zone is clicked |
| readOnly | boolean | false | Receptionist read-only mode |

**States:**
- Default — all zones colored by condition (or white for healthy)
- Zone hovered — subtle border highlight on hover
- Zone selected — active ring on selected zone; right panel updates
- Tooth selected — entire tooth card elevated with shadow
- Condition being painted — zone immediately repaints on click
- Loading — skeleton overlay on entire grid
- Read-only — no cursor change on hover, click disabled

**Behavior:**
- Click on zone → immediately calls `onZoneClick(toothId, zone)`
- Zone colors sourced from condition catalog (OD-09) color map
- No modal on click — condition applied via right panel selection
- Each tooth is labeled with its FDI number below the square
- Grid arranged: upper right (18→11), upper left (21→28), lower right (48→41), lower left (31→38)

---

### Component 2: ToothSquare

**Type:** Interactive SVG component

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| toothId | number | — | FDI tooth number |
| zones | ZoneConditions | — | Map of zone → condition_id |
| isSelected | boolean | false | Whether this tooth is selected |
| onZoneClick | (zone: ToothZone) => void | — | Zone click handler |
| readOnly | boolean | false | Disables interaction |

**Zones layout (cross pattern):**
```
     [V/Vestibular]
[M] [O/Oclusal]  [D]
     [L/Lingual]
```
- 5 zones: O (center), M (left), D (right), V (top), L (bottom — "L" for anteriors, "P" for posteriors)
- Each zone is a clickable area min 44px × 44px on tablet

**States:**
- Zone healthy: `bg-white border border-gray-200`
- Zone with condition: filled with condition color from catalog
- Zone hovered: `ring-2 ring-blue-400 ring-offset-1`
- Zone selected: `ring-2 ring-blue-600 ring-offset-2`

---

### Component 3: PatientSummary

**Type:** Stats bar

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| healthyPercent | number | — | % of zones with no condition |
| findingsCount | number | — | Total zones with any condition |
| lastUpdated | Date \| null | null | Timestamp of last change |

**Behavior:**
- Updates in real time as conditions are painted
- "% sano" recalculated as: `(healthy_zones / 160) × 100`

---

## Form Fields

Not applicable — conditions applied via click, not form submission.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Load odontogram | `/api/v1/patients/{id}/odontogram` | GET | `specs/odontogram/OD-01` | 2min stale |
| Save zone change | `/api/v1/patients/{id}/odontogram` | PATCH | `specs/odontogram/OD-02` | Invalidate on mutation |
| Load condition catalog | `/api/v1/odontogram/conditions` | GET | `specs/odontogram/OD-09` | 1 hour stale |

### State Management

**Local State (useState):**
- `selectedToothId: number | null` — currently selected tooth FDI number
- `selectedZone: ToothZone | null` — currently selected zone
- `pendingChange: { toothId, zone, conditionId } | null` — optimistic paint before save

**Global State (Zustand — useOdontogramStore):**
- `odontogramData: OdontogramState` — full 32-tooth condition map
- `conditionCatalog: Condition[]` — loaded once, shared with other components
- `selectedConditionId: string | null` — active condition in panel (FE-OD-03)
- `changeLog: ChangeEntry[]` — real-time history of changes in this session
- `isSaving: boolean` — save mutation in progress

**Server State (TanStack Query):**
- Query key: `['odontogram', patientId, tenantId]`
- Stale time: 2 minutes
- Mutation: `useMutation()` for PATCH zone update
  - Optimistic update: paint zone immediately, revert on error

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click zone | Click on tooth zone | Zone selected; right panel updates to show tooth + zone detail | Zone ring highlight |
| Select condition | Click condition in right panel (FE-OD-03) | Active condition set | Condition highlighted in panel |
| Click "Registrar" | Click in right panel | PATCH API call; zone color updates | Zone repaints; entry added to history log; toast "Guardado" |
| Keyboard shortcut 1-9 | Press number key | Selects corresponding condition | Condition panel updates active |
| Click tooth number label | Click FDI label | Selects full tooth (all zones shown in right panel) | Tooth elevated shadow |

### Animations/Transitions

- Zone color change: instant repaint (no animation — clinical use requires speed)
- Right panel slide: static — no animation to avoid distraction during examination
- HistoryLog new entry: slides in from bottom with 150ms ease-in
- Toast notification: bottom-right, 3-second auto-dismiss
- Skeleton loading: fade-in/out on 200ms

---

## Loading & Error States

### Loading State
- Skeleton overlay on grid area: 4 rows of 8 gray rectangles (`animate-pulse`)
- Right panel shows skeleton condition list
- Patient summary shows `-- %` and `-- hallazgos`

### Error State
- If odontogram load fails: full-page error in grid area with retry button
  - Icon: `AlertTriangle` (Lucide)
  - Message: "No se pudo cargar el odontograma. Intenta de nuevo."
  - CTA: "Reintentar" → re-runs query
- If save PATCH fails: toast error bottom-right
  - Message: "Error al guardar. El cambio no fue registrado."
  - Zone reverts to previous condition (optimistic rollback)

### Empty State
- Not applicable — odontogram always has 32 teeth (may all be healthy/no condition)
- First visit: all zones white with `condition = null`

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Hidden — odontogram not available on mobile. Redirect to patient summary page with message "El odontograma requiere una pantalla mas grande." |
| Tablet (640-1024px) | PRIMARY USE CASE. Right panel collapses to bottom drawer on landscape. Tooth squares: 48×48px minimum. Grid fills available width. Bottom summary hidden, accessible via swipe-up drawer. |
| Desktop (> 1024px) | Default layout — right panel fixed 280px. Grid centered with padding. |

**Tablet priority:** Critical — all touch targets minimum 44px. ToothSquare zones minimum 44×44px. Right panel usable with single thumb on landscape tablet.

---

## Accessibility

- **Focus order:** Toolbar controls → Tooth grid (left-to-right, top-to-bottom, FDI order) → Condition panel → Registrar button → Notes → History log
- **Screen reader:** Each ToothSquare has `aria-label="Diente {FDI}, zona {zone}, condicion: {condition_name}"`. Zone buttons have `role="button"` with descriptive labels. Grid has `role="grid"` with `aria-rowcount` and `aria-colcount`.
- **Keyboard navigation:** Arrow keys navigate between zones within a tooth. Tab moves to next tooth. Enter/Space selects a zone. Escape deselects. Number keys 1-9 select conditions.
- **Color contrast:** WCAG AA for all text labels. Condition zone colors include both fill color and an icon pattern for color-blind users.
- **Language:** All labels, tooltips, and messages in es-419. "MAXILAR SUPERIOR", "MAXILAR INFERIOR", zone names in Spanish (Oclusal, Mesial, Distal, Vestibular, Lingual/Palatino).

---

## Design Tokens

**Colors (Light theme):**
- Page background: `bg-gray-50`
- Grid card background: `bg-white`
- Tooth square border: `border-gray-300`
- Selected tooth: `shadow-lg ring-2 ring-blue-500`
- Healthy zone: `bg-white`
- Label text: `text-gray-500 text-xs font-mono`
- Arch label: `text-gray-700 text-sm font-semibold uppercase tracking-wide`

**Condition colors (from catalog OD-09):**
- Caries: `#EF4444` (red-500)
- Obturado: `#3B82F6` (blue-500)
- Corona: `#F59E0B` (amber-500)
- Ausente: `#6B7280` (gray-500) — zone crossed out
- Fractura: `#8B5CF6` (violet-500)
- (Full catalog from OD-09 API)

**Typography:**
- Arch labels: `text-sm font-semibold uppercase tracking-wider text-gray-600`
- FDI numbers: `text-xs font-mono text-gray-500`
- Summary stats: `text-2xl font-bold text-gray-800`

**Spacing:**
- Tooth gap: `gap-1` (4px between teeth)
- Row gap: `gap-3` (12px between upper/lower arches)
- Grid padding: `p-4 md:p-6`

**Border Radius:**
- Tooth squares: `rounded-sm`
- Right panel: `rounded-xl`

---

## Implementation Notes

**Dependencies (npm):**
- `zustand` — `useOdontogramStore` for shared state
- `@tanstack/react-query` — data fetching and optimistic mutations
- `lucide-react` — icons (AlertTriangle, CheckCircle, Clock)
- `framer-motion` — history log entry animation only

**File Location:**
- Page: `src/app/(dashboard)/patients/[id]/odontogram/page.tsx`
- Components: `src/components/odontogram/classic/ToothGridClassic.tsx`
- Components: `src/components/odontogram/classic/ToothSquare.tsx`
- Components: `src/components/odontogram/PatientSummary.tsx`
- Store: `src/stores/odontogramStore.ts`
- Types: `src/types/odontogram.ts`
- API: `src/lib/api/odontogram.ts`

**Hooks Used:**
- `useOdontogramStore()` — Zustand store
- `useQuery(['odontogram', patientId])` — load odontogram state
- `useQuery(['odontogram-conditions'])` — load condition catalog
- `useMutation()` — save zone change with optimistic update
- `useAuth()` — role check for read-only mode
- `useTenantPlan()` — verify odontogram_mode = classic (redirect if anatomic)

**Performance:**
- 160 interactive zone elements (32 teeth × 5 zones) must render without jank
- Use `React.memo` on `ToothSquare` to prevent unnecessary re-renders
- Condition color map pre-computed from catalog at mount time
- Optimistic updates avoid waiting for server round-trip before painting
- Virtualization not needed — 32 teeth always rendered

**Plan Gate:**
- If tenant plan allows anatomic mode (`plan >= Starter`) and `odontogram_mode = anatomic`, redirect to anatomic view (FE-OD-02). Classic is always available as fallback.

---

## Test Cases

### Happy Path
1. Doctor loads patient odontogram with existing conditions
   - **Given:** Patient has saved odontogram with caries on tooth 16 zone O
   - **When:** Doctor navigates to `/patients/{id}/odontogram`
   - **Then:** Grid loads with tooth 16 zone O painted red (caries color); patient summary shows correct findings count

2. Doctor clicks a zone and selects a condition
   - **Given:** Odontogram loaded, condition "Caries" selected in panel
   - **When:** Doctor clicks zone O on tooth 36
   - **Then:** Zone immediately paints red (optimistic); PATCH API fires; entry appears in history log; toast "Guardado" shows

3. Keyboard shortcut selects condition
   - **Given:** Right panel visible
   - **When:** Doctor presses key "1"
   - **Then:** First condition in catalog selected; highlighted in panel

4. Receptionist sees read-only view
   - **Given:** Logged in as receptionist
   - **When:** Navigate to odontogram
   - **Then:** Zones not clickable; "Registrar" button hidden; grid renders normally

### Edge Cases
1. Patient with no conditions (first visit)
   - **Given:** Odontogram exists but all zones are null
   - **When:** Load odontogram
   - **Then:** All zones white; "100% sano", "0 hallazgos"

2. Save fails — optimistic rollback
   - **Given:** PATCH returns 500
   - **When:** Doctor clicks zone to paint condition
   - **Then:** Zone briefly paints, then reverts; toast error shown; no history entry added

3. Condition catalog fails to load
   - **Given:** OD-09 endpoint returns error
   - **When:** Page loads
   - **Then:** Condition panel shows error state with retry; grid renders with existing conditions using cached colors

### Error Cases
1. Odontogram fetch fails (network error)
   - **Given:** OD-01 returns network error
   - **When:** Page loads
   - **Then:** Grid shows full error state; "No se pudo cargar el odontograma. Intenta de nuevo."

2. Access to wrong odontogram mode
   - **Given:** Tenant is configured as anatomic mode
   - **When:** URL is accessed directly
   - **Then:** Redirect to anatomic view route

---

## Acceptance Criteria

- [ ] Matches design spec — 4-row grid, FDI numbering, arch labels in Spanish
- [ ] All 32 teeth render with 5 interactive zones (160 total) — no jank on tablet
- [ ] Click zone → right panel updates immediately (no modal)
- [ ] Condition applied via "Registrar" in right panel — zone repaints and history entry added
- [ ] Optimistic updates: zone paints immediately, reverts on error
- [ ] Condition colors match OD-09 catalog
- [ ] PatientSummary: % sano and hallazgos count update in real time
- [ ] Keyboard shortcuts 1-9 select conditions
- [ ] Read-only mode for receptionist role (no editing)
- [ ] Plan gate: only shown when `odontogram_mode = classic`
- [ ] Loading skeleton rendered while data fetches
- [ ] Error state with retry for failed fetch
- [ ] Responsive: primary tablet layout with 44px min touch targets; mobile shows redirect message
- [ ] Accessibility: ARIA grid roles, keyboard navigation, screen reader labels
- [ ] All labels in Spanish (es-419)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
