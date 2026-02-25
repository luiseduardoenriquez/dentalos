# Firma de Consentimiento Informado — Portal del Paciente (Consent Sign) — Frontend Spec

## Overview

**Screen:** Consent form signing screen in the patient portal. Displays the full consent document (must scroll to bottom to enable the sign button — legal requirement). Patient reads, checks "He leido y acepto", draws signature on canvas pad, and submits. Confirmation screen shows with PDF download option. Mobile-first since most patients sign on their phone.

**Route:** `/portal/consents/{id}/sign` (patient portal, separate auth context)

**Priority:** High

**Backend Specs:** `specs/portal/portal-consent-sign.md` (PP-12)

**Dependencies:** `specs/frontend/portal/portal-dashboard.md`, `specs/frontend/design-system/design-system.md`

---

## User Flow

**Entry Points:**
- Notification link sent via SMS/email "Firma tu consentimiento antes de tu cita"
- Patient portal "Documentos pendientes" → pending consent list → click to sign
- QR code in clinic → signs on patient's own phone at reception

**Exit Points:**
- Successful signing → confirmation screen with PDF download link, then "Volver al portal" button → `/portal`
- "Cancelar" → back to portal documents list `/portal/documents`

**User Story:**
> As a patient, I want to read and sign my consent form from my phone so that I don't have to sign paper forms at the clinic and can review the document at my own pace.

**Roles with access:** `patient` role (patient portal only). Staff cannot sign on patient's behalf from this screen.

---

## Layout Structure

```
+------------------------------------------+
|  Portal logo + clinic branding            |
+------------------------------------------+
|  [Consent Title]                          |
|  [Consent type badge]  [Date]             |
+------------------------------------------+
|                                          |
|  [Document Content — scrollable, full]   |
|                                          |
|  (scroll-to-bottom required)             |
|                                          |
+------------------------------------------+
|  [Scroll progress indicator]             |
|  [Read confirmation check + checkbox]    |
+------------------------------------------+
|  [Signature pad canvas]                  |
|  [Limpiar | Deshacer buttons]            |
+------------------------------------------+
|  [Firmar y Enviar btn] [Cancelar link]   |
+------------------------------------------+
```

**Sections:**
1. Portal header — clinic branding (logo, name, primary color)
2. Consent header — title, type badge, creation date
3. Document content area — scrollable, full rendered text
4. Confirmation bar — scroll progress + "He leido" checkbox
5. Signature pad — canvas for finger/stylus signature
6. Actions — submit and cancel

---

## UI Components

### Component 1: DocumentScrollArea

**Type:** Scrollable content area

**Design:**
- `overflow-y-auto` with `max-h-[50vh] md:max-h-[60vh]` — forces scrolling on shorter screens
- No height limit on very tall screens (desktop)
- Smooth scrolling content: rendered HTML from consent template (sanitized with DOMPurify)
- Typography: `text-base leading-relaxed text-gray-800` — readable font size for legal text (min 16px)
- Padding: `px-5 py-4`

**Scroll tracking:**
- `useRef` on scroll container + `onScroll` handler
- `scrolledToBottom: boolean` — true when `scrollTop + clientHeight >= scrollHeight - 20px` tolerance
- Progress: `Math.min(100, ((scrollTop + clientHeight) / scrollHeight) * 100)` percent

### Component 2: ScrollProgressIndicator

**Type:** Linear progress bar

**Design:**
- Thin `h-1.5` progress bar at top of confirmation bar
- `bg-teal-500` fill, `bg-gray-200` track
- Label: `"Has leido {n}% del documento"` `text-xs text-gray-500` when < 100%
- Label: `"Has leido el documento completo"` with CheckCircle `text-green-600` when 100%

### Component 3: ReadConfirmationCheckbox

**Type:** Checkbox + label

**Enabled when:** `scrolledToBottom === true`

**Disabled state (not scrolled):** `opacity-50 cursor-not-allowed` + tooltip "Lee el documento completo para continuar"

**Enabled state (scrolled):**
- `cursor-pointer` checkbox `accent-teal-600 w-5 h-5`
- Label: `"He leido y acepto el presente consentimiento informado"` `text-sm text-gray-700 font-medium`

**Checking this enables the signature pad and submit button.**

### Component 4: SignaturePad

**Type:** Canvas drawing component

**Specifications:**
- Canvas: `min-w-full min-h-[150px] md:min-h-[180px]` — responsive within container
- Background: `bg-white border-2 border-gray-200 rounded-xl`
- Active recording border: `border-teal-400`
- Guide line: horizontal dashed line `border-dashed border-gray-300 h-px absolute` at 70% vertical center "signing line"
- "Firma aqui" ghost text `text-gray-200 text-2xl font-cursive italic absolute` centered, disappears on first stroke

**State: disabled** (before checkbox checked): `opacity-50 cursor-not-allowed bg-gray-50`

**Stroke smoothing:** Use Bezier curve interpolation for smooth pen strokes.

**Mobile touch:** `touchstart`, `touchmove`, `touchend` events — prevent default scroll during signing.

**Actions below canvas:**
- "Limpiar" (Clear all): `Button variant="ghost" text-sm text-red-500 hover:text-red-700` — clears canvas completely with confirmation pulse animation
- "Deshacer" (Undo last stroke): `Button variant="ghost" text-sm text-gray-500` — removes last drawn stroke. Stack of strokes tracked for undo.
- Stroke count indicator: not visible — used only internally to enable/disable submit

**isEmpty check:** Submit button disabled if canvas has fewer than 5 brush strokes (prevents accidental blank submission).

### Component 5: SignatureSubmitButton

**Enabled when:** `readConfirmed === true AND !isSignatureEmpty`

**Disabled state:** `opacity-50 cursor-not-allowed bg-teal-300` + tooltip "Lee y acepta el documento, luego firma para continuar"

**Enabled state:** `bg-teal-600 hover:bg-teal-700 text-white w-full h-14 text-base font-semibold rounded-xl`

**Loading state:** "Enviando firma..." + Loader2 spinner

---

## Confirmation Screen (Post-Sign)

After successful submission, replaces the entire page content:

```
+------------------------------------------+
|  [Large CheckCircle2 icon, green, 80px]  |
|  "Consentimiento firmado"                |
|  "Tu firma ha sido registrada"           |
|                                          |
|  [Document info: title, date, ID]        |
|                                          |
|  [Descargar PDF btn]                     |
|  [Volver al portal btn]                  |
+------------------------------------------+
```

- Full-page success animation: checkmark draws itself with SVG stroke animation
- PDF download: `GET /api/v1/consents/{id}/pdf` with auth header → blob download
- Auto-navigate to portal after 30 seconds if user doesn't interact (with countdown: "Redirigiendo en X segundos...")

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Get consent document | `/api/v1/portal/consents/{id}` | GET | `specs/portal/portal-consent-sign.md` | 1min |
| Submit signature | `/api/v1/portal/consents/{id}/sign` | POST | `specs/portal/portal-consent-sign.md` | None |
| Download signed PDF | `/api/v1/portal/consents/{id}/pdf` | GET | `specs/portal/portal-consent-sign.md` | None |

### Signature POST Request

```typescript
{
  signature_data_url: string;   // canvas.toDataURL('image/png') — base64
  ip_address: string;           // client IP (sent by backend via header, not client)
  user_agent: string;           // navigator.userAgent
  read_confirmed: true;         // must be true
  timestamp_ms: number;         // Date.now() at submission
}
```

### State Management

**Local State (useState):**
- `scrollPercent: number` — 0-100
- `scrolledToBottom: boolean`
- `readConfirmed: boolean`
- `strokeHistory: ImageData[]` — for undo functionality
- `isSignatureEmpty: boolean`
- `isSubmitting: boolean`
- `signedSuccessfully: boolean`
- `signedConsentId: string | null`

**Server State (TanStack Query):**
- Query: `useQuery({ queryKey: ['portal-consent', id] })` — load document
- Mutation: `useMutation({ mutationFn: submitSignature, onSuccess: () => setSignedSuccessfully(true) })`

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `consent_already_signed` | 409 | "Este consentimiento ya fue firmado anteriormente." |
| `consent_expired` | 410 | "Este consentimiento ha vencido. Contacta a tu clinica." |
| `consent_not_found` | 404 | "Documento no encontrado. El enlace puede estar vencido." |
| `empty_signature` | 400 | "Por favor, firma en el area de firma antes de enviar." |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Scroll document | Scroll | Progress bar updates | Percentage text + bar fill |
| Reach document bottom | Scroll threshold | Checkbox enabled | Checkbox opacity-100, "Has leido el documento" label appears |
| Check "He leido" checkbox | Click | Signature pad enabled | Canvas border changes to teal, ghost text visible |
| Draw signature | Touch/mouse on canvas | Strokes recorded | Real-time drawing |
| Click "Limpiar" | Click | Canvas cleared | Canvas fades, "Firma aqui" ghost reappears |
| Click "Deshacer" | Click | Last stroke removed | Stroke pops off canvas |
| Click "Firmar y Enviar" | Click | POST with canvas data URL | Loading state → success screen |
| Click "Descargar PDF" (success) | Click | Download PDF | Browser file download |
| Click "Volver al portal" | Click | Navigate to `/portal` | Standard navigation |

### Legal Requirement Note

The scroll-to-bottom requirement is intentional UX + legal design. The consent is legally void in Colombia if the patient did not demonstrably read it. The backend logs `read_confirmed: true` and the scroll behavior, which forms part of the audit trail per Ley 527/1999.

### Animations/Transitions

- Scroll progress bar: `transition-all duration-100` smooth fill
- Checkbox enable: `transition-opacity duration-300` from `opacity-50` to `opacity-100`
- Canvas enable: `transition-all duration-200` border change + fade in signing line
- Submit success: SVG checkmark stroke animation `stroke-dashoffset` over 600ms
- Confirmation screen entry: `motion.div opacity: 0 → 1, y: 20 → 0` 400ms

---

## Loading & Error States

### Loading State
- Document loading: skeleton for header `h-6 w-3/4 animate-pulse` + multiple lines `h-4 animate-pulse` simulating paragraph text
- Submit: button loading state, canvas disabled

### Error State
- Load error: centered error card "No pudimos cargar el documento. Intenta de nuevo." + retry + clinic contact info
- Submit error: toast above submit button with error message
- Already signed: full-page notice with link to view signed document

### Empty State
- Not applicable

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Full-screen layout. Document area `max-h-[45vh]`. Signature canvas `min-h-[150px]` full-width. Confirmation buttons full-width stacked. Signature pad optimized for thumb/finger signing. |
| Tablet (640-1024px) | Centered `max-w-2xl`. Document area larger `max-h-[60vh]`. Canvas taller `min-h-[180px]`. |
| Desktop (> 1024px) | `max-w-2xl` centered. Full document may not need scroll on wide monitors. Document + signature side by side layout not used (preserves reading flow). |

**Tablet priority:** High — patients often sign on clinic iPad. Canvas must respond accurately to Apple Pencil and finger touches. Prevent page scroll while drawing on canvas.

---

## Accessibility

- **Focus order:** Document scroll area (focusable with Tab, arrows scroll) → Checkbox → Canvas → Clear → Undo → Submit → Cancel
- **Screen reader:** Scroll progress region `aria-live="polite"` announces when document fully read. Checkbox `aria-describedby` pointing to scroll status. Canvas `role="application" aria-label="Area de firma. Usa el mouse o el dedo para firmar."`. Submit button `aria-disabled` when conditions not met, with `aria-describedby` explaining why.
- **Keyboard navigation:** Tab focuses canvas. Space/Enter toggles checkbox. Arrow keys scroll document when document is focused. Note: canvas signing is not achievable via keyboard — provide alternative: "¿No puedes firmar digitalmente? Llama a tu clinica al {phone}."
- **Color contrast:** Legal text body minimum `text-base text-gray-800` on white — meets WCAG AA. All interactive elements meet contrast requirements.
- **Language:** All labels, legal text rendering, and messages in es-419.

---

## Design Tokens

**Colors:**
- Portal header: clinic's primary color (from tenant branding config)
- Progress bar: `bg-teal-500`
- Checkbox accent: `accent-teal-600`
- Canvas border idle: `border-gray-200`
- Canvas border active: `border-teal-400`
- Submit enabled: `bg-teal-600 text-white`
- Submit disabled: `bg-teal-300 text-white opacity-60`
- Success icon: `text-green-500`
- Document text: `text-gray-800 leading-relaxed`

**Typography:**
- Consent title: `text-xl font-bold text-gray-900`
- Document body: `text-base leading-relaxed text-gray-800` (16px minimum for legal readability)
- Checkbox label: `text-sm font-medium text-gray-700`
- Progress label: `text-xs text-gray-500`
- Submit button: `text-base font-semibold`

**Spacing:**
- Page: `max-w-2xl mx-auto px-4 py-6`
- Document area padding: `px-5 py-4`
- Signature pad margin: `mt-5`
- Actions row: `mt-6 space-y-3`

---

## Implementation Notes

**Dependencies (npm):**
- `react-signature-canvas` or custom canvas implementation with touch support
- `dompurify` — sanitize HTML consent document before rendering
- `lucide-react` — CheckCircle2, Download, Loader2, X, Undo2
- `framer-motion` — confirmation screen animation

**File Location:**
- Page: `src/app/(portal)/consents/[id]/sign/page.tsx`
- Components: `src/components/portal/ConsentSignPage.tsx`, `src/components/portal/SignaturePad.tsx`, `src/components/portal/ConsentDocument.tsx`

**Hooks Used:**
- `useQuery(['portal-consent', id])` — load document
- `useMutation()` — submit signature
- `useRef` on scroll container + `useCallback` for scroll handler

**Canvas Implementation Note:**
- Use `HTMLCanvasElement` directly with pointer events for cross-device compatibility
- Scale canvas for `devicePixelRatio` to prevent blurry signatures on Retina displays
- Use `ctx.save()`/`ctx.restore()` for undo stack (save full ImageData snapshots, max 20)

---

## Test Cases

### Happy Path
1. Patient signs on mobile
   - **Given:** Patient receives SMS link to consent
   - **When:** Opens on phone, scrolls to bottom, checks checkbox, draws signature, taps submit
   - **Then:** Confirmation screen with checkmark, PDF download available

### Edge Cases
1. Patient tries to submit without scrolling
   - **Given:** Document loaded, patient does not scroll
   - **When:** Checkbox is visible but disabled
   - **Then:** Checkbox cursor-not-allowed, submit disabled, tooltip explains requirement

2. Patient clears and re-signs
   - **Given:** Patient drew an unsatisfactory signature
   - **When:** Taps "Limpiar", draws new signature
   - **Then:** Canvas cleared, new signature recorded, submit still enabled

### Error Cases
1. Consent already signed
   - **Given:** Patient follows stale link after already signing
   - **When:** Page loads
   - **Then:** Full-page "Este consentimiento ya fue firmado" notice with link to view signed document

2. Network error on submit
   - **Given:** Submit clicked, then connection lost
   - **When:** POST fails
   - **Then:** Error toast "Error al enviar la firma. Intenta de nuevo." Submit re-enabled.

---

## Acceptance Criteria

- [ ] Consent document rendered in full with scroll area
- [ ] "He leido" checkbox disabled until user scrolls to bottom
- [ ] Scroll progress bar updates in real-time
- [ ] Signature pad enabled only after checkbox is checked
- [ ] Canvas supports touch (finger/stylus) and mouse drawing
- [ ] "Limpiar" clears canvas completely
- [ ] "Deshacer" removes last stroke
- [ ] Submit disabled if signature canvas is empty
- [ ] POST includes canvas data URL, read confirmation, timestamp
- [ ] Confirmation screen with animated checkmark + PDF download
- [ ] All error codes handled with Spanish messages
- [ ] Legal requirement: scroll-to-bottom enforced (cannot be bypassed client-side)
- [ ] Mobile-first: responsive on all screen sizes
- [ ] Canvas scaled for Retina displays
- [ ] Accessibility: aria-disabled submit with explanation, canvas role=application
- [ ] Spanish (es-419) throughout

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
