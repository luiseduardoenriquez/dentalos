# Aprobacion y Firma del Plan de Tratamiento — Frontend Spec

## Overview

**Screen:** Flujo de aprobacion del plan de tratamiento por parte del paciente. Incluye resumen del plan con procedimientos y costo total, requisito legal de scroll hasta el final antes de habilitar la firma, pad de firma digital optimizado para tablet (canvas touch), campos de datos del firmante (nombre y cedula) y confirmacion. Accesible desde la clinica (en persona) y desde el portal del paciente (firma remota).

**Route:** Modal sobre FE-TP-03 (`/patients/{id}/treatment-plans/{plan_id}`) | ruta portal: `/portal/plans/{plan_id}/sign`

**Priority:** High

**Backend Specs:**
- `specs/treatment-plans/TP-08-sign-plan.md`
- `specs/digital-signatures/DS-01-capture-signature.md`

**Dependencies:**
- `specs/frontend/treatment-plans/plan-detail.md` — pantalla de origen en clinica (FE-TP-03)
- `specs/frontend/portal/portal-plan-detail.md` — pantalla de origen en el portal del paciente

---

## User Flow

**Entry Points:**
- Click "Aprobar plan" en FE-TP-03 (flujo en clinica con tablet)
- Link de firma remota enviado al paciente via notificacion (abre `/portal/plans/{id}/sign`)
- Boton "Solicitar aprobacion" que envia el link al paciente (flujo remoto)

**Exit Points:**
- Firma exitosa → muestra documento firmado con PDF preview inline → boton "Cerrar" vuelve a FE-TP-03
- Cancelar → cierra modal sin guardar → plan permanece en estado sin firmar
- Portal: firma exitosa → pagina de confirmacion en el portal

**User Story:**
> As a patient, I want to review my treatment plan details, understand all procedures and costs, scroll through the full document, and sign digitally so that I can formally approve my treatment in a legally valid way.

**Roles with access:**
- En clinica: `clinic_owner`, `doctor` (inician el flujo); el paciente firma en el dispositivo
- Portal: paciente autenticado en el portal (firma remota)

---

## Layout Structure

### Flujo en Clinica (Modal en tablet):

```
+--------------------------------------------------+
|  [X] Aprobacion del Plan de Tratamiento          |
+--------------------------------------------------+
|                                                  |
|  PLAN DE TRATAMIENTO                             |
|  Clinica Dental Los Pinos                        |
|  Paciente: Juan Carlos Perez Lopez               |
|  Doctor: Dr. Andres Lopez   Fecha: 24 Feb 2026  |
|  ------------------------------------------------|
|  PROCEDIMIENTOS:                                 |
|  1. Extraccion de diente 16 (23.09) .....$85.000 |
|  2. Restauracion composite 21 (97.22)...$65.000  |
|  3. Endodoncia diente 36 (70.01).......$200.000  |
|  4. Blanqueamiento general (89.40).....$150.000  |
|  5. Protesis diente 16 (90.02).........$350.000  |
|  ------------------------------------------------|
|  TOTAL ESTIMADO: $850.000                        |
|                                                  |
|  [Texto legal de consentimiento informado...]    |
|  [scroll continuo...]                            |
|  [...hasta el final del documento]              |
|  [       ↓ Desplaza hasta el final              ]|
|  ------------------------------------------------|
|  [Recuadro de firma aun deshabilitado]           |
|  (Llega al final del documento para firmar)      |
|                                                  |
+--------------------------------------------------+
--- Una vez que el usuario llega al final: ---------
+--------------------------------------------------+
|  FIRMA DEL PACIENTE                              |
|                                                  |
|  Nombre completo: [________________________]     |
|  Cedula: [________________________]              |
|                                                  |
|  +------------------------------------------+   |
|  |                                          |   |
|  |   [Area de firma — canvas touch]         |   |
|  |                                          |   |
|  |   "Firma aqui"                           |   |
|  +------------------------------------------+   |
|  [Limpiar firma]                                 |
|                                                  |
|  [! El firmante declara conocer y aceptar...]    |
|                                                  |
|  [Cancelar]            [Firmar y aprobar plan]   |
+--------------------------------------------------+
```

**Sections:**
1. Header modal — titulo y boton cerrar
2. Documento del plan — resumen completo scrolleable con formato de documento legal
3. Indicador de progreso de scroll — "Desplaza hasta el final para firmar" con chevron animado
4. Seccion de firma (deshabilitada hasta scroll completo) — nombre, cedula, pad de firma, aviso legal
5. Footer — Cancelar y Firmar (boton habilitado solo cuando hay firma valida)

---

## UI Components

### Component 1: DocumentoResumen

**Type:** Scrollable document

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.4

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| plan | TratamientoPlan | — | Datos del plan para el documento |
| onScrollComplete | function | — | Callback cuando el usuario llega al final |

**States:**
- Scrolling — usuario leyendo el documento
- Scroll complete — usuario llego al final (dispara `onScrollComplete`)

**Behavior:**
- Area scrolleable con `overflow-y-auto` y `max-h-[45vh]` en tablet
- Escucha el evento `onScroll`: cuando `scrollTop + clientHeight >= scrollHeight - 10px`, se considera "llegado al final"
- Formato de documento: fuente `font-serif`, margenes tipo documento
- Lista numerada de procedimientos con CUPS, diente/zona y costo
- Total en negrita al final
- Texto de consentimiento informado clinico en parrafo
- Indicador visual de "desplaza hasta el final" con icono `ChevronDown` animado al inicio

---

### Component 2: IndicadorScrollRequerido

**Type:** Visual hint / progress

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.9

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| isComplete | boolean | false | Si el scroll llego al final |
| scrollProgress | number | 0 | 0 a 1, progreso del scroll |

**States:**
- Incompleto — barra de progreso + texto "Desplaza hasta el final para poder firmar" + icono animado
- Completo — barra llena en verde + icono checkmark + "Documento revisado"

**Behavior:**
- Barra de progreso horizontal proporcional al scroll (`scrollProgress * 100%`)
- Icono `ChevronDown` animado con `animate-bounce` cuando scroll < 50%
- Al completar: transicion de barra a verde + checkmark sin `animate-bounce`
- La seccion de firma (debajo) tiene `pointer-events-none opacity-50` hasta que `isComplete = true`

---

### Component 3: PadFirmaDigital

**Type:** Signature canvas

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| onSign | (signatureDataUrl: string) => void | — | Callback con la firma en base64 PNG |
| onClear | function | — | Limpia el canvas |
| disabled | boolean | true | Deshabilitado hasta scroll completo |
| width | number | 400 | Ancho del canvas (ajusta segun viewport) |
| height | number | 180 | Alto del canvas |

**States:**
- Disabled — `opacity-50 cursor-not-allowed`, mensaje superpuesto "Llega al final del documento para firmar"
- Vacio (habilitado) — canvas en blanco con borde punteado y texto guia "Firma aqui" en gris
- Con firma — canvas con trazo de firma, borde solido
- Limpiando — breve flash antes de limpiar el canvas

**Behavior:**
- Implementado con `<canvas>` HTML nativo y eventos touch (`touchstart`, `touchmove`, `touchend`)
- Tambien soporta eventos de mouse para firma en desktop
- Trazo suavizado con interpolacion de Bezier para firma fluida
- Al terminar de firmar (`touchend`/`mouseup`): llama a `onSign(canvas.toDataURL('image/png'))`
- Boton "Limpiar firma" bajo el canvas llama a `onClear()` y limpia el canvas
- El canvas se ajusta al DPR del dispositivo (pixel ratio) para alta calidad en tablets con pantallas Retina
- Presion del stylus (si el tablet soporta `PointerEvent.pressure`): varia el grosor del trazo

---

### Component 4: CamposDatosFirmante

**Type:** Form fields

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.7

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| disabled | boolean | true | Deshabilitado hasta scroll completo |
| errors | FieldErrors | {} | Errores de validacion |

**Behavior:**
- Dos campos: nombre completo (texto) y cedula (numerico)
- Se habilitan cuando `scrollComplete = true`
- Transicion de `opacity-50` a `opacity-100` con 200ms ease-out cuando se habilitan
- El nombre puede pre-llenarse con el nombre del paciente (editable si es un representante quien firma)

---

### Component 5: AvisoLegalFirma

**Type:** Legal disclaimer text

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.9

**Behavior:**
- Texto en `text-xs text-gray-500` justo encima del boton de firma
- Texto: "Al firmar, el paciente o representante legal declara haber leido y comprendido el plan de tratamiento, los procedimientos, costos estimados y condiciones de la clinica. La firma tiene validez legal conforme a la ley colombiana."
- No interactivo

---

## Form Fields

| Field | Type | Required | Validation | Error Message | Placeholder |
|-------|------|----------|------------|---------------|-------------|
| firmante_nombre | string | Yes | Min 5 chars, max 120 | "Ingresa el nombre completo del firmante" | "Nombre completo del paciente o representante" |
| firmante_cedula | string | Yes | 6-10 digitos numericos | "Cedula invalida (6 a 10 digitos)" | "Numero de cedula" |
| firma_data | string | Yes | Base64 PNG no vacio, min pixels pintados | "La firma es requerida. Dibuja tu firma en el recuadro." | — |
| scroll_completado | boolean | Yes | Debe ser true | "Debes leer el documento completo antes de firmar" | — |

**Zod Schema:**
```typescript
const firmarPlanSchema = z.object({
  firmante_nombre: z.string()
    .min(5, "Ingresa el nombre completo del firmante")
    .max(120),
  firmante_cedula: z.string()
    .regex(/^\d{6,10}$/, "Cedula invalida (6 a 10 digitos)"),
  firma_data: z.string()
    .min(1, "La firma es requerida. Dibuja tu firma en el recuadro."),
  scroll_completado: z.literal(true, {
    errorMap: () => ({ message: "Debes leer el documento completo antes de firmar" }),
  }),
});
```

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Firmar y aprobar plan | `/api/v1/treatment-plans/{plan_id}/sign` | POST | `specs/treatment-plans/TP-08-sign-plan.md` | None |
| Cargar datos del plan para firma | `/api/v1/treatment-plans/{plan_id}` | GET | `specs/treatment-plans/TP-02-get-plan.md` | 5min |

### Request Body (POST firma):
```json
{
  "firmante_nombre": "Juan Carlos Perez Lopez",
  "firmante_cedula": "12345678",
  "firma_data": "data:image/png;base64,iVBORw0KGgo...",
  "timestamp": "2026-02-24T10:30:00Z",
  "ip_address": null,
  "device_info": "iPad, iOS 18, Safari 18"
}
```

### State Management

**Local State (useState):**
- `scrollComplete: boolean` — si el scroll llego al final
- `scrollProgress: number` — 0 a 1, para la barra de progreso
- `hasSignature: boolean` — si hay trazo en el canvas
- `signatureDataUrl: string | null` — PNG en base64 de la firma
- `isSubmitting: boolean`
- `showSuccessPreview: boolean` — muestra el documento firmado tras exito

**Global State (Zustand):**
- No requiere estado global especifico — contexto de paciente ya disponible

**Server State (TanStack Query):**
- Mutation: `useMutation({ mutationFn: signPlan })`
- `onSuccess`: invalida `['treatment-plan', planId]` → el plan pasa a estado firmado/aprobado

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `already_signed` | 409 | "Este plan ya fue firmado anteriormente" |
| `plan_not_found` | 404 | "Plan de tratamiento no encontrado" |
| `invalid_signature` | 422 | "La firma enviada no es valida. Intenta de nuevo." |
| `plan_cancelled` | 422 | "No se puede firmar un plan cancelado" |
| `forbidden` | 403 | "No tienes permisos para firmar este plan" |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Desplazar documento | Scroll en el area de documento | Actualiza `scrollProgress` | Barra de progreso avanza |
| Llegar al final del doc. | Scroll hasta el final | `scrollComplete = true` | Seccion firma se habilita, barra verde + checkmark |
| Dibujar firma | Touch/mouse en canvas | Trazo registrado en canvas | Trazo visible en tiempo real |
| Limpiar firma | Click "Limpiar firma" | Canvas limpio | Canvas en blanco |
| Firmar y aprobar | Click boton (activo solo con firma y campos llenos) | Valida + POST | Spinner, luego preview del documento firmado |
| Ver documento firmado | Post-exito | Panel de preview del PDF firmado | Slide-in del preview |
| Cerrar tras firma | Click "Cerrar" post-exito | Modal cierra | Plan en FE-TP-03 actualizado a "Firmado" |

### Validacion progresiva del boton "Firmar y aprobar plan":
El boton solo se habilita cuando TODOS se cumplen:
1. `scrollComplete === true`
2. `firmante_nombre.length >= 5`
3. `firmante_cedula` es un numero valido de 6-10 digitos
4. `hasSignature === true` (al menos 50 pixels pintados en el canvas)

### Animations/Transitions

- Barra de progreso de scroll: transicion CSS `width` 100ms easing
- Habilitacion de la seccion de firma: `opacity-50 → opacity-100` 300ms ease-out + `pointer-events-none → auto`
- Checkmark de documento revisado: scale-in 200ms
- Boton "Firmar" habilitandose: transicion de `bg-gray-300` a `bg-blue-600` 200ms
- Preview del documento firmado: slide-in desde la derecha 300ms

---

## Loading & Error States

### Loading State
- Durante submission (POST firma): boton muestra spinner "Enviando firma..." con `Loader2`
- Todos los campos y el canvas se deshabilitan durante la submission
- Loading del documento del plan al abrir el modal: skeleton de las filas de procedimientos

### Error State
- Error de validacion: errores inline bajo cada campo
- Canvas sin firma al intentar enviar: borde rojo en el canvas + mensaje "La firma es requerida"
- Scroll incompleto al intentar enviar (si se bypasea el disabled): error en la parte superior del modal
- Error de API: toast destructivo en top-right + todos los campos vuelven a habilitarse para reintentar

### Empty State
- No aplica — el modal siempre tiene el plan cargado cuando se abre

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Ruta dedicada (no modal). Canvas de firma ocupa el ancho completo de la pantalla (100% - padding). Documento con fuente mas pequena. Botones full-width apilados. |
| Tablet (640-1024px) | Modal full-height (95vh) u optimizado como fullscreen overlay. Canvas de firma 100% del ancho del modal menos padding. Altura del canvas: 180px. Optimizado para stylus/dedo. Layout primario. |
| Desktop (> 1024px) | Modal `max-w-xl` centrado. Canvas de firma 400px x 180px. Layout con documento y firma en scroll continuo. |

**Tablet priority:** CRITICAL — este flujo es el mas importante para tablet. El pad de firma debe ser grande (min 300px x 160px en tablet pequeño, 400px x 180px en tablet grande). El stylus debe funcionar perfectamente con trazo fluido y sin latencia visible. Presion del stylus debe variar el grosor si el dispositivo lo soporta.

---

## Accessibility

- **Focus order:** (Antes de scroll completo) Documento (scroll) → (Al completar scroll) Nombre → Cedula → Canvas de firma → Limpiar firma → Cancelar → Firmar y aprobar
- **Screen reader:** `role="dialog"` con `aria-label="Aprobacion del plan de tratamiento"`. Documento: `role="document"` con `aria-label="Plan de tratamiento completo para revision"`. Canvas: `role="img"` con `aria-label="Pad de firma digital. Dibuja tu firma con el dedo o lapiz."`. Boton firmar: `aria-disabled="true"` cuando no se pueden cumplir las condiciones.
- **Keyboard navigation:** El scroll del documento con teclado (PageDown, Arrow Down) debe contar para el calculo de `scrollProgress`. Canvas no es accesible por teclado — se provee alternativa: opcion de "Ingresar firma como texto" (nombre tipografico como firma) para usuarios con discapacidad motora.
- **Color contrast:** WCAG AA. Texto de aviso legal `text-gray-500` sobre `bg-white` puede no cumplir 4.5:1 — usar `text-gray-600` para garantizar cumplimiento.
- **Language:** es-419. Texto de consentimiento en español juridico colombiano. Mensajes de error en español.

---

## Design Tokens

**Colors:**
- Canvas habilitado: `border-2 border-gray-400`
- Canvas con firma: `border-2 border-blue-500`
- Canvas disabled: `border-2 border-dashed border-gray-200 bg-gray-50`
- Barra progreso scroll (incompleta): `bg-gray-200` / fill `bg-blue-400`
- Barra progreso scroll (completa): fill `bg-green-500`
- Seccion firma disabled: `opacity-50 pointer-events-none`
- Boton "Firmar" disabled: `bg-gray-300 text-gray-500 cursor-not-allowed`
- Boton "Firmar" habilitado: `bg-blue-600 text-white hover:bg-blue-700`
- Documento: `font-serif text-gray-900 leading-relaxed`
- Aviso legal: `text-xs text-gray-600`

**Typography:**
- Titulo del documento: `text-lg font-bold text-center uppercase tracking-wide`
- Nombre clinica en documento: `text-base font-semibold text-center`
- Procedimiento en lista: `text-sm font-mono` (para precio alineado)
- Total: `text-base font-bold`
- Texto consentimiento: `text-sm text-gray-700 leading-relaxed`
- Label firma: `text-sm font-medium text-gray-700`
- Aviso legal: `text-xs text-gray-600 leading-relaxed`

**Spacing:**
- Documento padding interno: `p-6 md:p-8`
- Canvas margin top: `mt-4`
- Gap entre campos firmante: `space-y-3`
- Aviso legal margin: `mt-4`
- Footer: `px-6 py-4 border-t border-gray-200`

**Border Radius:**
- Modal: `rounded-2xl` (desktop/tablet) | none (mobile fullscreen)
- Canvas: `rounded-lg`
- Barra de progreso: `rounded-full h-2`

---

## Implementation Notes

**Dependencies (npm):**
- `react-hook-form` + `zod` + `@hookform/resolvers` — validacion de campos firmante
- `@tanstack/react-query` — mutation de firma
- `lucide-react` — ChevronDown, CheckCircle, RotateCcw, PenLine, Loader2, AlertCircle
- Canvas API nativo — no se requiere libreria externa para el pad de firma
- `framer-motion` — animaciones de habilitacion y preview de documento firmado

**Manejo del canvas:**
```typescript
// Patron recomendado para el pad de firma:
const canvasRef = useRef<HTMLCanvasElement>(null);
const isDrawing = useRef(false);

const startDrawing = (e: TouchEvent | MouseEvent) => {
  isDrawing.current = true;
  const ctx = canvasRef.current?.getContext('2d');
  if (!ctx) return;
  ctx.beginPath();
  const { x, y } = getCoords(e, canvasRef.current!);
  ctx.moveTo(x, y);
};

const draw = (e: TouchEvent | MouseEvent) => {
  if (!isDrawing.current) return;
  const ctx = canvasRef.current?.getContext('2d');
  if (!ctx) return;
  e.preventDefault(); // Previene scroll accidental durante la firma
  const { x, y } = getCoords(e, canvasRef.current!);
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  ctx.strokeStyle = '#1e293b';
  ctx.lineTo(x, y);
  ctx.stroke();
};

const stopDrawing = () => {
  isDrawing.current = false;
  setHasSignature(true);
  const dataUrl = canvasRef.current?.toDataURL('image/png') ?? null;
  onSign(dataUrl);
};
```

**Deteccion de scroll completo:**
```typescript
const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
  const el = e.currentTarget;
  const progress = el.scrollTop / (el.scrollHeight - el.clientHeight);
  setScrollProgress(Math.min(progress, 1));
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 10) {
    setScrollComplete(true);
  }
};
```

**File Location:**
- Modal: `src/components/treatment-plans/PlanApprovalModal.tsx`
- Documento: `src/components/treatment-plans/PlanDocument.tsx`
- Canvas firma: `src/components/treatment-plans/SignaturePad.tsx`
- Indicador progreso: `src/components/treatment-plans/ScrollProgressIndicator.tsx`
- Hook: `src/hooks/useSignPlan.ts`
- Schema: `src/lib/schemas/plan-approval.ts`

**Hooks Used:**
- `useForm()` — React Hook Form para campos firmante
- `useMutation({ mutationFn: signPlan })` — POST de la firma
- `useRef` — canvas y estado de dibujo
- `useState` — scrollProgress, scrollComplete, hasSignature, signatureDataUrl
- `useEffect` — DPR del canvas (pixel ratio para alta resolución)

---

## Test Cases

### Happy Path
1. Firma exitosa en tablet con stylus
   - **Given:** Modal abierto con el plan cargado
   - **When:** Doctor muestra el tablet al paciente, el paciente desplaza el documento hasta el final (barra verde), ingresa nombre y cedula, firma en el canvas con el stylus y hace click "Firmar y aprobar plan"
   - **Then:** POST exitoso, se muestra preview del documento firmado, el plan en FE-TP-03 pasa a estado "Firmado/Aprobado"

2. Firma remota desde portal
   - **Given:** Paciente recibe link de firma por email/WhatsApp
   - **When:** Paciente abre el link en su movil, lee el documento, firma con el dedo, ingresa sus datos y confirma
   - **Then:** Firma registrada, paciente ve mensaje de confirmacion en el portal, el plan en la clinica se actualiza

### Edge Cases
1. Scroll incompleto no habilita la firma
   - **Given:** Documento abierto, usuario ha desplazado el 80% pero no ha llegado al final
   - **When:** La seccion de firma es visible (hace scroll pero el documento del plan es largo)
   - **Then:** Canvas y campos de nombre/cedula permanecen en `opacity-50` y `pointer-events-none`

2. Limpiar y volver a firmar
   - **Given:** Paciente firmo pero quiere hacerlo de nuevo (trazo poco claro)
   - **When:** Hace click "Limpiar firma"
   - **Then:** Canvas se limpia completamente, `hasSignature = false`, boton "Firmar" vuelve a deshabilitarse hasta que se vuelva a firmar

3. Canvas se ajusta a pantalla del dispositivo
   - **Given:** Modal abierto en tablet de 768px de ancho
   - **When:** El canvas se monta
   - **Then:** El canvas tiene `width = containerWidth - 48px` (padding del modal) y DPR aplicado para alta resolucion

4. Firma ya registrada al abrir el modal
   - **Given:** El plan ya fue firmado
   - **When:** Se intenta abrir el modal de aprobacion
   - **Then:** Error 409 manejado: mensaje "Este plan ya fue aprobado anteriormente" + boton "Ver documento firmado"

### Error Cases
1. POST falla durante la firma
   - **Given:** Doctor envia la firma y el servidor retorna error 500
   - **When:** POST falla
   - **Then:** Toast de error "Error al guardar la firma. Intenta de nuevo." Todos los campos y el canvas se rehabilitan. La firma dibujada permanece en el canvas (no se limpia) para no obligar al paciente a firmar de nuevo.

2. Cedula con formato incorrecto
   - **Given:** Campo cedula con "abc123"
   - **When:** Usuario intenta hacer click en "Firmar y aprobar"
   - **Then:** Error inline: "Cedula invalida (6 a 10 digitos)" y el boton permanece deshabilitado

---

## Acceptance Criteria

- [ ] Documento del plan con formato tipo documento legal: lista numerada de procedimientos con CUPS, diente/zona y costo + texto de consentimiento
- [ ] Area scrolleable del documento — scroll completo requerido antes de habilitar la firma
- [ ] Barra de progreso de scroll: proporcional al desplazamiento, verde al completar
- [ ] Texto "Desplaza hasta el final para poder firmar" con icono ChevronDown animado hasta que se complete el scroll
- [ ] Seccion de firma (`opacity-50 pointer-events-none`) hasta que scroll sea completo
- [ ] Campo "Nombre completo del firmante" (min 5 chars, max 120)
- [ ] Campo "Numero de cedula" (6-10 digitos numericos)
- [ ] Canvas de firma touch-optimizado: soporta toque con dedo y stylus
- [ ] Trazo suavizado y sin latencia en tablet
- [ ] Boton "Limpiar firma" que reinicia el canvas
- [ ] Boton "Firmar y aprobar plan" habilitado SOLO cuando: scroll completo + nombre valido + cedula valida + tiene firma en canvas
- [ ] Aviso legal visible sobre el boton de firma
- [ ] POST con: nombre, cedula, firma en base64, timestamp
- [ ] Exito: preview del documento firmado + boton "Cerrar" → plan actualizado en FE-TP-03
- [ ] Error de firma ya registrada (409): mensaje especifico + link a documento
- [ ] Firma NO se limpia del canvas si el POST falla
- [ ] Responsive: fullscreen en mobile, modal optimizado en tablet, modal centrado en desktop
- [ ] Canvas con DPR correcto para pantallas Retina/2x
- [ ] Accesibilidad: role="dialog", aria-label en canvas, boton firmar con aria-disabled correcto
- [ ] Textos en es-419, texto legal en español juridico colombiano

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
