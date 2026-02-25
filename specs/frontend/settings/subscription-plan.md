# Plan y Suscripción — Frontend Spec

## Overview

**Spec ID:** FE-S-03

**Screen:** Subscription management page showing current plan, usage, plan comparison, add-ons, and billing history.

**Route:** `/settings/plan`

**Priority:** High

**Backend Specs:** `specs/tenants/tenant-usage-stats.md`, `specs/tenants/plan-limits-check.md`

**Dependencies:** `FE-DS-01`, `FE-DS-02` (button), `FE-DS-05` (table), `FE-DS-06` (modal), `FE-DS-10` (card), `FE-DS-11` (badge)

---

## User Flow

**Entry Points:**
- Sidebar: Configuración → Plan
- Plan limit exceeded warning banners throughout app → "Ver plan" CTA
- Onboarding upgrade prompt

**Exit Points:**
- Any other settings section
- External billing portal (Stripe/payment provider)

**User Story:**
> As a clinic_owner, I want to view my current plan, understand usage limits, compare available plans, and manage add-ons so that I can scale the platform as my clinic grows.

**Roles with access:** `clinic_owner` only. Other roles are redirected to dashboard.

---

## Layout Structure

```
+------------------------------------------+
|              Header (h-16)               |
+--------+---------------------------------+
|        |  "Plan y Suscripción"           |
| Side-  +---------------------------------+
|  bar   |  [Current Plan Card]            |
|        |  [Usage Meters]                 |
|        |  [Plan Comparison Table]        |
|        |  [Add-ons Section]              |
|        |  [Billing History Table]        |
+--------+---------------------------------+
```

---

## Section 1: Current Plan Card

**Type:** Card (elevated variant)

**Content layout:**
```
+----------------------------------------------+
| Plan: Starter          [Cambiar plan]         |
| $19 / doctor / mes     Renovación: 15 Mar 2026|
| 1 doctor activo                               |
| Incluye: Pacientes ilimitados, Recordatorios, |
|          Exportación RIPS básico              |
+----------------------------------------------+
```

**Data displayed:**
- Plan name (badge: Free=gray, Starter=blue, Pro=teal, Clínica=purple, Enterprise=amber)
- Price display: formatted as `$[price] / doctor / mes` or `$[price] / sede / mes` for Clínica
- Next renewal date: `dd MMM yyyy` format
- Doctor count active on plan
- Feature highlights (3 bullet points from plan metadata)

**"Cambiar plan" button:** Opens plan comparison section (smooth scroll) or directly opens upgrade modal.

---

## Section 2: Usage Meters

Three progress bar meters displayed in a 3-column grid (1-column on mobile).

### Meter Component

**Props:**
- `label: string` — "Pacientes"
- `current: number` — 45
- `limit: number | null` — 50 (null = unlimited)
- `unit: string` — "pacientes"

**Visual:**
- Label + current/limit text: "45 / 50 pacientes"
- Progress bar (h-3, rounded-full)
- Bar color changes by percentage:
  - 0–74%: `bg-teal-500`
  - 75–89%: `bg-amber-500`
  - 90–100%: `bg-red-500`
- If limit is null (unlimited): "Ilimitado" text + full teal bar

**Meters shown:**
| Metric | Icon | Label |
|--------|------|-------|
| Patients | `Users` | Pacientes |
| Active doctors | `Stethoscope` | Doctores activos |
| Storage | `HardDrive` | Almacenamiento |

**Warning state:** If any meter is at >= 90%, a warning banner appears above meters: "Estás cerca del límite. Considera actualizar tu plan."

---

## Section 3: Plan Comparison Table

**Layout:** Horizontal comparison cards (one card per plan), scrollable horizontally on mobile.

**Plans:** Free | Starter | Pro | Clínica | Enterprise

### Plan Card Structure:

```
+------------------+
| Starter          |  ← plan name badge
| $19              |
| / doctor / mes   |
|                  |
| [feature rows]   |
| ✓ Pacientes      |  ← check icon + label
| ✓ Recordatorios  |
| ✗ Odontograma    |  ← X icon (red), grayed out
|                  |
| [CTA Button]     |
+------------------+
```

**Feature matrix rows (12 features):**

| Feature | Free | Starter | Pro | Clínica |
|---------|------|---------|-----|---------|
| Pacientes ilimitados | 50 | Ilimitado | Ilimitado | Ilimitado |
| Odontograma básico | Si | Si | Si | Si |
| Odontograma anatómico | No | No | Si | Si |
| Registros clínicos | No | Si | Si | Si |
| Planes de tratamiento | No | Si | Si | Si |
| Facturación DIAN | No | No | Si | Si |
| RIPS automático | No | No | Si | Si |
| Sedes múltiples | No | No | No | 3 incl. |
| Portal del paciente | No | No | Si | Si |
| Exportar reportes | No | Si | Si | Si |
| API acceso | No | No | No | Si |
| Soporte prioritario | No | No | Si | Si |

**CTA button per plan:**
- Current plan: "Plan actual" (disabled, outline)
- Lower plan: "Cambiar a [plan]" (secondary) — downgrades require confirmation
- Higher plan: "Actualizar a [plan]" (primary, teal)
- Enterprise: "Contactar ventas" (outline) → opens mailto or Calendly link

**Active plan card:** Highlighted with teal border and "Tu plan" badge at top.

---

## Upgrade Confirmation Modal

**Size:** `md`

**Title:** "Actualizar a Pro"

**Content:**
- Summary of change: current plan → new plan
- Price change: "Tu próxima factura será de $39 / doctor / mes"
- Effective date: "El cambio se aplica al final de tu ciclo actual (15 Mar 2026)"
- Features gained (3 bullet points)

**Footer:** "Cancelar" (secondary) + "Confirmar actualización" (primary)

**Post-confirm:** Redirect to payment provider (Stripe checkout) in new tab, or if already have payment method: immediate confirmation toast "Plan actualizado a Pro. Los cambios estarán activos inmediatamente."

---

## Section 4: Add-ons

**Layout:** Two add-on cards in a 2-column grid (1-column on mobile).

### Add-on Card Structure:

```
+--------------------------------+
| [Icon] AI Voz                  |
| $10 / doctor / mes             |
| Dicta notas y diagnósticos con |
| tu voz. Powered by Whisper AI  |
|                                |
| [Toggle: OFF]  Configurar      |
+--------------------------------+
```

**Add-ons:**

| Add-on | Icon | Price | Description |
|--------|------|-------|-------------|
| AI Voz | `Mic` | $10/doctor/mo | Dictado de notas y odontograma por voz |
| AI Radiografía | `Scan` | $20/doctor/mo | Análisis automático de radiografías |

**Toggle behavior:**
- Toggle ON: opens confirmation modal "Activar AI Voz. Se agregarán $10 por doctor activo a tu factura mensual. ¿Confirmas?"
- Toggle OFF: opens confirmation modal "Desactivar AI Voz. Se eliminará el costo del próximo ciclo de facturación."
- Disabled if plan is Free (tooltip: "Disponible desde el plan Starter")

---

## Section 5: Billing History Table

**Columns:**

| Column | Content | Width |
|--------|---------|-------|
| Fecha | "15 Feb 2026" | 120px |
| Descripción | "Plan Starter — Feb 2026" | flex-1 |
| Monto | "$19.00 USD" | 100px |
| Estado | Badge: Pagada/Pendiente/Fallida | 100px |
| Descarga | PDF icon button | 60px |

**Features:**
- Pagination: 10 per page
- "Descargar PDF" icon button → direct download of invoice PDF from Stripe

**Empty state:** "Sin historial de facturación. Tu primer ciclo de facturación aparecerá aquí."

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Load plan + usage | `/api/v1/tenants/{id}/usage` | GET | `specs/tenants/tenant-usage-stats.md` | 2min |
| Change plan | `/api/v1/tenants/{id}/plan` | PATCH | (billing backend) | Invalidate |
| Toggle add-on | `/api/v1/tenants/{id}/addons` | PATCH | (billing backend) | Invalidate |
| Billing history | `/api/v1/tenants/{id}/invoices` | GET | (billing backend) | 10min |

### State Management

**Local State:**
- `upgradeTarget: PlanType | null`
- `upgradeModalOpen: boolean`
- `addonConfirmTarget: AddonType | null`

**Server State (TanStack Query):**
- Query key: `['tenant-usage', tenantId]`
- Query key: `['tenant-invoices', tenantId, page]`
- Stale time: 2min (usage), 10min (invoices)

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Click "Actualizar a Pro" | Button | Upgrade modal opens | — |
| Confirm upgrade | Modal confirm | PATCH plan / Stripe redirect | Toast or redirect |
| Toggle add-on ON | Toggle switch | Confirmation modal | — |
| Confirm add-on | Modal confirm | PATCH addon | Toast "Add-on activado" |
| Download invoice | PDF icon | Direct download | Browser download |

---

## Loading & Error States

### Loading State
- Skeleton: current plan card skeleton, 3 meter bar skeletons, plan card skeletons, table skeleton

### Error State
- Usage load fail: "No se pudo cargar la información del plan. Intenta de nuevo."
- Plan change fail: "No se pudo actualizar el plan. Contacta soporte." with error code

### Empty State
- Billing history empty: "Sin historial de facturación aún."

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Plan comparison cards scroll horizontally. Add-on cards stack. Usage meters stack vertically. |
| Tablet (640-1024px) | 2-column usage meters. Plan cards 3 across (scroll for more). |
| Desktop (> 1024px) | All 5 plan cards visible. 3-column usage meters. |

---

## Accessibility

- **Focus order:** Current plan → Usage meters → Upgrade CTA → Plan comparison → Add-on toggles → Billing table
- **Screen reader:** Usage meters use `role="progressbar"` with `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-label`
- **Keyboard navigation:** Upgrade modal: Enter confirms, Escape cancels. Toggle switches keyboard-operable.
- **Language:** All labels es-419. Currency in COP/USD as configured.

---

## Implementation Notes

**File Location:**
- Page: `src/app/(dashboard)/settings/plan/page.tsx`
- Components: `src/components/settings/CurrentPlanCard.tsx`, `src/components/settings/UsageMeter.tsx`, `src/components/settings/PlanComparisonTable.tsx`, `src/components/settings/AddonCard.tsx`, `src/components/billing/BillingHistoryTable.tsx`

---

## Acceptance Criteria

- [ ] Current plan displayed correctly with pricing and renewal date
- [ ] Usage meters show correct data with color-coded states
- [ ] Plan comparison table shows all features correctly
- [ ] Upgrade modal shows price change and effective date
- [ ] Add-on toggles require confirmation before activating
- [ ] Billing history table with PDF download
- [ ] Plan limit warnings shown when approaching limits
- [ ] Free plan users see locked features with upgrade prompts
- [ ] Mobile horizontal scroll for plan comparison
- [ ] Accessibility: progress bars with ARIA attributes

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |
