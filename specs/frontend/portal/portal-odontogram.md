# Odontograma del Paciente — Portal (Patient Portal Odontogram) — Frontend Spec

## Overview

**Screen:** Simplified read-only odontogram view for patients in the patient portal. Classic grid view only (no anatomic view — simpler for non-clinical audience). Conditions displayed with color codes and layperson Spanish descriptions (e.g., "Caries" → "Cavidad dental"). Hover/tap shows tooltip explaining the condition in plain language. No edit controls. Educational purpose — helps patient understand their dental health.

**Route:** `/portal/odontogram`

**Priority:** Medium

**Backend Specs:** `specs/portal/portal-odontogram.md` (PP-13)

**Dependencies:** `specs/frontend/portal/portal-dashboard.md`, `specs/frontend/odontogram/classic-grid.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Patient portal sidebar "Mi Odontograma" link
- Portal dashboard quick link "Ver mi odontograma"
- "Ver odontograma" button in treatment plan detail

**Exit Points:**
- "Volver al portal" → `/portal`
- "Ver mis planes de tratamiento" → `/portal/treatment-plans`
- "Preguntar a mi doctor" → `/portal/messages/new` (pre-filled subject)

**User Story:**
> As a patient, I want to see my dental chart in simple, understandable language so that I can understand my dental health and the treatments my doctor has recommended.

**Roles with access:** `patient` (portal only).

---

## Layout Structure

```
+------------------------------------------+
|  Portal header (clinic branding)          |
+------------------------------------------+
|  "Mi Odontograma"                         |
|  Last updated: "Actualizado el 20 feb 2026" |
+------------------------------------------+
|                                          |
|  [Odontogram Grid — read-only classic]   |
|                                          |
+------------------------------------------+
|  [Condition Legend panel]                |
+------------------------------------------+
|  [Educational note / disclaimer]         |
+------------------------------------------+
|  [Ver planes de tratamiento btn]         |
|  [Preguntar a mi doctor btn]             |
+------------------------------------------+
```

**Sections:**
1. Portal header — clinic logo, clinic name, patient name
2. Page title — title, last updated date
3. Odontogram grid — read-only classic FDI grid
4. Condition legend — all conditions present in this patient's chart with plain-language names
5. Educational note — brief explanation of what an odontogram is
6. Action buttons — treatment plans + message doctor

---

## UI Components

### Component 1: PortalOdontogramGrid

**Type:** Adapted from `ClassicGrid` component, read-only variant

**Design System Ref:** `frontend/odontogram/classic-grid.md`

**Key differences from clinical odontogram:**
- No toolbar (no mode selector, no condition selector, no edit tools)
- No multi-select, no right-click menus
- Click/tap on tooth opens condition tooltip (not edit panel)
- Simplified tooth squares: larger `44px min` per tooth for touch accessibility
- FDI numbers shown above each tooth (smaller patients: deciduous label shown with star)

**Tooth square visual:**
- Default (healthy): `bg-white border border-gray-200`
- With condition: filled with condition color (see layperson color table below)
- Multiple conditions: diagonal split color fill (CSS `linear-gradient`)
- Missing tooth: `bg-gray-100 border-dashed border-gray-300` with `×` icon
- Extracted: same as missing but with different label

**Grid layout:**
```
[Permanent superior right]  |  [Permanent superior left]
18 17 16 15 14 13 12 11  |  21 22 23 24 25 26 27 28
--------------------------+--------------------------
48 47 46 45 44 43 42 41  |  31 32 33 34 35 36 37 38
[Permanent inferior right]  |  [Permanent inferior left]
```

Deciduous (if applicable — pediatric patients):
```
55 54 53 52 51 | 61 62 63 64 65
85 84 83 82 81 | 71 72 73 74 75
```

### Component 2: ConditionTooltip

**Type:** Popover tooltip (hover on desktop, tap on mobile)

**Trigger:** Click/tap tooth with conditions

**Content per tooth (when tapped):**
```
[Tooth number + name]        "Diente 16 — Primer molar superior derecho"
[Condition list]             Each condition as a colored dot + layperson name
[Doctor note (if any)]       Brief note from treating doctor
[Date recorded]              "Registrado el 15 ene 2026"
```

**Mobile behavior:** Full-bottom-sheet tooltip `fixed bottom-0 left-0 right-0 bg-white rounded-t-2xl p-5` — slides up with `motion.div`. Close via swipe down or tap outside.

**Desktop behavior:** Floating popover `absolute z-50 bg-white rounded-xl shadow-xl p-4 max-w-xs` positioned above or below tooth depending on viewport space.

### Component 3: ConditionLegend

**Type:** Legend panel

**Design:**
- Title: `"Condiciones en tu odontograma"` `text-sm font-semibold text-gray-700`
- Only shows conditions that EXIST in this patient's chart (filtered)
- Each item: `color swatch (16px rounded-full) + layperson name + clinical name in parentheses`
- Grid: `grid grid-cols-2 md:grid-cols-3 gap-3`

**Layperson condition translation table:**

| Clinical name | Layperson name (es-419) | Color |
|---------------|------------------------|-------|
| Caries | Cavidad dental | `#F87171` (red) |
| Obturacion | Empaste / Restauracion | `#60A5FA` (blue) |
| Endodoncia | Tratamiento de conducto | `#C084FC` (purple) |
| Corona | Corona dental (funda) | `#FBBF24` (yellow) |
| Extraccion indicada | Extraccion recomendada | `#F97316` (orange) |
| Diente ausente | Diente faltante | `#9CA3AF` (gray) |
| Implante | Implante dental | `#34D399` (green) |
| Puente | Puente dental | `#A78BFA` (violet) |
| Fractura | Diente fracturado | `#EF4444` (red-dark) |
| Edema | Inflamacion | `#FB923C` (orange-light) |
| Gingivitis | Encias inflamadas | `#F472B6` (pink) |
| Periodontitis | Enfermedad de las encias | `#EC4899` (pink-dark) |
| Diente sano | Diente sano | `bg-white border-gray-200` |

**"Que significa esto?" expandable section:**
- `<details>/<summary>` with `"Que significa cada color?"` as summary
- Expanded: brief 2-sentence explanation of what an odontogram is and how to read it

### Component 4: EducationalNote

**Type:** Callout box

**Design:** `bg-blue-50 border border-blue-100 rounded-xl p-4 flex gap-3`
- Icon: `Info text-blue-500 w-5 h-5 flex-shrink-0`
- Text: `"Este es un mapa de tus dientes, actualizado por tu odontologo. Los colores muestran el estado de cada diente. Si tienes preguntas, escribele a tu doctor."`
- `text-sm text-blue-700`

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Get patient odontogram | `/api/v1/portal/odontogram` | GET | `specs/portal/portal-odontogram.md` | 5min |

### Response Shape

```typescript
{
  last_updated: string;       // ISO date
  teeth: Array<{
    fdi: string;
    conditions: Array<{
      type: string;           // clinical key
      zone: string;           // "oclusal", "vestibular", etc.
      note?: string;
    }>;
  }>;
  is_deciduous: boolean;      // show deciduous grid if true
}
```

### State Management

**Local State (useState):**
- `selectedTooth: string | null` — FDI of tooth with open tooltip

**Server State (TanStack Query):**
- `useQuery({ queryKey: ['portal-odontogram'], staleTime: 5 * 60 * 1000 })`

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Tap healthy tooth | Tap/click | No tooltip (nothing to show) | Subtle scale `1 → 1.02 → 1` tap feedback |
| Tap tooth with conditions | Tap/click | Open condition tooltip | Tooltip slides in |
| Tap different tooth | Tap/click | Previous tooltip closes, new opens | Smooth transition |
| Tap outside tooltip | Tap | Tooltip closes | Smooth close |
| Swipe down on bottom sheet (mobile) | Swipe | Tooltip closes | Spring animation |
| Click "Ver mis planes de tratamiento" | Click | Navigate to `/portal/treatment-plans` | Standard navigation |
| Click "Preguntar a mi doctor" | Click | Navigate to `/portal/messages/new?subject=Consulta+sobre+mi+odontograma` | Standard navigation |

### Animations/Transitions

- Tooth tap feedback: `scale 1 → 1.05 → 1` 150ms
- Desktop tooltip appear: `opacity 0 → 1, scale 0.95 → 1` 150ms
- Mobile bottom sheet: `y: 100% → 0%` 300ms spring
- Mobile bottom sheet close: `y: 0% → 100%` 250ms ease-in

---

## Loading & Error States

### Loading State
- Skeleton odontogram grid: `grid` matching dental layout, each tooth position `w-11 h-11 bg-gray-100 rounded animate-pulse`
- Legend skeleton: 6 items `h-5 w-32 bg-gray-100 rounded animate-pulse`

### Error State
- API error: centered card "No pudimos cargar tu odontograma" + "Intenta de nuevo" button + clinic contact info

### Empty State
- Patient has no recorded conditions (all teeth healthy): odontogram renders with all white teeth + message `"Tu odontologo no ha registrado condiciones activas. ¡Que buena noticia!"` in `bg-green-50 border-green-100` callout box.

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Odontogram grid scaled to fit viewport width. Teeth `w-9 h-9 text-xs`. Scroll hint appears if grid wider than screen. Legend 1 column. Action buttons full-width stacked. |
| Tablet (640-1024px) | Grid standard size `w-11 h-11`. Legend 2 columns. Action buttons side by side. |
| Desktop (> 1024px) | Grid `w-12 h-12` for comfortable viewing. Legend 3 columns. Tooltip floating. |

**Overflow handling on mobile:** Grid container `overflow-x-auto` with scroll hint: `"Desliza para ver todos los dientes"` `text-xs text-gray-400` with swipe icon.

**Tablet priority:** Medium — patients may view portal on clinic iPad. Tooth touch targets must be min 44px.

---

## Accessibility

- **Focus order:** Odontogram grid (arrow key navigation between teeth) → Legend items (read-only) → Educational note → Action buttons
- **Screen reader:** Each tooth: `role="button" aria-label="Diente {FDI}: {tooth name}. Condiciones: {layperson condition list or 'Sano'}"`. Grid: `role="grid" aria-label="Mapa dental"`. Missing tooth: `aria-label="Diente {FDI}: Faltante"`. Tooltip: `role="dialog" aria-label="Detalle diente {FDI}"`.
- **Keyboard navigation:** Arrow keys navigate between teeth in grid. Enter/Space opens tooltip for focused tooth. Escape closes tooltip.
- **Color alone:** Condition legend always includes text name alongside color swatch — never uses color as sole identifier.
- **Language:** All patient-facing text uses layperson Spanish (es-419). No clinical jargon without explanation.

---

## Design Tokens

**Colors:**
- Portal background: `bg-gray-50`
- Grid tooth (healthy): `bg-white border-gray-200`
- Grid tooth (has condition): condition-specific color (see table)
- Grid tooth (missing): `bg-gray-100 border-dashed border-gray-300`
- Selected tooth: `ring-2 ring-teal-500`
- Educational note: `bg-blue-50 border-blue-100 text-blue-700`
- Empty/healthy state: `bg-green-50 border-green-100 text-green-700`
- Action buttons: `bg-teal-600 text-white` (primary) + `border border-teal-600 text-teal-600` (secondary)

**Typography:**
- Page title: `text-2xl font-bold text-gray-900`
- Last updated: `text-sm text-gray-500`
- Tooth FDI label: `text-xs font-mono text-gray-500`
- Tooltip title: `text-sm font-bold text-gray-800`
- Tooltip condition: `text-sm text-gray-700`
- Legend item: `text-sm text-gray-700`
- Clinical name in legend: `text-xs text-gray-400 italic`

**Spacing:**
- Page: `max-w-2xl mx-auto px-4 py-6`
- Grid container: `overflow-x-auto py-4`
- Grid cell gap: `gap-1 md:gap-1.5`
- Legend padding: `mt-6 p-5 bg-white rounded-xl border border-gray-100`
- Educational note: `mt-5 p-4`

---

## Implementation Notes

**Dependencies (npm):**
- `framer-motion` — tooltip animations
- `lucide-react` — Info, ChevronDown (for legend toggle), MessageSquare, ClipboardList

**File Location:**
- Page: `src/app/(portal)/odontogram/page.tsx`
- Components: `src/components/portal/PortalOdontogramGrid.tsx`, `src/components/portal/ToothConditionTooltip.tsx`, `src/components/portal/ConditionLegend.tsx`

**Hooks Used:**
- `useQuery(['portal-odontogram'])` — patient odontogram data
- `useState(selectedTooth)` — tooltip management

**Condition Translation Map:**
```typescript
// src/lib/constants/conditionTranslations.ts
export const CONDITION_TRANSLATIONS: Record<string, { layperson: string; color: string }> = {
  caries: { layperson: "Cavidad dental", color: "#F87171" },
  obturacion: { layperson: "Empaste / Restauracion", color: "#60A5FA" },
  endodoncia: { layperson: "Tratamiento de conducto", color: "#C084FC" },
  // ...
};
```

---

## Test Cases

### Happy Path
1. Patient views odontogram with several conditions
   - **Given:** Patient has caries (tooth 16), crown (tooth 21), endodontics (tooth 36)
   - **When:** Opens portal odontogram
   - **Then:** Grid shows 3 colored teeth, legend shows 3 conditions with layperson names, tooltips work on tap

### Edge Cases
1. Patient has only healthy teeth
   - **Given:** No conditions recorded
   - **When:** Odontogram loads
   - **Then:** All teeth white, green callout "Tu odontologo no ha registrado condiciones activas"

2. Pediatric patient with deciduous teeth
   - **Given:** `is_deciduous = true` in response
   - **When:** Grid renders
   - **Then:** Both permanent and deciduous grids shown with appropriate labeling

### Error Cases
1. API unavailable
   - **Given:** Backend down
   - **When:** Page loads
   - **Then:** Error card with clinic phone number to call for information

---

## Acceptance Criteria

- [ ] Read-only classic FDI grid with color-coded conditions
- [ ] Layperson Spanish condition names (not clinical terms)
- [ ] Condition legend shows only conditions present in patient's chart
- [ ] Tap/click tooth opens tooltip with tooth name, conditions, doctor note, date
- [ ] Mobile: bottom sheet tooltip with swipe-to-close
- [ ] Desktop: floating popover tooltip
- [ ] Educational note explaining odontogram purpose
- [ ] Empty state (healthy patient) with positive message
- [ ] "Ver planes de tratamiento" and "Preguntar a mi doctor" action buttons
- [ ] Loading skeleton matching grid layout
- [ ] Deciduous grid for pediatric patients
- [ ] Responsive: scrollable grid on mobile, full grid on tablet/desktop
- [ ] Accessibility: aria-labels with layperson descriptions, keyboard navigation
- [ ] Color not used as sole condition indicator (text always accompanies)
- [ ] Spanish (es-419) layperson language throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
