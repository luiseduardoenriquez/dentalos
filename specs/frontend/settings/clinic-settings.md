# Configuración de Clínica — Frontend Spec

## Overview

**Spec ID:** FE-S-01

**Screen:** Settings page for clinic profile, branding, and regional configuration.

**Route:** `/settings/clinic`

**Priority:** High

**Backend Specs:** `specs/tenants/tenant-settings-update.md`, `specs/tenants/tenant-settings-get.md`

**Dependencies:** `FE-DS-01` (design system), `FE-DS-02` (button), `FE-DS-03` (input), `FE-DS-04` (select), `FE-DS-10` (card)

---

## User Flow

**Entry Points:**
- Sidebar nav: Configuración → Clínica
- Onboarding wizard final step

**Exit Points:**
- Any other settings section
- Back to dashboard

**User Story:**
> As a clinic_owner, I want to configure my clinic's name, contact info, branding, and regional settings so that documents, invoices, and patient communications reflect accurate clinic data.

**Roles with access:** `clinic_owner` only. Doctors and other roles see a read-only view without save buttons.

---

## Layout Structure

```
+------------------------------------------+
|              Header (h-16)               |
+--------+---------------------------------+
|        |  Page Header: "Configuración"   |
| Side-  |  Breadcrumb: Configuración / Clínica |
|  bar   +---------------------------------+
|        |  [Section 1: Info Clínica]      |
|        |  [Section 2: Marca]             |
|        |  [Section 3: Regional]          |
+--------+---------------------------------+
```

**Sections:**
1. Info Clínica — name, address, NIT/RUT, phone, email
2. Marca — logo upload with crop, primary color picker
3. Regional — country (read-only), timezone, currency, language

Each section is an independent card with its own Save button.

---

## UI Components

### Section Card Wrapper

**Type:** Card

**Design System Ref:** `frontend/design-system/card.md`

**Behavior:**
- Each section renders inside a `Card` with a header (`text-lg font-semibold`) and a footer with a "Guardar" button
- Unsaved changes indicator: orange dot beside section title when form is dirty
- Save only affects that section (independent PATCH calls)

---

## Form Fields

### Section 1: Info Clínica

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| nombre_clinica | text | Yes | 2-100 chars | "Nombre requerido" | "Clínica Dental Sonrisa" |
| direccion | text | Yes | 5-200 chars | "Dirección requerida" | "Calle 72 # 10-45, Bogotá" |
| numero_documento | text | Yes | NIT format: 9 digits + check digit | "NIT inválido" | "900.123.456-7" |
| telefono | phone | Yes | Country-specific format | "Teléfono inválido" | "+57 300 123 4567" |
| email_clinica | email | Yes | Valid email | "Email inválido" | "info@clinica.com" |
| sitio_web | url | No | Valid URL or empty | "URL inválida" | "https://clinica.com" |

### Section 2: Marca

| Field | Type | Required | Validation | Error Message | Notes |
|-------|------|----------|------------|---------------|-------|
| logo | file | No | JPG/PNG/SVG, max 2MB | "Archivo muy grande o formato no soportado" | Drag-drop zone with crop modal |
| color_primario | color | No | Valid hex color | "Color inválido" | Preset palette + custom hex input |

### Section 3: Regional

| Field | Type | Required | Validation | Error Message | Notes |
|-------|------|----------|------------|---------------|-------|
| pais | select | Yes | Read-only (set at registration) | — | Shows flag emoji + country name |
| zona_horaria | select | Yes | Valid IANA timezone | "Zona horaria requerida" | Filtered by country |
| moneda | text | Yes | Auto-derived from country | — | Read-only, shows "COP - Peso Colombiano" |
| idioma | select | Yes | es-419, es-CO, en-US | "Idioma requerido" | Dropdown |

---

## Subcomponent: Logo Upload

**Flow:**
1. Drag file onto dashed-border zone OR click to open file picker
2. File selected → open crop modal (`FE-DS-06` lg size)
3. Crop modal: react-image-crop library, aspect ratio lock 1:1 (square) or free
4. "Aceptar" crops and sets preview; "Cancelar" discards selection
5. Preview shows 80x80px cropped logo in clinic info header

**States:**
- Empty: dashed border zone, upload icon, "Arrastra tu logo aquí o haz clic"
- Uploading: progress bar overlay on preview
- Uploaded: thumbnail + "Cambiar" and "Eliminar" buttons
- Error: red border + error text below

**Constraints:**
- Accepted types: JPG, PNG, SVG, WebP
- Max size: 2 MB
- Output stored as signed URL in tenant settings

---

## Subcomponent: Color Picker

**Layout:** Horizontal row of 8 preset color swatches (30x30px circles) + "Personalizado" input.

**Preset swatches:**
- `#0F766E` (teal-700, DentalOS default)
- `#2563EB` (blue-600)
- `#7C3AED` (violet-600)
- `#DC2626` (red-600)
- `#D97706` (amber-600)
- `#16A34A` (green-600)
- `#0284C7` (sky-600)
- `#DB2777` (pink-600)

**Custom input:** `#RRGGBB` hex field + live preview swatch.

**Behavior:** Selected color is shown with a checkmark overlay on the swatch. Live preview bar below showing "Así se ve tu color primario" with a sample button rendered in chosen color.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Load settings | `/api/v1/tenants/{tenant_id}/settings` | GET | `specs/tenants/tenant-settings-get.md` | 5min |
| Save clinic info | `/api/v1/tenants/{tenant_id}/settings` | PATCH | `specs/tenants/tenant-settings-update.md` | Invalidate |
| Upload logo | `/api/v1/tenants/{tenant_id}/logo` | POST | `specs/tenants/tenant-settings-update.md` | Invalidate |

### State Management

**Local State (useState):**
- `isDirty: Record<'info' | 'branding' | 'regional', boolean>` — tracks unsaved sections
- `cropModalOpen: boolean`
- `cropImageSrc: string | null`

**Global State (Zustand):**
- `tenantStore`: `currentTenant.settings` — updated on successful save

**Server State (TanStack Query):**
- Query key: `['tenant-settings', tenantId]`
- Stale time: 5 minutes
- Mutation: `useMutation()` with `onSuccess` invalidating query and showing toast

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Edit any field | Typing/selecting | Form becomes dirty | Orange unsaved dot on card header |
| Click "Guardar" (any section) | Button click | PATCH to API | Loading spinner on button; success toast "Configuración guardada" |
| Upload logo | Drag or click | Crop modal opens | — |
| Crop and accept | Click "Aceptar" in modal | Preview updates | "Logo actualizado" on save |
| Change color swatch | Click swatch | Color field updates, live preview refreshes | Immediate visual update |
| Navigate away with unsaved changes | Route change | Confirmation dialog: "Tienes cambios sin guardar. ¿Deseas salir?" | "Quedarme" / "Salir sin guardar" |

### Animations/Transitions

- Section cards fade in sequentially (stagger 100ms each) on page load
- Unsaved dot animates in with `scale 0 → 1` (150ms)
- Crop modal: standard modal open/close animation (FE-DS-06)

---

## Loading & Error States

### Loading State
- Page skeleton: three card skeletons stacked vertically, each with label+input row repeating 4 times (FE-DS-17 form-skeleton variant)

### Error State
- API load failure: inline alert card "No se pudieron cargar los ajustes. Intenta de nuevo." with retry button
- Save failure: toast error (persistent until dismissed) with API error message

### Empty State
- Not applicable (settings always pre-populated from registration)

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Single column, full-width cards, stacked inputs |
| Tablet (640-1024px) | Single column cards, 2-column input grid inside cards |
| Desktop (> 1024px) | Max-width container (max-w-3xl), single column cards, 2-column input grid |

**Tablet priority:** High. All touch targets min 44px. Logo upload zone min 120px tall.

---

## Accessibility

- **Focus order:** Page header → Section 1 inputs (top-to-bottom) → Save → Section 2 → Save → Section 3 → Save
- **Screen reader:** `aria-live="polite"` region for save success/error. Section cards labeled with `aria-labelledby` pointing to card header h2
- **Keyboard navigation:** Full tab support. Color picker swatches navigable with arrow keys. Crop modal traps focus.
- **Color contrast:** All text WCAG AA compliant. Color picker custom input validates contrast ratio and warns if < 3:1
- **Language:** All labels and messages in es-419

---

## Design Tokens

**Colors:**
- Page background: `bg-gray-50`
- Card background: `bg-white`
- Section header text: `text-gray-900 text-lg font-semibold`
- Unsaved indicator: `bg-amber-500` dot

**Typography:**
- Page title: `text-2xl font-bold text-gray-900`
- Card header: `text-lg font-semibold text-gray-900`
- Labels: `text-sm font-medium text-gray-700`

**Spacing:**
- Card gap: `space-y-6`
- Form field gap: `space-y-4`
- Card padding: `p-6`

---

## Implementation Notes

**Dependencies (npm):**
- `react-image-crop` — logo cropping
- `react-hook-form` + `zod` — form validation
- `@tanstack/react-query` — data fetching and mutation

**File Location:**
- Page: `src/app/(dashboard)/settings/clinic/page.tsx`
- Components: `src/components/settings/ClinicInfoForm.tsx`, `src/components/settings/BrandingForm.tsx`, `src/components/settings/RegionalForm.tsx`, `src/components/settings/LogoUpload.tsx`, `src/components/settings/ColorPicker.tsx`

**Hooks Used:**
- `useAuth()` — tenant context and role check
- `useTenantSettings()` — custom hook wrapping TanStack Query for settings fetch
- `useUpdateTenantSettings()` — mutation hook per section

**Form Library:**
- React Hook Form with Zod. Each section is an independent `useForm` instance.

---

## Test Cases

### Happy Path
1. Load settings page
   - **Given:** clinic_owner logged in
   - **When:** navigates to /settings/clinic
   - **Then:** all three sections load with current values pre-filled

2. Save clinic info
   - **Given:** form pre-filled, user changes clinic name
   - **When:** clicks "Guardar" in section 1
   - **Then:** PATCH sent, success toast shown, dirty indicator clears

3. Upload and crop logo
   - **Given:** branding section visible
   - **When:** drags image file, crops, clicks "Aceptar", clicks "Guardar"
   - **Then:** logo uploaded, preview updated in header

### Edge Cases
1. Non-owner role accesses page: all inputs are `disabled`, no Save buttons render
2. Large file (> 2MB) dropped: error message below drop zone, no modal opens
3. Navigate away with dirty form: confirmation dialog appears

### Error Cases
1. API save returns 422: inline field-level errors mapped from response detail
2. Logo upload returns 413: "Archivo demasiado grande" toast error

---

## Acceptance Criteria

- [ ] Matches design spec
- [ ] Three independent sections each save independently
- [ ] Logo upload with crop works on tablet touch
- [ ] Color picker shows live preview
- [ ] Unsaved changes indicator per section
- [ ] Navigate-away confirmation when dirty
- [ ] Role-based read-only for non-owners
- [ ] All inputs validate with Zod + React Hook Form
- [ ] Responsive on all breakpoints
- [ ] Accessibility: focus trap in modals, ARIA labels in Spanish

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
