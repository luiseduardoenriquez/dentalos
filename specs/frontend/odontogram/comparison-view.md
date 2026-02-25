# Vista de Comparacion de Odontogramas — Frontend Spec

## Overview

**Screen:** Side-by-side snapshot comparison view for odontograms. Renders two odontogram snapshots simultaneously and highlights visual differences: added conditions (green border), removed conditions (red border), and changed conditions (yellow border). Includes a date range slider to select which snapshots to compare.

**Route:** `/patients/{id}/odontogram/comparison`

**Priority:** Medium

**Backend Specs:**
- `specs/odontogram/OD-08` — Get odontogram snapshots list and snapshot data

**Dependencies:**
- `specs/frontend/odontogram/classic-grid.md` (FE-OD-01) — rendered as read-only grid per snapshot
- `specs/frontend/odontogram/anatomic-arch.md` (FE-OD-02) — read-only arch per snapshot (if plan >= Starter)
- `specs/frontend/odontogram/toolbar.md` (FE-OD-07) — toolbar with snapshot button

---

## User Flow

**Entry Points:**
- From toolbar snapshot button → after taking a snapshot, prompt "Ver comparacion"
- From patient odontogram view → toolbar "Comparar" button
- Direct navigation to `/patients/{id}/odontogram/comparison`

**Exit Points:**
- "Volver al odontograma" button → navigates back to `/patients/{id}/odontogram`
- Navigate to patient tabs (historia, tratamientos, citas)

**User Story:**
> As a doctor or clinic owner, I want to compare two snapshots of a patient's odontogram side by side so that I can evaluate treatment progress and document condition changes over time.

**Roles with access:** clinic_owner, doctor (read); assistant (read); receptionist (read)

---

## Layout Structure

```
+----------------------------------------------------------+
|  [Toolbar: Volver | Paciente: Juan Lopez | Comparar]     |
+----------------------------------------------------------+
|  [SnapshotSelector] — date slider / dropdown pickers     |
|  Snapshot A: [15 ene 2026 ▼]    Snapshot B: [15 feb ▼]  |
+---------------------------+------------------------------+
|  SNAPSHOT A               |  SNAPSHOT B                  |
|  15 ene 2026              |  15 feb 2026                 |
|  Dr. Martinez             |  Dra. Lopez                  |
|                           |                              |
|  [Odontogram Grid/Arch    |  [Odontogram Grid/Arch       |
|   Read-only, left panel]  |   Read-only, right panel]   |
|                           |                              |
+---------------------------+------------------------------+
|  [DiffLegend] ■ Agregado  ■ Eliminado  ■ Modificado     |
+----------------------------------------------------------+
|  [DiffSummary: N cambios total — list of changed teeth]  |
+----------------------------------------------------------+
```

**Sections:**
1. Top bar — back button, patient name, page title "Comparacion de Odontogramas"
2. SnapshotSelector — date pickers or slider for Snapshot A and B
3. Left panel — Snapshot A (read-only odontogram at selected date)
4. Right panel — Snapshot B (read-only odontogram at selected date)
5. Diff legend — color key: green=agregado, red=eliminado, yellow=modificado
6. Diff summary — list of all detected changes between the two snapshots

---

## UI Components

### Component 1: SnapshotSelector

**Type:** Date comparison control

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.3 (Selects / Pickers)

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| snapshots | Snapshot[] | [] | List of available snapshots (date + author) |
| snapshotAId | string \| null | null | Currently selected left snapshot ID |
| snapshotBId | string \| null | null | Currently selected right snapshot ID |
| onSelectA | (id: string) => void | — | Handler for left snapshot selection |
| onSelectB | (id: string) => void | — | Handler for right snapshot selection |

**Layout:**
- Two side-by-side dropdowns labeled "Snapshot A (antes)" and "Snapshot B (despues)"
- Each dropdown option: `{fecha formateada} — {doctor_name}` (e.g., "15 ene 2026 — Dr. Martinez")
- Dropdowns sorted newest-first
- Validation: Snapshot A must be an earlier date than Snapshot B. If user selects same date for both, warning shown.
- "Intercambiar" button (swap A and B) between the two dropdowns

**States:**
- Initial: both dropdowns empty, showing "Selecciona un snapshot..."
- Loading snapshots list: skeleton dropdown
- A or B not selected: comparison area shows placeholder "Selecciona ambas fechas para comparar"
- Both selected: comparison renders
- Same snapshot selected for A and B: warning banner "Selecciona dos fechas diferentes"

---

### Component 2: OdontogramSnapshot (read-only)

**Type:** Read-only odontogram view (grid or arch, depending on tenant mode)

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| snapshotData | OdontogramState | — | Tooth conditions at snapshot date |
| diffMap | DiffMap | {} | Map of toothId+zone → diff type (added/removed/changed) |
| label | "A" \| "B" | — | Which side this is |
| snapshotDate | Date | — | Date of snapshot |
| authorName | string | — | Name of doctor who took snapshot |
| mode | "classic" \| "anatomic" | "classic" | Rendering mode |

**States:**
- Default: full read-only odontogram render
- Diff overlays applied: zones with changes show colored borders
  - `border-2 border-green-500` — condition added (existed in B, not in A)
  - `border-2 border-red-500` — condition removed (existed in A, not in B)
  - `border-2 border-yellow-500` — condition changed (different condition in A vs B)
- Loading: skeleton odontogram (same skeleton as FE-OD-01/02)

**Diff border behavior:**
- Diff borders applied as absolute overlay rings on zones (do not change zone fill color)
- Healthy zones that received a condition in B: green ring in B panel, red ring in A panel
- Diff borders pulse subtly on initial render: `animate-pulse` for 1s then stop

---

### Component 3: DiffLegend

**Type:** Color legend strip

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| counts | { added: number, removed: number, changed: number } | — | Count of each diff type |

**Layout:**
```
■ Agregado (N)   ■ Eliminado (N)   ■ Modificado (N)   ■ Sin cambios
```
- Each item: colored square swatch (16×16px) + label + count
- "Sin cambios" shown in gray for unchanged zones
- "Sin diferencias detectadas" shown when all counts are 0

---

### Component 4: DiffSummary

**Type:** Expandable detail list

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| changes | DiffChange[] | [] | Array of detected zone-level changes |

**Each change item:**
```
Diente 36 • Oclusal    [Caries] → [Obturado]      MODIFICADO
Diente 26 • Mesial     [ninguna] → [Corona]         AGREGADO
Diente 11 • Distal     [Fractura] → [ninguna]       ELIMINADO
```

- Changes sorted by: first ELIMINADO, then AGREGADO, then MODIFICADO
- Expandable: shows first 5 changes; "Ver todos ({N})" expands the list
- Each item: tooth FDI + zone + old condition pill + arrow + new condition pill + diff type badge

---

## Form Fields

Not applicable — read-only comparison view with no form inputs beyond snapshot selectors.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| List snapshots | `/api/v1/patients/{id}/odontogram/snapshots` | GET | `specs/odontogram/OD-08` | 2min stale |
| Get snapshot A | `/api/v1/patients/{id}/odontogram/snapshots/{snapshot_id}` | GET | `specs/odontogram/OD-08` | 10min stale |
| Get snapshot B | `/api/v1/patients/{id}/odontogram/snapshots/{snapshot_id}` | GET | `specs/odontogram/OD-08` | 10min stale |

### State Management

**Local State (useState):**
- `snapshotAId: string | null` — selected left snapshot ID
- `snapshotBId: string | null` — selected right snapshot ID
- `diffMap: DiffMap | null` — computed diff (derived, not server state)
- `expandedDiff: boolean` — DiffSummary expanded state

**Global State (Zustand):**
- None — comparison view is self-contained; does not write to `useOdontogramStore`

**Server State (TanStack Query):**
- Query key: `['odontogram-snapshots', patientId]` — snapshots list
- Query key: `['odontogram-snapshot', patientId, snapshotAId]` — snapshot A data
- Query key: `['odontogram-snapshot', patientId, snapshotBId]` — snapshot B data
- Stale time: 10 minutes for individual snapshots (snapshots are immutable)
- Both snapshot queries run in parallel when both IDs selected

**Diff computation:**
- Pure client-side, runs in `useMemo` when both snapshots loaded:
  ```typescript
  const diffMap = useMemo(() => computeDiff(snapshotA, snapshotB), [snapshotA, snapshotB]);
  ```
- Iterates all 32 teeth × 5-6 zones; O(N) time, no backend needed

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Select Snapshot A | Dropdown change | Fetches snapshot A data | Left panel loads skeleton then renders |
| Select Snapshot B | Dropdown change | Fetches snapshot B data | Right panel loads skeleton then renders |
| Click "Intercambiar" | Button click | Swaps A and B snapshot IDs | Both panels re-render with swapped dates |
| Hover zone with diff | Hover zone in either panel | Tooltip shows: "{old condition} → {new condition}" | Tooltip appears |
| Click DiffSummary item | Click change row | Scrolls both panels to that tooth; tooth highlighted | Smooth scroll + highlight ring |
| "Ver todos" changes | Click expand | DiffSummary expands to show all changes | Smooth height transition |
| "Volver al odontograma" | Click back button | Navigate to `/patients/{id}/odontogram` | Standard navigation |

### Animations/Transitions

- Snapshot panel load: fade in from `opacity-0` over 200ms after data arrives
- Diff border pulse: `animate-pulse` on diff zone borders for 1 second on render, then static
- DiffSummary expand: `motion.div` height animation 200ms ease-out
- "Intercambiar" button rotation: icon rotates 180° on click: `transition-transform duration-200`
- Snapshot select: brief loading skeleton covers the affected panel only

---

## Loading & Error States

### Loading State
- Snapshots list loading: skeleton dropdown buttons for A and B selectors
- Individual snapshot loading: skeleton odontogram (same pattern as FE-OD-01) on affected panel only
- Both panels can load independently (parallel queries)

### Error State
- Snapshots list fails: error in selector area
  - Message: "No se pudo cargar la lista de snapshots. Intenta de nuevo."
  - Button: "Reintentar"
- Individual snapshot fails: error card in that panel
  - Message: "No se pudo cargar este snapshot."
  - Button: "Reintentar"
- DiffSummary not computed yet (one panel still loading): "Calculando diferencias..."

### Empty State
- No snapshots exist for patient:
  - Selector shows "Este paciente no tiene snapshots guardados."
  - CTA: "Tomar un snapshot" → redirects to odontogram view with toolbar snapshot button highlighted
- Snapshots selected but no differences:
  - DiffLegend all zeros; DiffSummary shows "No se detectaron diferencias entre estos dos snapshots."

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Not supported — comparison requires side-by-side layout. Shows message: "La vista de comparacion requiere una pantalla mas grande." |
| Tablet (640-1024px) | PRIMARY USE CASE. Side-by-side panels stacked vertically (A above B) on portrait; side-by-side on landscape. SnapshotSelector as full-width row above both panels. DiffLegend below. DiffSummary as collapsible drawer at bottom. |
| Desktop (> 1024px) | Default side-by-side layout. Panels equal width. DiffSummary as right sidebar or below panels. |

**Tablet priority:** High — tablet landscape is ideal for side-by-side. Portrait stacks vertically. Diff zone borders must be clearly visible on tablet-sized tooth zones (minimum 2px border width).

---

## Accessibility

- **Focus order:** Back button → Snapshot A selector → Snapshot B selector → Intercambiar → Left panel (read-only, tooth order) → Right panel → DiffLegend → DiffSummary → "Ver todos" → individual change rows
- **Screen reader:** Comparison page has `role="main"` with `aria-label="Comparacion de odontogramas"`. Each read-only odontogram has `aria-label="Snapshot {A/B} — {fecha}"`. DiffSummary has `aria-live="polite"` so changes announce after diff computed. Each DiffChange row has `aria-label="Diente {FDI}, {zone}: {old} cambiado a {new}"`.
- **Keyboard navigation:** Tab between selector dropdowns. Arrow keys within dropdowns. "Intercambiar" button: Enter/Space. DiffSummary "Ver todos": Enter to expand. Escape closes any open dropdown.
- **Color contrast:** Diff borders supplement by text labels. Green border: `border-green-500` (not sole indicator — "AGREGADO" text badge also present). Red: `border-red-500` + "ELIMINADO" badge. Yellow: `border-yellow-500` + "MODIFICADO" badge. WCAG AA for all text.
- **Language:** All labels in es-419. "Snapshot A (antes)", "Snapshot B (despues)". Diff types: "Agregado", "Eliminado", "Modificado". "Intercambiar" for swap. Timestamps formatted: "15 de enero de 2026".

---

## Design Tokens

**Colors:**
- Page background: `bg-gray-50 dark:bg-gray-950`
- Panel background: `bg-white dark:bg-gray-900`
- Panel divider: `border-r border-gray-200 dark:border-gray-700`
- Diff border added: `border-green-500` (2px)
- Diff border removed: `border-red-500` (2px)
- Diff border changed: `border-yellow-500` (2px)
- Diff badge added: `bg-green-100 text-green-700`
- Diff badge removed: `bg-red-100 text-red-700`
- Diff badge changed: `bg-yellow-100 text-yellow-700`

**Typography:**
- Page title: `text-lg font-semibold text-gray-800`
- Panel label: `text-sm font-semibold text-gray-700 uppercase tracking-wide`
- Snapshot date: `text-base font-medium text-gray-900`
- Snapshot author: `text-xs text-gray-500`
- DiffChange row: `text-sm text-gray-700`

**Spacing:**
- Panel padding: `p-4`
- Panel gap (side-by-side): `gap-4`
- DiffLegend padding: `py-3 px-4`
- DiffSummary padding: `p-4`

**Border Radius:**
- Panels: `rounded-xl`
- Diff badges: `rounded-full`
- Diff borders: applied as `ring-2` on zone elements

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-query` — parallel snapshot queries
- `framer-motion` — DiffSummary expand, panel fade-in
- `lucide-react` — ArrowLeftRight (swap), AlertTriangle, CheckCircle

**File Location:**
- Page: `src/app/(dashboard)/patients/[id]/odontogram/comparison/page.tsx`
- Components: `src/components/odontogram/comparison/ComparisonView.tsx`
- Components: `src/components/odontogram/comparison/SnapshotSelector.tsx`
- Components: `src/components/odontogram/comparison/OdontogramSnapshot.tsx`
- Components: `src/components/odontogram/comparison/DiffLegend.tsx`
- Components: `src/components/odontogram/comparison/DiffSummary.tsx`
- Utils: `src/lib/odontogram/diffComputer.ts`
- Types: `src/types/odontogram.ts`

**Hooks Used:**
- `useQuery(['odontogram-snapshots', patientId])` — snapshots list
- `useQuery(['odontogram-snapshot', patientId, snapshotAId], { enabled: !!snapshotAId })` — snapshot A
- `useQuery(['odontogram-snapshot', patientId, snapshotBId], { enabled: !!snapshotBId })` — snapshot B
- `useMemo(() => computeDiff(a, b), [a, b])` — diff computation
- `useAuth()` — role check (all roles can compare, receptionist included)

**Diff computation algorithm (`diffComputer.ts`):**
```typescript
type DiffType = 'added' | 'removed' | 'changed';
type DiffMap = Record<string, DiffType>; // key: `${toothId}_${zone}`

function computeDiff(a: OdontogramState, b: OdontogramState): DiffMap {
  const diff: DiffMap = {};
  for (const tooth of ALL_TOOTH_IDS) {
    for (const zone of ALL_ZONES) {
      const condA = a[tooth]?.[zone] ?? null;
      const condB = b[tooth]?.[zone] ?? null;
      if (condA === null && condB !== null) diff[`${tooth}_${zone}`] = 'added';
      else if (condA !== null && condB === null) diff[`${tooth}_${zone}`] = 'removed';
      else if (condA !== null && condB !== null && condA !== condB) diff[`${tooth}_${zone}`] = 'changed';
    }
  }
  return diff;
}
```

---

## Test Cases

### Happy Path
1. Doctor selects two snapshots and sees diff
   - **Given:** Patient has 3 snapshots; Snapshot A (Jan 15) has caries on 36-O; Snapshot B (Feb 15) has 36-O obturado
   - **When:** Select A = Jan 15, B = Feb 15
   - **Then:** Left panel shows 36-O red; right panel shows 36-O blue; 36-O has yellow border in right (MODIFICADO); DiffLegend shows 1 Modificado; DiffSummary shows row for 36-O

2. Swap button reverses A and B
   - **Given:** A = Jan 15, B = Feb 15 selected
   - **When:** Click "Intercambiar"
   - **Then:** A becomes Feb 15, B becomes Jan 15; panels swap; diff borders flip (added/removed invert)

3. No differences between snapshots
   - **Given:** Two snapshots with identical condition maps
   - **When:** Both selected
   - **Then:** No diff borders; DiffLegend shows all zeros; DiffSummary: "No se detectaron diferencias."

4. New condition in B (added)
   - **Given:** Snapshot A: tooth 11 zone M = null; Snapshot B: tooth 11 zone M = "Fractura"
   - **When:** Compare selected
   - **Then:** Left panel 11-M has no border; right panel 11-M has green border; DiffLegend: Agregado +1

### Edge Cases
1. Patient has no snapshots
   - **Given:** No snapshots exist for patient
   - **When:** Navigate to comparison page
   - **Then:** Selector shows "Sin snapshots"; CTA "Tomar un snapshot"

2. Only one snapshot exists
   - **Given:** Patient has exactly 1 snapshot
   - **When:** Navigate to comparison page
   - **Then:** Snapshot A can be selected; Snapshot B dropdown disabled with message "Se necesitan al menos dos snapshots para comparar."

3. Both dropdowns show same snapshot
   - **Given:** User selects same snapshot for A and B
   - **When:** Diff computed
   - **Then:** DiffMap is empty (no differences); warning banner "Selecciona dos fechas diferentes para una comparacion significativa."

### Error Cases
1. Snapshots list fails to load
   - **Given:** OD-08 returns 500
   - **When:** Page loads
   - **Then:** Selector error state; "No se pudo cargar la lista de snapshots. Reintentar."

2. Individual snapshot data fails
   - **Given:** Snapshot A loads; Snapshot B request fails
   - **When:** B selected
   - **Then:** Right panel shows error card; diff not computed; DiffSummary hidden

---

## Acceptance Criteria

- [ ] Side-by-side read-only odontogram panels rendered for two selected snapshots
- [ ] SnapshotSelector: two dropdowns listing available snapshots (date + author)
- [ ] "Intercambiar" button swaps A and B correctly
- [ ] Diff computation is client-side, runs after both snapshots loaded
- [ ] Added condition zones: green border (2px) in B panel, red border in A panel
- [ ] Removed condition zones: red border in B panel
- [ ] Changed condition zones: yellow border in both panels
- [ ] DiffLegend shows counts for added, removed, modified
- [ ] DiffSummary lists all detected changes with tooth, zone, old → new condition
- [ ] DiffSummary "Ver todos" expands full list
- [ ] Clicking DiffSummary item scrolls to + highlights tooth in both panels
- [ ] Empty diff state: "No se detectaron diferencias."
- [ ] No snapshots state: prompt to take first snapshot
- [ ] Loading skeleton per panel (independent loading)
- [ ] Error state per panel with retry
- [ ] Tablet landscape: side-by-side layout; portrait: stacked
- [ ] All labels in Spanish (es-419)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
