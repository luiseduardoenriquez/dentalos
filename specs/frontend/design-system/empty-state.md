# Empty State — Design System Component Spec

## Overview

**Spec ID:** FE-DS-16

**Component:** `EmptyState`

**File:** `src/components/shared/empty-state.tsx`

**Description:** Contextual empty state component displayed when a list, table, or section has no data. Provides clear communication that no content exists and offers a primary call-to-action to resolve the empty condition. Features dental-themed minimalist SVG illustrations.

**Design System Ref:** `FE-DS-01` (§4.14)

---

## Props Table

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `context` | `EmptyStateContext` | — | No | Pre-defined context (auto-selects illustration + text) |
| `title` | `string` | — | No | Heading text (overrides context default) |
| `description` | `string` | — | No | Body text (overrides context default) |
| `illustration` | `EmptyIllustration \| ReactNode` | Auto from context | No | Illustration key or custom ReactNode |
| `action` | `{ label: string, onClick: () => void }` | — | No | Primary CTA button |
| `secondaryAction` | `{ label: string, onClick: () => void }` | — | No | Secondary CTA (ghost button) |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | No | Component size |
| `className` | `string` | — | No | Additional classes on wrapper |

---

## EmptyStateContext Type

```typescript
type EmptyStateContext =
  | 'no-patients'
  | 'no-appointments'
  | 'no-records'
  | 'no-invoices'
  | 'no-messages'
  | 'no-treatment-plans'
  | 'no-team-members'
  | 'no-consent-templates'
  | 'no-notifications'
  | 'no-search-results'
  | 'no-audit-logs'
  | 'no-prescriptions'
  | 'access-denied'
  | 'error'
  | 'offline'
```

---

## Pre-defined Contexts

| Context | Title | Description | CTA Label | CTA Action (default) |
|---------|-------|-------------|-----------|----------------------|
| `no-patients` | "Sin pacientes aún" | "Registra tu primer paciente para comenzar a gestionar su historial clínico." | "Registrar paciente" | Open patient create form |
| `no-appointments` | "Sin citas programadas" | "Agenda la primera cita del día y mantén tu agenda organizada." | "Agendar cita" | Open appointment create |
| `no-records` | "Sin registros clínicos" | "Los registros de atención del paciente aparecerán aquí." | "Crear registro" | Open clinical record form |
| `no-invoices` | "Sin facturas" | "Las facturas generadas para este paciente se mostrarán aquí." | "Crear factura" | Open invoice form |
| `no-messages` | "Sin mensajes" | "Los mensajes con tu equipo y pacientes aparecerán aquí." | "Enviar mensaje" | Open message compose |
| `no-treatment-plans` | "Sin planes de tratamiento" | "Crea un plan de tratamiento para proponer procedimientos al paciente." | "Crear plan" | Open plan wizard |
| `no-team-members` | "Solo tú en el equipo" | "Invita a doctores, asistentes y recepcionistas para trabajar juntos." | "Invitar miembro" | Open invite modal |
| `no-consent-templates` | "Sin plantillas personalizadas" | "Duplica una plantilla incorporada o crea la tuya desde cero." | "Crear plantilla" | Navigate to template editor |
| `no-notifications` | "Todo al día" | "No tienes notificaciones pendientes. ¡Excelente trabajo!" | — | — |
| `no-search-results` | "Sin resultados" | "No encontramos resultados para tu búsqueda. Intenta con otros términos." | "Limpiar filtros" | Reset filters |
| `no-audit-logs` | "Sin registros para este período" | "No hay actividad registrada para el período y filtros seleccionados." | "Limpiar filtros" | Reset filters |
| `access-denied` | "Sin acceso" | "No tienes permiso para ver este contenido. Contacta al propietario de la clínica." | "Volver al inicio" | Navigate to dashboard |
| `error` | "Algo salió mal" | "Ocurrió un error al cargar los datos. Intenta de nuevo." | "Reintentar" | onRetry callback |
| `offline` | "Sin conexión" | "Verifica tu conexión a internet e intenta de nuevo." | "Reintentar" | onRetry callback |

---

## Sizes

| Size | Max Width | Illustration | Title | Padding |
|------|-----------|-------------|-------|---------|
| `sm` | `max-w-xs` | 120x90px | `text-base` | `py-8` |
| `md` | `max-w-sm` | 160x120px | `text-lg` | `py-12` |
| `lg` | `max-w-md` | 200x150px | `text-xl` | `py-16` |

---

## Visual Structure

```
+------------------------------------------+
|                                          |
|          [SVG Illustration]              |  ← 200x150px (md size)
|                                          |
|         Sin pacientes aún               |  ← text-lg font-semibold text-gray-700
|                                          |
|  Registra tu primer paciente para       |  ← text-sm text-gray-500 max-w-xs
|  comenzar a gestionar su historial      |    text-center mt-2
|  clínico.                               |
|                                          |
|        [Registrar paciente]             |  ← Button primary mt-6
|        [Ver tutorial]                   |  ← Button ghost mt-2 (secondaryAction)
|                                          |
+------------------------------------------+
```

**Container classes:**
```
flex flex-col items-center justify-center text-center
mx-auto
```

---

## Illustrations

SVG illustrations are minimalist line art with the DentalOS teal accent. They are intentionally simple and friendly, not clinical.

All illustrations live at: `src/components/shared/illustrations/`

### Illustration Catalog

**`no-patients`:**
- Two simplified human silhouettes (outline only)
- A tooth outline between them
- Teal accent on tooth

**`no-appointments`:**
- A calendar icon with blank days
- A teal checkmark hint in one cell
- Clock beside calendar

**`no-records`:**
- A clipboard with dotted lines (empty)
- Small tooth at bottom-right corner
- Teal border on clipboard

**`no-invoices`:**
- A document with "$" symbol
- Dotted lines for blank content
- Gray neutral tones, no teal (billing is not clinical)

**`no-messages`:**
- A speech bubble outline (empty inside)
- Small ellipsis "..." inside
- Teal accent on bubble

**`no-treatment-plans`:**
- A flowchart (boxes and arrows) simplified
- Boxes empty, dashed outlines

**`no-team-members`:**
- A single person silhouette (just the primary user)
- Dotted circle to the right (placeholder for new member)

**`no-search-results`:**
- Magnifying glass
- "?" inside the lens
- Gray tones

**`no-notifications`:**
- Bell with a checkmark overlaid
- Teal checkmark
- Bell outline in gray

**`access-denied`:**
- Lock icon with shield
- Red-ish tone (amber actually, not alarming)

**`error`:**
- Triangle with "!" inside
- Amber color

**`offline`:**
- Wi-Fi icon with an X through the waves
- Gray tones

---

## SVG Style Guidelines

All illustrations follow:

1. **Stroke only:** `fill="none"`, `stroke="currentColor"` (inherits `text-gray-300` from wrapper)
2. **Accent elements:** 1-2 elements use `stroke="#0F766E"` (teal-700) for visual interest
3. **Line weight:** `stroke-width="1.5"` for main elements, `stroke-width="1"` for detail
4. **ViewBox:** `0 0 200 150` standard
5. **No text:** Never text inside SVGs (localization)
6. **Rounded caps:** `stroke-linecap="round"`, `stroke-linejoin="round"`

### Sample SVG (no-patients):

```svg
<svg viewBox="0 0 200 150" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Background circle -->
  <circle cx="100" cy="75" r="55" stroke="#E5E7EB" stroke-width="1" stroke-dasharray="4 4"/>
  <!-- Tooth accent -->
  <path d="M85 60 Q100 45 115 60 L118 85 Q108 95 100 90 Q92 95 82 85 Z"
        stroke="#0F766E" stroke-width="1.5" stroke-linecap="round"/>
  <!-- Person left -->
  <circle cx="65" cy="58" r="12" stroke="#D1D5DB" stroke-width="1.5"/>
  <path d="M45 95 Q50 78 65 78 Q80 78 85 95" stroke="#D1D5DB" stroke-width="1.5" stroke-linecap="round"/>
  <!-- Person right -->
  <circle cx="135" cy="58" r="12" stroke="#D1D5DB" stroke-width="1.5"/>
  <path d="M115 95 Q120 78 135 78 Q150 78 155 95" stroke="#D1D5DB" stroke-width="1.5" stroke-linecap="round"/>
</svg>
```

---

## Usage Examples

```tsx
// With pre-defined context
<EmptyState context="no-patients" action={{ label: "Registrar paciente", onClick: openCreateForm }} />

// With custom text (overrides context)
<EmptyState
  context="no-records"
  title="Sin registros de hoy"
  description="Aún no has creado registros clínicos para hoy."
  action={{ label: "Crear registro", onClick: openRecordForm }}
/>

// No CTA (notifications done state)
<EmptyState context="no-notifications" size="sm" />

// Error state with retry
<EmptyState
  context="error"
  action={{ label: "Reintentar", onClick: refetch }}
/>

// Custom illustration (ReactNode)
<EmptyState
  title="Sin historial de facturación"
  description="Tu primera factura aparecerá aquí."
  illustration={<CustomBillingIllustration />}
  size="md"
/>

// Small for panel/sidebar
<EmptyState context="no-messages" size="sm" />

// With secondary action
<EmptyState
  context="no-consent-templates"
  action={{ label: "Crear plantilla", onClick: openEditor }}
  secondaryAction={{ label: "Ver plantillas incorporadas", onClick: scrollToBuiltIn }}
/>
```

---

## Accessibility

- **Role:** Container has `role="status"` when the empty state is replacing a loading/data area, so screen readers announce the empty condition.
- **Illustration:** SVG has `aria-hidden="true"` (decorative). The title text provides the meaningful content.
- **CTA button:** Standard button accessibility (FE-DS-02).
- **Language:** All pre-defined titles and descriptions in Spanish es-419. Custom text should also be in es-419.

---

## Responsive Behavior

- `mx-auto` centers the component in any container
- Illustration scales proportionally on mobile: `max-w-full` on the SVG
- Size `sm` recommended for sidebars and panels
- Size `lg` for full-page empty states (e.g., empty patient list first visit)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial component spec — 14 pre-defined contexts |
