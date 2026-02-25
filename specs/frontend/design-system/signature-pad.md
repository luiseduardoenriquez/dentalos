# Signature Pad — Design System Component Spec

## Overview

**Spec ID:** FE-DS-14

**Component:** `SignaturePad`

**File:** `src/components/shared/signature-pad.tsx`

**Description:** Canvas-based digital signature capture component for collecting legally valid patient and professional signatures on clinical consents and records. Supports both mouse and touch/stylus input. Output is base64 PNG. Compliant with Colombia Ley 527/1999 (digital signatures), paired with SHA-256 hash and audit trail stored server-side.

**Design System Ref:** `FE-DS-01` (§5.x clinical components)

**Backend Spec:** `specs/patients/digital-signature.md`

---

## Props Table

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `onSignatureChange` | `(dataUrl: string \| null) => void` | — | Yes | Called with base64 PNG when stroke detected or cleared |
| `width` | `number` | `600` | No | Canvas width in pixels |
| `height` | `number` | `200` | No | Canvas height in pixels |
| `placeholder` | `string` | `"Firme aquí"` | No | Watermark text shown on empty canvas |
| `strokeColor` | `string` | `"#1F2937"` | No | Ink color (dark gray for scanned appearance) |
| `strokeWidth` | `number` | `2` | No | Pen stroke width in pixels |
| `backgroundColor` | `string` | `"#FFFFFF"` | No | Canvas background (always white for document embedding) |
| `disabled` | `boolean` | `false` | No | Prevents new strokes (for view-only mode) |
| `initialSignature` | `string` | — | No | Pre-load an existing signature (base64 PNG) |
| `required` | `boolean` | `false` | No | Marks the field as required in the form context |
| `label` | `string` | — | No | Label text above the signature area |
| `signerName` | `string` | — | No | Name printed below signature line |
| `signerRole` | `string` | — | No | Role printed below signature line |

---

## Visual Structure

```
[Label: "Firma del paciente"]

+------------------------------------------+
|                                          |
|                                          |
|          [ Firme aquí ]                  |  ← watermark (hidden once stroke detected)
|                                          |
|                                          |
+------------------------------------------+
________________________
María García Torres            ← signerName + signerRole printed below
Paciente

[Borrar]         [✓ Firma válida]
```

**Canvas container classes:**
```
relative border-2 border-gray-300 rounded-lg bg-white
overflow-hidden cursor-crosshair
```

**On focus (tablet/stylus):** Border changes to `border-teal-500 ring-2 ring-teal-500/20`.

**After signature detected:** Border changes to `border-gray-400`.

---

## Placeholder Watermark

Centered in canvas when no strokes have been drawn:

```
"Firme aquí"
```

**Style:** `text-gray-300 text-lg font-light italic`, centered via absolute positioning.

**Behavior:** Disappears as soon as first stroke begins (`opacity: 0` transition 200ms).

---

## Controls

**Layout:** Below the canvas, full width. Two areas: left (clear) + right (status).

### Clear Button

- "Borrar" — ghost variant with `Eraser` icon
- Always visible (enabled only when canvas has strokes)
- Disabled state when canvas is empty: `opacity-50 cursor-not-allowed`
- `aria-label="Borrar firma"`

**Click action:**
1. Canvas cleared (white fill)
2. `onSignatureChange(null)` called
3. Placeholder watermark reappears
4. Status indicator resets

### Status Indicator

Right side, inline text:

- Empty: `text-sm text-gray-400 "Sin firma"`
- Has strokes: `text-sm text-green-600 flex items-center gap-1` → `[CheckCircle2 16px] Firma capturada`
- Required + empty + attempted submit: `text-sm text-red-600` → `[AlertCircle 16px] Firma requerida`

---

## Signer Info Block (Below Canvas)

Optional, shown when `signerName` is provided.

```
_________________________
[signerName]
[signerRole]
```

**Signature line:** 1px solid gray-400, full width of canvas.

**Name text:** `text-sm text-gray-700 font-medium mt-1`

**Role text:** `text-xs text-gray-500`

This block is NOT on the canvas — it's HTML rendered below. The exported PNG includes only what's on the canvas.

---

## Canvas Implementation

### Drawing Engine

```typescript
// Core pointer/touch drawing logic
const draw = (x: number, y: number) => {
  if (!ctx || !isDrawing.current) return
  ctx.lineTo(x, y)
  ctx.stroke()
  ctx.beginPath()
  ctx.moveTo(x, y)
}

// Pointer events (unified mouse + touch + stylus)
canvas.addEventListener('pointerdown', (e) => {
  e.preventDefault()
  isDrawing.current = true
  ctx.beginPath()
  ctx.moveTo(e.offsetX, e.offsetY)
  canvas.setPointerCapture(e.pointerId)
})

canvas.addEventListener('pointermove', (e) => {
  if (!isDrawing.current) return
  draw(e.offsetX, e.offsetY)
})

canvas.addEventListener('pointerup', () => {
  isDrawing.current = false
  onSignatureChange(canvas.toDataURL('image/png'))
})
```

**Context settings:**
```typescript
ctx.strokeStyle = strokeColor    // '#1F2937'
ctx.lineWidth = strokeWidth      // 2
ctx.lineCap = 'round'
ctx.lineJoin = 'round'
ctx.imageSmoothingEnabled = true
```

**Pressure support:** If `e.pressure` is available (Apple Pencil, Wacom stylus), scale line width: `ctx.lineWidth = strokeWidth * (0.5 + e.pressure * 0.8)`.

### Empty Detection

A signature is considered empty (not valid) if:

```typescript
function isCanvasEmpty(canvas: HTMLCanvasElement): boolean {
  const ctx = canvas.getContext('2d')!
  const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data
  // Check if any pixel is non-white (not background)
  for (let i = 0; i < data.length; i += 4) {
    if (data[i] < 250 || data[i+1] < 250 || data[i+2] < 250) return false
  }
  return true
}
```

Minimum valid signature: at least 100 non-white pixels (prevents accidental single-dot signatures).

---

## Responsive Behavior

Canvas scales to container width maintaining aspect ratio:

```typescript
// Responsive canvas sizing
const containerWidth = containerRef.current?.offsetWidth ?? 600
const scale = containerWidth / props.width
const scaledHeight = props.height * scale

canvas.width = containerWidth
canvas.height = scaledHeight
```

**Width behavior:**
- Mobile (< 640px): Canvas fills full width (`w-full`), minimum 280px
- Tablet: Canvas fills card/modal body width, up to 600px
- Desktop: Fixed at specified width or capped at 600px

### Landscape Prompt (Mobile)

On very small screens (< 400px width), the signature pad shows a landscape orientation prompt:

```
+------------------------------------------+
| [RotateCw icon]                          |
| Rota el dispositivo para firmar mejor    |
| [Continuar de todas formas]              |
+------------------------------------------+
```

The prompt can be dismissed. This is a suggestion, not a blocker.

---

## Validation (React Hook Form integration)

```tsx
// In a consent form:
<Controller
  name="firma_paciente"
  control={control}
  rules={{
    validate: (val) => {
      if (!val) return 'La firma del paciente es requerida'
      return true
    }
  }}
  render={({ field, fieldState }) => (
    <SignaturePad
      label="Firma del paciente"
      signerName={patient.nombre_completo}
      signerRole="Paciente"
      required
      onSignatureChange={field.onChange}
      initialSignature={field.value}
    />
  )}
/>
```

---

## Output and Security

**Output:** `canvas.toDataURL('image/png')` — base64-encoded PNG string.

**Client-side:** The base64 PNG is transmitted to the API as part of the form payload.

**Server-side:** API layer generates SHA-256 hash of the PNG content + timestamp + user_id. Hash stored in `signatures` table alongside the base64. Audit log entry created.

**Colombia Ley 527/1999:** Displayed metadata (date, time, IP, user agent) is stored server-side and can be rendered on the signed document PDF. The client component does NOT need to handle the legal metadata — it only captures the visual signature.

---

## View-Only Mode

When `disabled={true}` and `initialSignature` is provided:

- Canvas shows the existing signature image (drawn from `initialSignature` base64)
- No pointer events (cursor: default)
- Clear button hidden
- Border: `border-gray-200`
- Status text: "Firmado el [date]" if timestamp passed via `signedAt` prop

---

## Accessibility

- **Role:** The canvas element has `role="img"` with `aria-label="Área de firma — dibuja tu firma usando tu dedo o lápiz"`.
- **Label association:** `<label>` above with `htmlFor` pointing to a wrapper `id`. Canvas itself cannot receive `htmlFor`, so use `aria-labelledby`.
- **Keyboard:** Tab reaches the clear button and any focus in the form. The canvas drawing itself is not keyboard-accessible (by nature). For keyboard-only users, provide alternative: "¿No puedes firmar? [Usar firma tipografiada]" fallback option (optional).
- **Required:** `aria-required="true"` on a wrapping div. Error state announced via `role="alert"`.
- **Status:** `aria-live="polite"` on the status indicator div so "Firma capturada" / "Sin firma" is announced.

---

## Usage Examples

```tsx
// Consent form signature
<SignaturePad
  label="Firma del paciente"
  signerName={patient.nombre_completo}
  signerRole="Paciente"
  required
  onSignatureChange={(dataUrl) => setValue('firma_paciente', dataUrl)}
/>

// Doctor signature (view only after signing)
<SignaturePad
  label="Firma del profesional"
  signerName="Dr. Alejandro Gómez"
  signerRole="Odontólogo — TP 12345"
  disabled
  initialSignature={existingSignatureBase64}
/>

// Minimal usage (no signer info)
<SignaturePad
  onSignatureChange={handleSignature}
  width={400}
  height={150}
/>
```

---

## Implementation Notes

**File Location:** `src/components/shared/signature-pad.tsx`

**Dependencies:** No external library needed — pure canvas API with pointer events.

**Performance:** Canvas operations are synchronous. For 600x200px canvas, `getImageData` check is ~0.5ms. Acceptable.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec — Colombia Ley 527/1999 compliance |
