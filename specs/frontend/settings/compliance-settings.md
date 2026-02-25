# Configuración de Cumplimiento — Frontend Spec

## Overview

**Spec ID:** FE-S-07

**Screen:** Compliance settings page — RDA enforcement, RIPS auto-generation, and e-invoicing configuration (Colombia-focused).

**Route:** `/settings/cumplimiento`

**Priority:** High (regulatory deadline April 2026)

**Backend Specs:** `specs/compliance/CO-05.md`, `specs/compliance/CO-08.md`

**Dependencies:** `FE-DS-01`, `FE-DS-02` (button), `FE-DS-03` (input), `FE-DS-10` (card), `FE-DS-11` (badge)

---

## User Flow

**Entry Points:**
- Sidebar: Configuración → Cumplimiento
- Compliance warning banners in clinical forms → "Configurar"

**Exit Points:**
- Any other settings section
- MATIAS API external documentation link

**User Story:**
> As a clinic_owner, I want to configure compliance settings for Colombia's Resolución 1888, RIPS reporting, and DIAN e-invoicing so that my clinic operates legally and avoids regulatory penalties before the April 2026 deadline.

**Roles with access:** `clinic_owner` only. Redirect other roles to dashboard.

---

## Layout Structure

```
+------------------------------------------+
|              Header (h-16)               |
+--------+---------------------------------+
|        |  "Cumplimiento Regulatorio"     |
|        |  Country pill: "🇨🇴 Colombia"    |
| Side-  +---------------------------------+
|  bar   |  [Compliance Score Banner]      |
|        |  [Section 1: RDA]               |
|        |  [Section 2: RIPS]              |
|        |  [Section 3: Facturación DIAN]  |
+--------+---------------------------------+
```

---

## Compliance Score Banner

**Position:** Top of content area, full width.

**Type:** Prominent card with gauge visualization.

**Content:**
```
+----------------------------------------------+
| Nivel de cumplimiento Resolución 1888        |
| [Gauge/donut chart: 68%]                     |
| 68% — Cumplimiento parcial                   |
|                                              |
| Pendiente: 3 requisitos sin configurar       |
| [Ver checklist completo]                     |
+----------------------------------------------+
```

**Gauge component:**
- SVG donut chart, 120px diameter
- Color gradient: 0-49% red, 50-74% amber, 75-89% teal, 90-100% green
- Center text: percentage + icon (X / AlertTriangle / CheckCircle based on level)
- Label below: "Cumplimiento crítico" / "Parcial" / "Bueno" / "Excelente"

**Compliance level labels:**

| Range | Label | Color |
|-------|-------|-------|
| 0-49% | Crítico | `red-600` |
| 50-74% | Parcial | `amber-600` |
| 75-89% | Bueno | `teal-600` |
| 90-100% | Excelente | `green-600` |

**"Ver checklist completo" link:** Expands collapsible section showing full list of requirements:
- [x] NIT registrado
- [x] Zona horaria configurada
- [ ] RIPS habilitado
- [ ] DIAN conectado
- [ ] Campos obligatorios RDA activos
- [ ] Firma digital configurada

---

## Section 1: RDA (Registro Dental Asistencial)

**Card title:** "Campos RDA — Resolución 1888"

**Description:** "La Resolución 1888 de 2021 exige el registro completo de datos clínicos para cada atención. Activa la validación para que los formularios clínicos requieran todos los campos obligatorios."

### Auto-field Enforcement Toggle

**Layout:** Toggle switch row.

```
+----------------------------------------------+
| Validación estricta de campos RDA            |
| Cuando está activo, los registros clínicos   |
| no pueden guardarse sin completar todos los  |
| campos requeridos por la Res. 1888.          |
|                                    [Toggle]  |
+----------------------------------------------+
```

**Toggle ON state:** `bg-teal-600`, knob right.
**Toggle OFF state:** `bg-gray-300`, knob left.

**Impact message (shown when toggling to ON):**
- Amber inline alert: "Al activar esta opción, todos los doctores deberán completar los siguientes campos antes de guardar un registro clínico: diagnóstico CIE-10, código CUPS del procedimiento, motivo de consulta, hallazgos del examen clínico."

**Confirmation modal for toggle ON:**
- Title: "Activar validación estricta RDA"
- Message: "Esta configuración se aplicará de inmediato a todos los usuarios de la clínica. Los registros clínicos incompletos no podrán guardarse. ¿Confirmas?"
- Buttons: "Cancelar" / "Activar"

### Required Fields Reference Table

Collapsible section "Ver campos obligatorios RDA":

| Campo | Sección | Obligatorio Res. 1888 |
|-------|---------|----------------------|
| Motivo de consulta | Historia clínica | Sí |
| Diagnóstico CIE-10 | Diagnóstico | Sí |
| Código CUPS | Procedimiento | Sí |
| Firma del paciente | Consentimiento | Sí |
| Firma del profesional | Registro | Sí |
| Anamnesis | Historia | Sí |
| Examen clínico | Examen | Sí |

---

## Section 2: RIPS (Registro Individual de Prestación de Servicios)

**Card title:** "Generación de RIPS"

**Description:** "RIPS es el reporte mensual de atenciones de salud requerido por el Ministerio de Salud. DentalOS puede generarlo automáticamente al final de cada mes."

### Auto-generation Toggle

```
+----------------------------------------------+
| Generación automática mensual                |
| Genera el archivo RIPS el primer día de      |
| cada mes con los datos del mes anterior.     |
|                                    [Toggle]  |
+----------------------------------------------+
```

### Day of Month Picker

**Visible only when auto-generation is ON.**

```
Generar el día:  [Select: 1 al 28]  de cada mes
```

- Dropdown: numbers 1 through 28 (avoid 29-31 for month compatibility)
- Default: 1 (first day of month)

### RIPS Download History

**Below the toggle settings:**

Table of recent generated RIPS files:

| Período | Generado | Estado | Descargar |
|---------|---------|--------|-----------|
| Enero 2026 | 01 Feb 2026 | Listo | [Download] |
| Diciembre 2025 | 01 Ene 2026 | Listo | [Download] |

**"Generar RIPS ahora" button:** Manual generation trigger (secondary button). Click → confirmation "Se generará el RIPS del período actual. ¿Continuar?" → shows progress → toast "RIPS generado. Descarga disponible."

---

## Section 3: Facturación Electrónica DIAN / MATIAS

**Card title:** "Facturación Electrónica DIAN"

**Description:** "Conecta con MATIAS API (Casa de Software) para emitir facturas electrónicas válidas ante la DIAN conforme al Decreto 2242."

### Connection Status Banner

**States:**

**Disconnected (initial):**
```
+----------------------------------------------+
| ● Desconectado                               |
| La facturación electrónica DIAN no está      |
| configurada.                                 |
| [Conectar con MATIAS]                        |
+----------------------------------------------+
```
- Red dot indicator
- "Conectar con MATIAS" primary button

**Connected:**
```
+----------------------------------------------+
| ● Conectado — MATIAS API                     |
| Facturas enviadas este mes: 47               |
| Último envío: 23 Feb 2026, 14:32             |
| [Desconectar] [Probar conexión]              |
+----------------------------------------------+
```
- Green dot indicator

### Configuration Fields (shown after connecting)

| Field | Type | Required | Validation | Placeholder |
|-------|------|----------|------------|-------------|
| NIT emisor | text | Yes | 9 digits + check | "900.123.456-7" |
| Número de resolución DIAN | text | Yes | Alphanumeric | "18764000001-2019" |
| Rango autorizado desde | number | Yes | Integer | "1" |
| Rango autorizado hasta | number | Yes | Integer > desde | "1000" |
| Prefijo factura | text | No | Max 4 chars | "FE" |

### Test Mode Toggle

```
+----------------------------------------------+
| Modo de prueba (sandbox)                     |
| Las facturas se envían al ambiente de        |
| pruebas DIAN, no tienen validez fiscal.      |
|                                    [Toggle]  |
+----------------------------------------------+
```

**Warning banner when test mode is OFF:** "Modo producción activo. Las facturas emitidas tienen validez fiscal ante la DIAN."

### MATIAS Connection Flow

**"Conectar con MATIAS" button click:**
1. Modal opens: "Configurar MATIAS API"
2. Form fields: API Key (password input), API Secret, Entorno (Sandbox / Producción select)
3. "Verificar conexión" button tests the credentials
4. Success: modal closes, green connected status shows
5. Failure: error message inside modal "Credenciales inválidas. Verifica tu API Key."

**Save:** Separate "Guardar configuración DIAN" button for the NIT/resolution fields.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|-------------|-------|
| Load compliance config | `/api/v1/tenants/{id}/compliance` | GET | `specs/compliance/CO-05.md` | 5min |
| Save RDA enforcement | `/api/v1/tenants/{id}/compliance/rda` | PATCH | `specs/compliance/CO-05.md` | Invalidate |
| Save RIPS config | `/api/v1/tenants/{id}/compliance/rips` | PATCH | `specs/compliance/CO-08.md` | Invalidate |
| Generate RIPS now | `/api/v1/tenants/{id}/rips/generate` | POST | `specs/compliance/CO-08.md` | — |
| Connect MATIAS | `/api/v1/tenants/{id}/integrations/matias` | POST | (integrations backend) | Invalidate |
| Compliance score | `/api/v1/tenants/{id}/compliance/score` | GET | `specs/compliance/CO-05.md` | 10min |

### State Management

**Local State (useState):**
- `rdaEnforcementEnabled: boolean`
- `ripsAutoEnabled: boolean`
- `ripsDay: number`
- `matiasConnectModalOpen: boolean`
- `testModeEnabled: boolean`
- `expandedChecklist: boolean`

---

## Interactions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Toggle RDA enforcement ON | Toggle click | Confirmation modal | Activate if confirmed |
| Toggle RDA enforcement OFF | Toggle click | PATCH immediately | Toast "Validación desactivada" |
| Set RIPS day | Select change | PATCH | Toast "Configuración RIPS guardada" |
| Generate RIPS now | Button click | POST → progress indicator | Toast with download link |
| Connect MATIAS | Button click | Modal opens | — |
| Verify MATIAS credentials | Modal button | POST credentials | Inline success/error in modal |
| Toggle test mode | Toggle | PATCH | Warning banner updates |

---

## Loading & Error States

### Loading State
- Skeleton: compliance score gauge placeholder, 3 section card skeletons

### Error State
- Compliance score load fail: gauge shows "--%" with error message
- RIPS generation fail: error toast "Error al generar RIPS. Verifica los datos del período."

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Gauge smaller (80px). Sections stack. RIPS table scrolls horizontally. |
| Tablet (640-1024px) | Standard layout. |
| Desktop (> 1024px) | Max-w-3xl. |

---

## Accessibility

- **Focus order:** Score banner → checklist toggle → Section 1 → Section 2 → Section 3
- **Screen reader:** Gauge uses `role="meter"` with `aria-valuenow`, `aria-valuemin=0`, `aria-valuemax=100`, `aria-label="Nivel de cumplimiento: 68%"`. Toggles use `role="switch"` with `aria-checked`.
- **Keyboard:** Space activates toggles. Confirmation modals trap focus.
- **Language:** All labels es-419. Regulatory terms in Spanish.

---

## Implementation Notes

**File Location:**
- Page: `src/app/(dashboard)/settings/cumplimiento/page.tsx`
- Components: `src/components/settings/ComplianceScoreGauge.tsx`, `src/components/settings/RdaSection.tsx`, `src/components/settings/RipsSection.tsx`, `src/components/settings/DianSection.tsx`, `src/components/settings/MatiasConnectModal.tsx`

---

## Acceptance Criteria

- [ ] Compliance score gauge renders with correct color coding
- [ ] Checklist expands/collapses
- [ ] RDA toggle requires confirmation before activating
- [ ] RIPS auto-generation toggle shows day picker when ON
- [ ] RIPS download history table shows with download buttons
- [ ] MATIAS connection modal validates credentials before closing
- [ ] DIAN config form saves correctly
- [ ] Test mode toggle shows/hides production warning
- [ ] All sections accessible via keyboard
- [ ] Owner-only access enforced

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec — Colombia Resolución 1888 focus |
