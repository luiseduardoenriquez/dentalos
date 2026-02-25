# Input — Design System Component Spec

## Overview

**Spec ID:** FE-DS-03

**Component:** `Input`, `Textarea`, `PhoneInput`

**File:** `src/components/ui/input.tsx`

**Description:** Form input components for collecting user data. Integrated with React Hook Form via `Controller` or `register()`. Includes all common input types used across DentalOS clinical and administrative forms.

**Design System Ref:** `FE-DS-01` (§4.2)

---

## Props Table — `Input`

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `label` | `string` | — | No | Label text rendered above the input |
| `type` | `'text' \| 'email' \| 'password' \| 'number' \| 'date' \| 'tel' \| 'url'` | `'text'` | No | HTML input type |
| `placeholder` | `string` | — | No | Placeholder text in Spanish |
| `error` | `string` | — | No | Error message displayed below input |
| `helperText` | `string` | — | No | Helper text below input (hidden if error present) |
| `prefix` | `ReactNode` | — | No | Content inside left side of input (icon or text) |
| `suffix` | `ReactNode` | — | No | Content inside right side of input (icon or text) |
| `disabled` | `boolean` | `false` | No | Disables the input |
| `readOnly` | `boolean` | `false` | No | Makes input read-only |
| `required` | `boolean` | `false` | No | Marks field as required (adds * to label) |
| `className` | `string` | — | No | Additional classes on wrapper |
| `inputClassName` | `string` | — | No | Additional classes on the input element |
| All native `<input>` props | — | — | No | Forwarded to underlying `<input>` |

## Props Table — `Textarea`

Extends all `Input` props except `type`, `prefix`, `suffix`. Adds:

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `rows` | `number` | `4` | Initial visible rows |
| `maxLength` | `number` | — | Character limit (shows counter if set) |
| `autoGrow` | `boolean` | `false` | Expands height as user types |

---

## Visual Structure

```
[Label text] [Required asterisk*]         ← text-sm font-medium text-gray-700
+------------------------------------------+
| [Prefix icon/text] [Input value]         | ← h-10 border rounded-md
| [Suffix icon/text]                       |
+------------------------------------------+
[Helper text or Error message]             ← text-xs
```

**Label:** `text-sm font-medium text-gray-700`. Required asterisk: `text-red-500` space after label.

**Input element base classes:**
```
w-full h-10 rounded-md border px-3 py-2
text-sm text-gray-900 bg-white
placeholder:text-gray-400
transition-colors duration-150
outline-none
```

---

## States

| State | Border | Ring | Background | Label Color | Text |
|-------|--------|------|-----------|-------------|------|
| Default | `border-gray-300` | none | `bg-white` | `text-gray-700` | `text-gray-900` |
| Focus | `border-teal-500` | `ring-2 ring-teal-500/20` | `bg-white` | `text-gray-700` | `text-gray-900` |
| Error | `border-red-500` | `ring-2 ring-red-500/20` | `bg-red-50` | `text-red-600` | `text-gray-900` |
| Disabled | `border-gray-200` | none | `bg-gray-50` | `text-gray-400` | `text-gray-400` |
| Read-only | `border-gray-200` | none | `bg-gray-50` | `text-gray-600` | `text-gray-600` |
| Valid (optional) | `border-green-500` | `ring-2 ring-green-500/20` | `bg-white` | `text-gray-700` | `text-gray-900` |

**Error message:** `text-xs text-red-600 mt-1` with `AlertCircle` (12px) icon inline.

**Helper text:** `text-xs text-gray-500 mt-1`. Hidden when error is present.

---

## Input Types

### Text / Email / URL

Standard input. Email validates format on blur.

```tsx
<Input
  label="Correo electrónico"
  type="email"
  placeholder="doctor@clinica.com"
  required
  error={errors.email?.message}
  {...register('email')}
/>
```

### Password

Includes show/hide toggle button in the suffix slot.

**Suffix button:** `Eye` / `EyeOff` icon, 16px, `text-gray-400 hover:text-gray-600`. `aria-label="Mostrar contraseña"` / `"Ocultar contraseña"`.

```tsx
<Input
  label="Contraseña"
  type={showPassword ? 'text' : 'password'}
  suffix={
    <button
      type="button"
      onClick={() => setShowPassword(!showPassword)}
      aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
    >
      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
    </button>
  }
/>
```

### Number

Adds `min`, `max`, `step` props. Optional unit suffix text (e.g., "horas", "kg"):

```tsx
<Input
  label="Horas antes del recordatorio"
  type="number"
  min={1}
  max={720}
  suffix={<span className="text-sm text-gray-500 pr-1">horas</span>}
/>
```

### Date

Uses native `<input type="date">` with locale-aware display. Wrapper provides consistent styling. For date range pickers, use the Calendar component (FE-DS-13).

```tsx
<Input
  label="Fecha de nacimiento"
  type="date"
  max={new Date().toISOString().split('T')[0]}
/>
```

### PhoneInput

Specialized component combining country code selector + number input.

**Props:** Extends Input props plus:
- `defaultCountry?: string` — ISO 2-letter code, default `'CO'`
- `onPhoneChange?: (value: string) => void` — returns E.164 format (+573001234567)

**Structure:**
```
+---+-------+-------------------------------+
|🇨🇴| +57 ▾  | 300 123 4567                  |
+---+-------+-------------------------------+
```

Country selector: 36x40px, shows flag emoji + dial code + chevron. Click → popover with country list (searchable, shows flag + country name + dial code).

```tsx
<PhoneInput
  label="Teléfono de contacto"
  defaultCountry="CO"
  onPhoneChange={(val) => setValue('phone', val)}
  error={errors.phone?.message}
/>
```

---

## Textarea

```tsx
<Textarea
  label="Motivo de consulta"
  placeholder="Describe el motivo de consulta del paciente..."
  rows={4}
  maxLength={500}
  autoGrow
  error={errors.motivo?.message}
  {...register('motivo_consulta')}
/>
```

**Character counter** (shown when `maxLength` is set):

```
[Textarea value here...]

                              [247/500]  ← text-xs text-gray-400, right-aligned
```

Counter color changes at 80%: `text-amber-600`, at 95%: `text-red-600`.

**Auto-grow:** Uses `ResizeObserver` or `onInput` to set `height = scrollHeight`. Has `min-height` from `rows` prop and optional `max-height` to prevent infinite growth.

---

## Prefix and Suffix

Used for icons, currency symbols, unit text.

**Prefix examples:**
- Search icon: `<Search className="w-4 h-4 text-gray-400" />`
- Currency: `<span className="text-sm text-gray-500">$</span>`

**Suffix examples:**
- Unit text: `<span className="text-sm text-gray-500">años</span>`
- Clear button: `<X className="w-3 h-3 text-gray-400" />` (only when value is non-empty)
- Copy icon: `<Copy className="w-4 h-4 text-gray-400 cursor-pointer" />`

Prefix/suffix are positioned inside the input box using `relative` wrapper + `absolute` positioned divs:

```css
.input-wrapper { position: relative; }
.prefix { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); }
.suffix { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); }
/* Input gets padding-left: 36px with prefix, padding-right: 36px with suffix */
```

---

## React Hook Form Integration

```tsx
// With register (uncontrolled)
<Input
  label="Nombre completo"
  placeholder="María García Torres"
  error={errors.nombre?.message}
  {...register('nombre', { required: 'Nombre requerido' })}
/>

// With Controller (controlled)
<Controller
  name="rol"
  control={control}
  render={({ field, fieldState }) => (
    <Input
      label="Rol"
      error={fieldState.error?.message}
      {...field}
    />
  )}
/>
```

---

## Accessibility

- **Label association:** Every input has a `<label>` with `htmlFor` matching the input `id`. ID is auto-generated from name if not provided.
- **Error announcement:** Error message element has `role="alert"` and `aria-live="polite"`. Input has `aria-describedby` pointing to error or helper text element.
- **Required:** `aria-required="true"` on required inputs, not just the `required` HTML attribute.
- **Invalid state:** `aria-invalid="true"` when error is present.
- **Password toggle:** Toggle button is `type="button"` to prevent form submission. Has descriptive `aria-label`.
- **Read-only:** `aria-readonly="true"` on read-only inputs.
- **Phone country selector:** Combobox role for country dropdown. `aria-label="Código de país"`.

---

## Responsive Behavior

- Full width by default (`w-full` on wrapper)
- Height remains constant (h-10 for input, variable for textarea)
- Label wraps if text is long (use `truncate` only if guaranteed short)
- On tablet: input touch target is naturally 40px. Combined with 44px row padding in forms, total touch area is sufficient.
- Textarea resizes vertically on mobile if `autoGrow` is set

---

## Usage Examples

```tsx
// NIT input with format helper
<Input
  label="NIT de la clínica"
  type="text"
  placeholder="900.123.456-7"
  helperText="Formato: 9 dígitos seguidos del dígito verificador"
  required
  {...register('nit')}
/>

// Read-only country
<Input
  label="País"
  type="text"
  value="Colombia"
  readOnly
  prefix={<span>🇨🇴</span>}
  helperText="El país no puede cambiarse después del registro"
/>

// Textarea with counter
<Textarea
  label="Observaciones clínicas"
  placeholder="Escribe aquí tus observaciones..."
  maxLength={1000}
  rows={5}
  error={errors.observaciones?.message}
  {...register('observaciones')}
/>
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec |
