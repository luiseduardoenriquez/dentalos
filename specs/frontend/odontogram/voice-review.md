# Revision de Cambios por Voz (Voice Review) — Frontend Spec

## Overview

**Screen:** Modal or slide-over panel displaying proposed odontogram changes parsed from a voice command. Each proposed change is shown as a card with tooth number (FDI), zone, condition icon, and action (add/remove). The user accepts or rejects each change individually, with confidence indicators from the LLM pipeline. Batch actions: accept all / reject all. "Aplicar seleccionados" applies only accepted changes to the odontogram.

**Route:** Modal within `/patients/{id}` odontogram view — no dedicated route. Controlled by `useVoiceReviewStore`.

**Priority:** High

**Backend Specs:** `specs/voice/voice-parse.md` (V-03), `specs/voice/voice-apply.md` (V-04)

**Dependencies:** `specs/frontend/odontogram/voice-input.md`, `specs/frontend/odontogram/classic-grid.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Triggered automatically after voice transcription parsing completes (V-03 result delivered)
- User recorded voice input → transcription done → LLM parsed → this review modal opens

**Exit Points:**
- "Aplicar seleccionados" → accepted changes applied to odontogram, modal closes, odontogram refreshes
- "Cancelar" → modal closes, no changes applied, voice recording state resets
- Reject all cards + "Aplicar" → no changes applied, modal closes with info toast

**User Story:**
> As a doctor, I want to review AI-parsed odontogram changes before they are applied so that I can correct any misinterpretations and ensure clinical accuracy.

**Roles with access:** `doctor`, `assistant`

---

## Layout Structure

```
+--------------------------------------------------+
|  Modal overlay (backdrop blur)                   |
|  +--------------------------------------------+ |
|  |  "Cambios propuestos por voz"    [X close]  | |
|  |  [Batch actions: Aceptar todo | Rechazar todo] |
|  +--------------------------------------------+ |
|  |                                            | |
|  |  [Change card 1: tooth + condition]        | |
|  |  [Change card 2: tooth + condition]        | |
|  |  [Change card 3: tooth + condition]        | |
|  |  [... more cards, scrollable]              | |
|  |                                            | |
|  +--------------------------------------------+ |
|  |  [Cancelar]    [Aplicar seleccionados (N)] | |
|  +--------------------------------------------+ |
+--------------------------------------------------+
```

**Sections:**
1. Modal header — title, X close button
2. Batch action bar — "Aceptar todo" / "Rechazar todo" buttons + summary count
3. Change cards list — scrollable, one card per proposed change
4. Footer — cancel + apply button with accepted count

---

## UI Components

### Component 1: VoiceReviewModal

**Type:** Modal dialog

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.15

**Dimensions:** `max-w-lg w-full` on desktop; `w-full h-full rounded-t-2xl` bottom sheet on mobile
**Animation:** Desktop: fade + scale `scale-95 → scale-100, opacity 0 → 1` 200ms. Mobile: slide up from bottom 250ms.
**Backdrop:** `bg-black/50 backdrop-blur-sm`
**Close:** X button top-right, Escape key

### Component 2: BatchActionBar

**Type:** Action row below header

**Content:**
- Summary text: `"{N} cambios detectados"` `text-sm text-gray-600`
- "Aceptar todo" button: `variant="outline" text-green-600 border-green-300 hover:bg-green-50 text-sm`
- "Rechazar todo" button: `variant="outline" text-red-500 border-red-200 hover:bg-red-50 text-sm`

**Behavior:**
- "Aceptar todo" → sets all cards to `accepted = true`
- "Rechazar todo" → sets all cards to `accepted = false`
- Both buttons animate affected cards simultaneously

### Component 3: ChangeCard

**Type:** Interactive card

**Layout:**
```
+------------------------------------------+
| [Mini-tooth graphic]  [Diente {FDI}]     |
|                       [{Zone name}]      |
|                       [{Condition icon} {Condition name}] |
|                       [Accion: {Agregar/Eliminar} badge]  |
|                       [Confidence indicator]              |
| [Reject toggle]                [Accept toggle] |
+------------------------------------------+
```

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| tooth_fdi | string | FDI tooth number, e.g., "16" |
| zone | string | "Oclusal", "Vestibular", "Mesial", "Distal", "Lingual/Palatino" |
| condition | string | Condition key: "caries", "corona", "extraccion", etc. |
| action | "add" \| "remove" | Whether to add or remove the condition |
| confidence | "high" \| "medium" \| "low" | LLM confidence score |
| accepted | boolean | Current accept/reject state (default: true) |

**Mini-tooth graphic:**
- `40x40px` SVG simplified tooth outline from the design system
- Highlighted zone shaded with condition color
- No interaction — purely illustrative

**Condition icon + name:** Same icons used in the odontogram condition panel.

**Action badge:**

| Action | Badge style | Label |
|--------|------------|-------|
| `add` | `bg-teal-100 text-teal-700` | "Agregar" |
| `remove` | `bg-red-100 text-red-600` | "Eliminar" |

**Confidence indicator:**

| Level | Visual | Label |
|-------|--------|-------|
| `high` | 3 filled bars `|||` in `text-green-500` | "Alta confianza" |
| `medium` | 2 filled bars `||_` in `text-amber-400` | "Confianza media" |
| `low` | 1 filled bar `|__` in `text-red-400` | "Baja confianza" |

Confidence bar: 3 segments `w-1 h-3` each, `rounded-sm`, filled or `bg-gray-200`.

**Accept/Reject toggles:**
- Two large icon buttons at bottom of card
- Reject (left): `CheckX` icon, `w-10 h-10 rounded-full`, accepted=false state: `bg-red-100 text-red-600`, default: `bg-gray-100 text-gray-400`
- Accept (right): `Check` icon, accepted=true state: `bg-green-100 text-green-600`, default: `bg-gray-100 text-gray-400`
- Toggle: clicking Accept when already accepted = no-op; clicking Reject when already accepted = sets to rejected
- Touch target: `min-44px` with additional padding

**Card states:**
- Accepted: `border-2 border-green-300 bg-green-50/30`
- Rejected: `border-2 border-red-200 bg-red-50/20 opacity-60`
- Default (pending): `border border-gray-200 bg-white`

**Low confidence callout:**
- If `confidence === 'low'`, show inline warning inside card: `"Verifica este cambio — baja confianza del modelo"` `text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded mt-2`

---

## Form Fields

No form fields. All interactions are toggle-based accept/reject on each card.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Apply accepted changes | `/api/v1/odontogram/{patientId}/apply-voice` | POST | `specs/voice/voice-apply.md` | None |

### Request Body (POST)

```typescript
{
  session_id: string;         // voice session ID from V-03 result
  accepted_changes: Array<{
    tooth_fdi: string;
    zone: string;
    condition: string;
    action: "add" | "remove";
  }>;
}
```

### State Management

**Local State (useState):**
- `cardStates: Record<string, boolean>` — key: `{fdi}_{zone}_{condition}`, value: accepted
- `isApplying: boolean`

**Global State (Zustand):**
- `voiceReviewStore.isOpen: boolean`
- `voiceReviewStore.proposedChanges: ProposedChange[]`
- `voiceReviewStore.sessionId: string`
- After apply: invalidate `['odontogram', patientId]` query

**Server State (TanStack Query):**
- Mutation: `useMutation({ mutationFn: applyVoiceChanges, onSuccess: () => { queryClient.invalidateQueries(['odontogram', patientId]); closeModal(); } })`

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click Accept toggle | Click | Card → accepted state | Green border + background |
| Click Reject toggle | Click | Card → rejected state | Opacity reduced, red border |
| Click "Aceptar todo" | Click | All cards → accepted | All cards green simultaneously |
| Click "Rechazar todo" | Click | All cards → rejected | All cards dim simultaneously |
| Click "Aplicar seleccionados (N)" | Click | POST with accepted changes | Spinner on button |
| POST success | API | Modal closes, odontogram refreshes | Toast "N cambios aplicados al odontograma" |
| Click "Cancelar" | Click | Modal closes, no API call | Toast "Cambios descartados" |
| Press Escape | Key | Same as Cancelar | Same |
| Scroll card list | Scroll | Cards scroll within modal | Natural scroll |

**N in "Aplicar seleccionados (N)":** Real-time count of accepted cards. Updates immediately as user toggles.

### Animations/Transitions

- Modal open: `motion.div scale-95 → scale-100, opacity 0 → 1` 200ms ease-out
- Card accept toggle: card border color transition `transition-all duration-200`
- Card reject toggle: `opacity: 1 → 0.6` + border change 200ms
- "Aceptar todo" / "Rechazar todo": all cards animate simultaneously with stagger `delay: index * 40ms`
- Success close: modal fades out 150ms, odontogram cards animate in with new conditions

---

## Loading & Error States

### Loading State
- "Aplicar seleccionados" clicked: button shows "Aplicando..." + `Loader2 animate-spin`, all toggles disabled
- Cards `pointer-events-none opacity-80`

### Error State
- API error: toast `"Error al aplicar cambios. Intenta de nuevo."` — modal stays open
- Button re-enabled, user can retry

### Empty State
- 0 proposed changes (edge case where LLM returns empty result): modal shows "No se detectaron cambios en la grabacion" with voice icon + "Cerrar" button

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Bottom sheet sliding from bottom `h-[85vh]`. Cards take full width. Toggle buttons larger `w-12 h-12`. Batch actions row stacks vertically. |
| Tablet (640-1024px) | Modal `max-w-lg` centered. Cards in single column within modal. |
| Desktop (> 1024px) | Same as tablet. Cards potentially in 2-column grid if > 4 changes. |

**Tablet priority:** Critical — doctors dictate and review on tablets during consultation. Toggle buttons min 44px. Entire card is tappable for accept (convenience: tapping card body = accept).

---

## Accessibility

- **Focus order:** Close X → "Aceptar todo" → "Rechazar todo" → Card 1 Accept → Card 1 Reject → Card 2 Accept → ... → "Cancelar" → "Aplicar"
- **Screen reader:** Modal: `role="dialog" aria-modal="true" aria-labelledby="voice-review-title"`. Each card: `role="group" aria-label="Cambio propuesto: Diente {FDI}, {zone}, {condition}, {action}"`. Accept toggle: `role="checkbox" aria-checked="true/false" aria-label="Aceptar este cambio"`. Reject toggle: `aria-label="Rechazar este cambio"`. Confidence: `aria-label="Confianza {level}"`.
- **Keyboard navigation:** Tab cycles through all interactive elements. Space/Enter toggles accept/reject. Arrow keys within card group.
- **Color contrast:** Green accepted state: border + background, text `text-green-700` meets 4.5:1. Red rejected: `text-red-600` on white meets WCAG AA.
- **Motion:** Respect `prefers-reduced-motion` — disable stagger animations, use instant transitions.
- **Language:** All labels in es-419.

---

## Design Tokens

**Colors:**
- Modal background: `bg-white dark:bg-gray-900`
- Backdrop: `bg-black/50 backdrop-blur-sm`
- Card accepted: `border-green-300 bg-green-50/30`
- Card rejected: `border-red-200 bg-red-50/20 opacity-60`
- Card default: `border-gray-200 bg-white`
- Accept button active: `bg-green-100 text-green-600`
- Reject button active: `bg-red-100 text-red-600`
- Confidence high: `text-green-500`
- Confidence medium: `text-amber-400`
- Confidence low: `text-red-400`
- Add badge: `bg-teal-100 text-teal-700`
- Remove badge: `bg-red-100 text-red-600`

**Typography:**
- Modal title: `text-lg font-bold text-gray-900`
- FDI number: `text-base font-bold text-gray-800`
- Zone name: `text-xs text-gray-500`
- Condition name: `text-sm font-medium text-gray-700`
- Confidence label: `text-xs font-medium`

**Spacing:**
- Modal padding: `p-6`
- Card padding: `p-4 rounded-xl mb-3`
- Toggle button gap: `gap-3 mt-3 pt-3 border-t border-gray-100`
- Batch action bar padding: `px-6 py-3 border-b border-gray-100`

---

## Implementation Notes

**Dependencies (npm):**
- `framer-motion` — modal animation, stagger on batch actions
- `lucide-react` — Check, X, Mic, Loader2

**File Location:**
- Component: `src/components/odontogram/VoiceReviewModal.tsx`
- Card: `src/components/odontogram/VoiceChangeCard.tsx`
- Store: `src/stores/voiceReviewStore.ts`
- API: `src/lib/api/voice.ts`

**Hooks Used:**
- `useVoiceReviewStore()` — open/close, proposed changes, session ID
- `useMutation()` — apply changes
- `useQueryClient()` — invalidate odontogram after apply

---

## Test Cases

### Happy Path
1. Doctor reviews 3 proposed changes, accepts all, applies
   - **Given:** Voice session parsed 3 changes (caries tooth 16, extraccion tooth 48, corona tooth 21)
   - **When:** All 3 cards show accepted (default), click "Aplicar seleccionados (3)"
   - **Then:** POST with 3 changes, odontogram updates, modal closes, toast "3 cambios aplicados"

2. Doctor rejects one low-confidence change
   - **Given:** 3 cards, one has `confidence: 'low'` with warning callout
   - **When:** Doctor clicks reject on low-confidence card, applies remaining 2
   - **Then:** POST with 2 changes only

### Edge Cases
1. "Rechazar todo" then "Aplicar seleccionados (0)"
   - **Given:** All cards rejected
   - **When:** Apply button shows "(0)", user clicks
   - **Then:** POST with empty array, modal closes, toast "Sin cambios aplicados"

2. Single card, tap card body
   - **Given:** 1 proposed change
   - **When:** Doctor taps card body (not toggle buttons)
   - **Then:** Card toggles to accepted state (convenience behavior on touch)

### Error Cases
1. API error on apply
   - **Given:** Network intermittent
   - **When:** "Aplicar seleccionados" clicked, POST fails
   - **Then:** Toast error, modal stays open, button re-enabled, user can retry

---

## Acceptance Criteria

- [ ] Modal opens automatically after voice parse completes
- [ ] Each change card shows: mini-tooth graphic, FDI number, zone, condition icon+name, action badge, confidence indicator
- [ ] Default state: all cards accepted (green border)
- [ ] Individual accept/reject toggles per card with visual state change
- [ ] "Aceptar todo" / "Rechazar todo" batch actions
- [ ] Low-confidence cards show amber warning callout
- [ ] "Aplicar seleccionados (N)" count updates in real-time
- [ ] POST sends only accepted changes with session ID
- [ ] Success: modal closes, odontogram refreshes, success toast
- [ ] Error: modal stays open, error toast, retry possible
- [ ] Mobile: bottom sheet layout
- [ ] Accessibility: dialog ARIA, card group ARIA, keyboard navigation
- [ ] Respects `prefers-reduced-motion`
- [ ] Spanish (es-419) throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
