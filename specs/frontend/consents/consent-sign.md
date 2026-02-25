# Firma de Consentimiento Informado — Frontend Spec

## Overview

**Screen:** Consent signing screen. Full consent text displayed with mandatory scroll-to-bottom before the signature pad activates (legal requirement). Signature canvas component, touch-optimized for tablet use. The patient signs directly on the device. Works as the primary signing interface in the clinic. After signature submission, generates a signed PDF with audit metadata (timestamp, IP, user-agent, SHA-256 hash).

**Route:** `/patients/{id}/consentimientos/{consentId}/firmar`

**Priority:** Critical

**Backend Specs:**
- `specs/consents/IC-05` — Submit patient signature
- `specs/patients/digital-signature.md` — Signature storage and audit

**Dependencies:**
- `specs/frontend/consents/consent-create.md` (FE-IC-02) — navigates here after "Firmar ahora"
- `specs/frontend/consents/consent-list.md` (FE-IC-01) — destination after successful signing
- `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Step 3 of FE-IC-02 "Firmar ahora" selection → confirm → navigate to this screen
- Consent list FE-IC-01 → click "Firmar" on a draft consent

**Exit Points:**
- Signature submitted successfully → toast "Consentimiento firmado" → return to FE-IC-01
- "Cancelar" → confirmation dialog → return to FE-IC-01 (consent remains as draft)
- Signature submit → PDF generated → download prompt

**User Story:**
> As a doctor, I want the patient to read the full consent form on a tablet and sign it digitally so that I have a legally valid, auditable consent record without printing paper.

**Roles with access:**
- doctor: initiate and witness signing
- assistant: initiate and witness signing
- clinic_owner: initiate and witness signing
- (Patient identity confirmed by staff verbally — no patient login required for in-clinic signing)

---

## Layout Structure

```
+----------------------------------------------------------+
|  [X]  Consentimiento Informado — Lectura y Firma        |
|  Paciente: Juan Pérez Ramírez  |  Dr. García  | 25 Feb  |
+----------------------------------------------------------+
|                                                          |
|  [Consent text section — scrollable]                    |
|  ┌────────────────────────────────────────────────────┐  |
|  │ CLÍNICA DENTAL FAMILIA                            │  |
|  │ CONSENTIMIENTO INFORMADO PARA...                  │  |
|  │                                                    │  |
|  │ Yo, Juan Pérez Ramírez, identificado con cédula   │  |
|  │ 1.234.567.890, paciente de la clínica...           │  |
|  │                                                    │  |
|  │ [Full legal text — multiple paragraphs]           │  |
|  │                                                    │  |
|  │ [Scroll progress bar: ─────── 45%]                │  |
|  │                                                    │  |
|  │ [END OF TEXT — must scroll here to sign]          │  |
|  └────────────────────────────────────────────────────┘  |
|                                                          |
|  [Signature area — locked until text fully scrolled]    |
|  ┌────────────────────────────────────────────────────┐  |
|  │  Firma del Paciente                                │  |
|  │  ┌──────────────────────────────────────────────┐  │  |
|  │  │                                              │  │  |
|  │  │         [Canvas signature area]              │  │  |
|  │  │                                              │  │  |
|  │  └──────────────────────────────────────────────┘  │  |
|  │  [Limpiar firma]                                   │  |
|  └────────────────────────────────────────────────────┘  |
|                                                          |
|  [☑ Confirmo que el paciente leyó el documento]         |
|  [Cancelar]              [Confirmar Firma →]            |
+----------------------------------------------------------+
```

**Sections:**
1. Page header — title, patient name, doctor, date
2. Consent text — full legal text, scrollable, with scroll progress indicator
3. "Scroll to bottom" gate message — shown when not yet scrolled to end
4. Signature pad — canvas area, unlocked after full scroll, touch optimized
5. Witness confirmation checkbox — doctor/assistant confirms patient read
6. Action footer — Cancel + Confirm signature

---

## UI Components

### Component 1: ConsentTextViewer

**Type:** Scrollable legal text container

**Design:** White background, serif or clear sans-serif font for readability, `leading-relaxed text-base`

**Scroll gate behavior:**
- `onScroll` listener tracks scrollTop + clientHeight vs scrollHeight
- Gate releases when `scrollTop + clientHeight >= scrollHeight - 10` (10px tolerance)
- Progress bar at bottom of text area: `w-full h-1 bg-gray-200 rounded-full` with fill `bg-primary-500`
- Gate indicator message at bottom of text: "Desplázate hasta el final para habilitar la firma" in `text-sm text-amber-600 font-medium` with `ChevronDown` icon — disappears once scrolled
- Scroll lock: signature pad area rendered but `opacity-40 pointer-events-none` until gate releases
- Auto-scroll button: "Ir al final" floating button `bottom-4 right-4 within text area` shown until 80% scroll

**Accessibility note:** Keyboard users can reach the end via keyboard scrolling (Page Down, End key) — gate also listens for keyboard scroll events.

### Component 2: SignaturePad

**Type:** Canvas signature component

**Library:** `react-signature-canvas` or custom canvas implementation

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| disabled | boolean | true | Locked until scroll gate releases |
| width | number | auto | Canvas width (fills container) |
| height | number | 180 | Canvas height in px |
| penColor | string | "#1a1a2e" | Ink color |
| dotSize | number | 2 | Minimum dot size for tap |

**States:**
- Locked: `opacity-40 cursor-not-allowed` overlay with lock icon `🔒`
- Empty: dashed border `border-2 border-dashed border-gray-300 bg-gray-50`
- Has signature: `border-2 border-gray-300 bg-white`
- Saving: overlay with spinner

**Touch behavior:**
- Touch events: `onTouchStart`, `onTouchMove`, `onTouchEnd` — uses `canvas.getContext('2d')` for smooth line drawing
- Pressure sensitivity: uses `e.pressure` on PointerEvent if available, else fixed lineWidth 2px
- Palm rejection: events with contact area > threshold are ignored
- Tablet stylus: supports Apple Pencil via Pointer Events API

**Behavior:**
- "Limpiar firma" button: `canvas.clearRect()` resets canvas — `text-sm text-gray-500 underline`
- Empty check: before submit, verify canvas is not blank (compare to empty canvas data URL)

### Component 3: ScrollProgressBar

**Type:** Thin progress bar at bottom of consent text

**Content:** `w-full h-1.5 bg-gray-200 rounded-full` track. Fill: `bg-primary-500` width tied to scroll percentage via `scrollTop / (scrollHeight - clientHeight) * 100`
**Updates:** on every `scroll` event (throttled to 16ms via requestAnimationFrame)

### Component 4: WitnessConfirmCheckbox

**Type:** Checkbox with label

**Label:** "Confirmo que el paciente leyó el documento en su totalidad y firmó de manera voluntaria."
**Required:** true — submit button disabled until checked
**Style:** `text-sm text-gray-700` label, checkbox `w-5 h-5` (larger for touch)

### Component 5: ActionFooter

**Type:** Sticky bottom bar

**"Confirmar Firma" button:**
- Primary variant, `h-11 px-6`
- Disabled until: (1) scroll gate released, (2) signature canvas not empty, (3) witness checkbox checked
- Disabled state: `bg-gray-200 text-gray-400 cursor-not-allowed`
- Loading state: spinner + "Procesando..."

**"Cancelar" button:**
- Outline variant
- Opens confirmation dialog: "¿Cancelar la firma? El consentimiento quedará como borrador."

---

## Form Fields

| Field | Type | Required | Validation | Error Message |
|-------|------|----------|------------|---------------|
| signature_data | canvas/base64 | Yes | Canvas not empty | "Se requiere la firma del paciente" |
| scroll_completed | boolean | Yes | Must reach end | (Enforced by UI gate, no error message shown) |
| witness_confirmed | boolean | Yes | Must be checked | "Confirma que el paciente leyó el documento" |

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Load consent for signing | `/api/v1/consents/{id}` | GET | `specs/consents/IC-05` | 1min |
| Submit signature | `/api/v1/consents/{id}/sign` | POST | `specs/consents/IC-05` | none |

**POST /sign payload:**
```json
{
  "signature_data": "data:image/png;base64,iVBORw0...",
  "signature_hash": "sha256:abc123...",
  "signed_at": "2026-02-25T10:30:00Z",
  "witness_user_id": "uuid",
  "patient_confirmed": true,
  "user_agent": "Mozilla/5.0...",
  "client_ip": "192.168.1.1"
}
```

**SHA-256 hash computation (client-side):**
```typescript
async function hashSignature(dataUrl: string): Promise<string> {
  const buffer = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(dataUrl));
  return 'sha256:' + Array.from(new Uint8Array(buffer)).map(b => b.toString(16).padStart(2, '0')).join('');
}
```

### State Management

**Local State (useState):**
- `isScrollCompleted: boolean` — scroll gate state
- `scrollPercent: number` — 0–100
- `isSignatureEmpty: boolean` — canvas state
- `isWitnessConfirmed: boolean`
- `isSubmitting: boolean`

**Global State (Zustand):**
- `authStore.user` — witness user ID for audit

**Server State (TanStack Query):**
- Query key: `['consent', consentId, tenantId]` — staleTime 1min
- Mutation: `useSignConsent(consentId)` — POST signature

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Scroll consent text | Scroll | Progress bar fills, gate releases at 100% | Progress bar animates, lock icon disappears from pad |
| Click "Ir al final" | Button click | Smooth scroll to bottom of text | Gate releases after scroll |
| Draw signature | Touch/mouse on canvas | Ink line appears | Live canvas render |
| Click "Limpiar firma" | Button click | Canvas cleared | Canvas empties |
| Check witness checkbox | Click | Checkbox checked | Confirm button enables (if all conditions met) |
| Click "Confirmar Firma" | Button click | Hash → POST → PDF generated | Spinner → success toast |
| Click "Cancelar" | Button click | Confirmation dialog | Dialog |

### Animations/Transitions

- Scroll gate release: signature pad fades in from `opacity-40` to `opacity-100` + lock icon disappears (200ms)
- "Ir al final" button: fades out once at 80% scroll
- Submit button state transitions: smooth color change from disabled gray to primary blue as conditions met
- Post-submit: success checkmark animation before navigating away

---

## Loading & Error States

### Loading State
- Consent text: skeleton text lines (10 lines, varying widths) filling scroll area
- Signature pad: shows immediately (just canvas, not locked by skeleton — locked by scroll gate)

### Error State
- Load failure: full-page error "No se pudo cargar el consentimiento. Intenta de nuevo." with Reintentar
- Submit failure 500: toast "Error al procesar la firma. La firma no fue guardada. Intenta de nuevo."
- Submit failure 409 (already signed): toast "Este consentimiento ya fue firmado." with "Ver consentimiento" link
- Network offline during submit: toast "Sin conexión. La firma será enviada cuando se restablezca la conexión." (offline queue — future enhancement, V1 shows error and retains canvas)

### Empty State
Not applicable — consent text always present (loaded from template).

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Full-page view. Text in upper 50% screen, signature pad in lower 50%. "Ir al final" button large (56px). Font size increased to 16px minimum to prevent iOS zoom on interaction. |
| Tablet (640-1024px) | Primary use case. Full-page layout. Signature pad height 200px. Touch-optimized — palm rejection enabled. All 44px touch targets. Landscape orientation supported. |
| Desktop (> 1024px) | Two-panel: text left (60%), signature right (40%). Signature pad with mouse input. |

**Tablet priority:** Critical — this is the primary signing device. Must work flawlessly on iPad and Android tablets, both orientations.

---

## Accessibility

- **Focus order:** Page header → consent text scroll area → scroll progress indicator → signature canvas → clear button → witness checkbox → confirm button
- **Screen reader:** Scroll area `role="document"` `aria-label="Texto del consentimiento informado"`. Progress bar `role="progressbar"` `aria-valuenow="{percent}"` `aria-valuemin="0"` `aria-valuemax="100"` `aria-label="Lectura del documento: {percent}%"`. Signature canvas `aria-label="Área de firma del paciente — {locked/unlocked}"`. Witness checkbox `aria-required="true"`.
- **Keyboard navigation:** Page Down / End to scroll consent text to bottom (triggers gate release). Tab to canvas, Enter to activate drawing mode (then mouse/touch draws). Tab to witness checkbox, Space to check. Tab to confirm button, Enter to submit.
- **Color contrast:** WCAG AA. Locked state uses both reduced opacity and lock icon (not color alone). Progress bar has sufficient contrast against gray track.
- **Legal accessibility note:** The scroll-to-bottom gate is a legal UX requirement per Resolución 1888. Screen readers that read the full document via synthetic scroll must also trigger the gate — gate also releases after `aria-live` region announces end of document.
- **Language:** All labels, gate messages, confirmations in es-419.

---

## Design Tokens

**Colors:**
- Page background: `bg-gray-50`
- Consent text container: `bg-white shadow-sm border border-gray-200`
- Consent text: `text-gray-800 text-base leading-relaxed`
- Scroll gate message: `text-amber-600`
- Progress bar fill: `bg-primary-500`
- Progress bar track: `bg-gray-200`
- Signature canvas border (locked): `border-gray-200 bg-gray-50`
- Signature canvas border (active): `border-gray-300 bg-white`
- Lock icon overlay: `text-gray-400`
- Confirm button (disabled): `bg-gray-200 text-gray-400`
- Confirm button (enabled): `bg-primary-600 text-white hover:bg-primary-700`

**Typography:**
- Page title: `text-lg font-bold text-gray-900`
- Patient/doctor meta: `text-sm text-gray-600`
- Consent text: `font-inter text-base leading-relaxed text-gray-800`
- Gate message: `text-sm font-medium text-amber-600`
- "Limpiar firma": `text-sm text-gray-500 underline`
- Witness checkbox label: `text-sm text-gray-700`

**Spacing:**
- Page padding: `px-4 py-4 md:px-8 md:py-6`
- Consent text container max-height: `max-h-[55vh]` (mobile: `max-h-[45vh]`)
- Signature pad height: `h-44 md:h-52` (176px / 208px)
- Footer padding: `pt-4 border-t border-gray-200`

**Border Radius:**
- Consent text container: `rounded-2xl`
- Signature pad: `rounded-xl`
- "Ir al final" button: `rounded-full`

---

## Implementation Notes

**Dependencies (npm):**
- `react-signature-canvas` or custom canvas hook — signature capture
- `@tanstack/react-query` — consent load + sign mutation
- `lucide-react` — Lock, Unlock, ChevronDown, CheckCircle, X, RotateCcw
- `date-fns` — signing date formatting
- Web Crypto API (browser built-in) — SHA-256 hash computation

**File Location:**
- Page: `src/app/(dashboard)/patients/[id]/consentimientos/[consentId]/firmar/page.tsx`
- Components: `src/components/consents/ConsentSignScreen.tsx`, `src/components/consents/SignaturePad.tsx`, `src/components/consents/ConsentTextViewer.tsx`
- Hook: `src/hooks/useSignConsent.ts`, `src/hooks/useScrollGate.ts`

**Hooks Used:**
- `useAuth()` — witness user ID
- `useQuery(['consent', consentId])` — consent text + metadata
- `useSignConsent(consentId)` — POST mutation
- `useScrollGate(containerRef)` — custom hook tracking scroll to bottom
- `useSignatureCanvas(canvasRef)` — custom hook for canvas clear/export

**Orientation handling:**
```typescript
// On orientation change, resize canvas preserving drawn content
useEffect(() => {
  const handler = () => {
    const imgData = canvasRef.current?.toDataURL();
    // Resize canvas
    if (imgData) canvasRef.current?.fromDataURL(imgData);
  };
  window.addEventListener('orientationchange', handler);
  return () => window.removeEventListener('orientationchange', handler);
}, []);
```

---

## Test Cases

### Happy Path
1. Patient reads full consent and signs on tablet
   - **Given:** Doctor opens signing screen, consent text loaded
   - **When:** Patient scrolls to bottom of consent (progress reaches 100%) → draws signature → doctor checks witness box → "Confirmar Firma"
   - **Then:** SHA-256 computed client-side, POST /sign fires, consent status → `signed`, toast "Consentimiento firmado correctamente", navigate to FE-IC-01

2. "Ir al final" shortcut used
   - **Given:** Long consent text, patient taps "Ir al final" button
   - **When:** Page smooth-scrolls to bottom
   - **Then:** Scroll gate releases, signature pad becomes active

### Edge Cases
1. Patient clears signature and re-signs
   - **Given:** Signature drawn
   - **When:** "Limpiar firma" clicked, then new signature drawn
   - **Then:** Canvas cleared cleanly, new signature captures without artifacts

2. Tablet rotated during signing
   - **Given:** Signature partially drawn in portrait
   - **When:** Device rotated to landscape
   - **Then:** Canvas resizes, drawn content preserved and scaled (or cleared with notification "La firma se borró al girar el dispositivo")

### Error Cases
1. Network drops during signature submission
   - **Given:** No internet during POST /sign
   - **When:** "Confirmar Firma" clicked
   - **Then:** Toast "Sin conexión. La firma no fue guardada. Intenta de nuevo." — canvas preserved, button re-enabled

2. Consent already signed by another session
   - **Given:** Same consent opened in two browser tabs
   - **When:** Second tab submits signature
   - **Then:** 409 response → toast "Este consentimiento ya fue firmado." — redirect to FE-IC-01

---

## Acceptance Criteria

- [ ] Full consent text displayed in scrollable container
- [ ] Scroll progress bar updates in real-time
- [ ] Scroll gate: signature pad locked until 100% scroll reached
- [ ] "Ir al final" auto-scroll button visible until 80% scroll
- [ ] Gate message "Desplázate hasta el final..." disappears on completion
- [ ] Signature canvas unlocks on scroll completion (visual unlock animation)
- [ ] Signature canvas touch-optimized: smooth ink rendering, palm rejection
- [ ] "Limpiar firma" button resets canvas
- [ ] Signature empty check before submit
- [ ] Witness confirmation checkbox required
- [ ] Submit button disabled until all 3 conditions met (scroll, signature, checkbox)
- [ ] SHA-256 hash computed client-side before POST
- [ ] Submit spinner on button during processing
- [ ] Success toast + navigate to FE-IC-01 after signing
- [ ] Cancel with confirmation dialog (consent stays as draft)
- [ ] Orientation change handling (canvas resize)
- [ ] Loading skeleton for consent text
- [ ] Error states for load failure and submit failure
- [ ] Responsive: tablet-optimized (primary), full-page mobile, two-panel desktop
- [ ] All touch targets min 44px
- [ ] Keyboard: Page Down / End triggers scroll gate
- [ ] ARIA: progressbar role, canvas label, checkbox required
- [ ] All labels in es-419
- [ ] Complies with Colombia Ley 527/1999 and Resolución 1888 audit requirements

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
