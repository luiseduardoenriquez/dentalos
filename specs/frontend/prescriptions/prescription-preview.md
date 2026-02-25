# Previsualizacion e Impresion de Receta Medica — Frontend Spec

## Overview

**Screen:** Vista de previsualizacion e impresion de una receta medica formateada como talonario fisico. Replica el formato de una receta impresa: membrete de la clinica, datos del doctor (nombre, especialidad, tarjeta profesional), datos del paciente (nombre, edad, cedula), seccion Rp/ con medicamentos numerados, y pie de pagina con firma y fecha. Incluye boton de impresion y descarga de PDF. Puede usarse como modal de preview desde FE-RX-01 (con datos sin guardar) o como vista de detalle desde FE-RX-02 (receta guardada).

**Route:** Modal sobre FE-RX-01 o FE-RX-02 | Ruta directa para impresion: `/prescriptions/{id}/print`

**Priority:** High

**Backend Specs:** `specs/prescriptions/RX-04-get-prescription-pdf.md`

**Dependencies:**
- `specs/frontend/prescriptions/prescription-create.md` — origen del preview antes de guardar (FE-RX-01)
- `specs/frontend/prescriptions/prescription-list.md` — origen de la vista de detalle guardado (FE-RX-02)

---

## User Flow

**Entry Points:**
- Click "Previsualizar" en FE-RX-01 (con datos del formulario no guardados aun)
- Click en fila de receta en FE-RX-02 (receta ya guardada)
- Boton descarga PDF en FE-RX-02 (abre la misma vista optimizada para impresion)
- Link directo `/prescriptions/{id}/print` desde email o notificacion

**Exit Points:**
- Boton "Imprimir" → dialogo de impresion del navegador con solo el documento de receta (sin chrome del navegador)
- Boton "Descargar PDF" → descarga del PDF generado por el backend
- Boton "Cerrar" o Escape → cierra modal y vuelve a la vista de origen
  - Si vino de FE-RX-01: vuelve al formulario con datos intactos
  - Si vino de FE-RX-02: cierra modal

**User Story:**
> As a doctor, I want to see exactly how the prescription will look when printed so that I can verify all information is correct before handing it to the patient, and then print or download it immediately.

**Roles with access:** `clinic_owner`, `doctor` (crear y ver), `assistant` (solo ver/imprimir), `receptionist` (solo ver/imprimir)

---

## Layout Structure

```
+--------------------------------------------------+
|  [X] Receta Medica           [Imprimir] [PDF]   |
+--------------------------------------------------+
|                                                  |
|  +-----------------------------------------+    |
|  |   CLINICA DENTAL LOS PINOS              |    |
|  |   [Logo]  Calle 90 #15-30, Bogota DC   |    |
|  |           Tel: (601) 234-5678           |    |
|  |   ------------------------------------ |    |
|  |   Dr. Andres Lopez Martinez            |    |
|  |   Odontologia General - Cirugia Oral   |    |
|  |   TP # 12345-67                        |    |
|  |   ------------------------------------ |    |
|  |   Paciente: Juan Carlos Perez Lopez    |    |
|  |   Edad: 42 anos  |  CC: 12.345.678    |    |
|  |   Ciudad: Bogota, 24 de febrero 2026   |    |
|  |   ------------------------------------ |    |
|  |                                         |    |
|  |   Rp/                                   |    |
|  |                                         |    |
|  |   1. Amoxicilina 500mg (Capsulas)       |    |
|  |      Sig: Tomar 1 capsula cada 8 horas  |    |
|  |      Duracion: 7 dias (21 capsulas)     |    |
|  |      Via: Oral                          |    |
|  |      Nota: Tomar con alimentos          |    |
|  |                                         |    |
|  |   2. Ibuprofeno 400mg (Tabletas)        |    |
|  |      Sig: Tomar 1 tableta cada 12 horas |    |
|  |      Duracion: 5 dias (10 tabletas)     |    |
|  |      Via: Oral                          |    |
|  |      Nota: Si hay dolor                 |    |
|  |                                         |    |
|  |   Diagnostico: K02.1 - Caries dental   |    |
|  |                                         |    |
|  |   Notas: Tomar toda la serie aunque..  |    |
|  |                                         |    |
|  |   ------------------------------------ |    |
|  |                                         |    |
|  |   ____________________                  |    |
|  |   Firma del medico                      |    |
|  |   Dr. Andres Lopez - TP # 12345-67     |    |
|  |   Fecha: 24 de febrero de 2026          |    |
|  +-----------------------------------------+    |
|                                                  |
+--------------------------------------------------+
```

**Sections:**
1. Header modal — titulo, boton cerrar, botones de accion (imprimir, descargar PDF)
2. Documento de receta — el talonario completo formateado para impresion:
   a. Membrete de la clinica (logo, nombre, direccion, telefono)
   b. Datos del doctor (nombre, especialidad, tarjeta profesional)
   c. Datos del paciente (nombre, edad, cedula, ciudad, fecha)
   d. Cuerpo Rp/ — lista numerada de medicamentos con sig, duracion, via y notas
   e. Diagnostico vinculado (si aplica)
   f. Notas del medico (si aplica)
   g. Pie de pagina — espacio para firma + datos del doctor + fecha

---

## UI Components

### Component 1: DocumentoReceta

**Type:** Print document

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.4

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| receta | RecetaCompleta \| RecetaFormData | — | Datos de la receta (guardada o del formulario) |
| clinica | ClinicaData | — | Datos de la clinica: nombre, direccion, logo |
| doctor | DoctorData | — | Datos del doctor: nombre, especialidad, TP# |
| paciente | PacienteData | — | Nombre, edad, cedula |
| mode | "preview" \| "print" | "preview" | Modo de renderizado |

**States:**
- Preview (modo normal) — con borde, sombra, contenido completo visible en un area scrolleable
- Print (CSS @media print) — sin borde del modal, sin header/footer del modal, solo el documento

**Behavior:**
- El documento se renderiza como un componente React puro con estilos de CSS
- Para impresion: se usa `window.print()` con CSS `@media print` que oculta todo excepto el documento
- El documento ocupa el 100% de una hoja A4 (210mm x 297mm)
- En modo preview: el documento se muestra con sombra tipo hoja de papel (`shadow-md`) sobre fondo `bg-gray-100`
- Longitud del documento: si hay muchos medicamentos, el documento se extiende a multiples paginas en impresion

---

### Component 2: MembreteClinica

**Type:** Document header

**Design System Ref:** No aplica — este es un componente de documento, no de interfaz

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| clinica | ClinicaData | — | { nombre, direccion, telefono, logoUrl } |

**Behavior:**
- Logo a la izquierda si existe (`<img>`, max 80x60px en el documento)
- Si no hay logo: solo nombre de la clinica en `font-bold text-lg`
- Nombre de la clinica: `text-lg font-bold text-gray-900`
- Direccion y telefono: `text-sm text-gray-600`
- Separador: `border-b border-gray-300 my-3`

---

### Component 3: DatosDoctor

**Type:** Document section

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| doctor | DoctorData | — | { nombre, especialidad, tarjeta_profesional } |

**Behavior:**
- Nombre del doctor: "Dr./Dra. {nombre completo}" en `font-semibold`
- Especialidad(es) en segunda linea: `text-sm text-gray-600`
- Tarjeta profesional: "TP # {numero}" en `text-sm text-gray-600`
- Separador bajo los datos del doctor

---

### Component 4: DatosPaciente

**Type:** Document section

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| paciente | PacienteData | — | { nombre, edad, cedula } |
| ciudad | string | — | Ciudad de la clinica (del tenant) |
| fecha | Date | — | Fecha de la receta |

**Behavior:**
- "Paciente: {nombre completo}"
- "Edad: {N} anos | C.C.: {cedula con puntos de miles}"
- "Ciudad: {ciudad}, {fecha en formato: 24 de febrero de 2026}" — en la misma linea o en la siguiente
- Separador bajo los datos del paciente

---

### Component 5: CuerpoRp

**Type:** Document body

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| medicamentos | Medicamento[] | [] | Lista de medicamentos con todos sus datos |

**Behavior:**
- Encabezado "Rp/" en negrita, ligeramente mas grande
- Lista numerada (1, 2, 3...) de medicamentos
- Por cada medicamento:
  - `1. {Nombre} {dosis_cantidad}{dosis_unidad} ({forma farmaceutica})`
  - `   Sig: Tomar {dosis_cantidad} {unidad} {frecuencia}`
  - `   Duracion: {N} dias ({cantidad_total calculada} unidades)`
  - `   Via: {via}`
  - `   Nota: {instrucciones}` (solo si tiene instrucciones)
- Cantidad total calculada: para frecuencias conocidas (ej: "cada 8h" = 3 por dia → 3 x dias = total)
- Si la frecuencia es libre ("PRN" o texto custom): no se calcula la cantidad total
- Espaciado entre medicamentos: `mb-4`

---

### Component 6: PieDocumento

**Type:** Document footer

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| doctor | DoctorData | — | Datos del doctor para el pie |
| fecha | Date | — | Fecha de la receta |
| firmaImageUrl | string \| null | null | URL de la imagen de firma digital (si existe) |

**Behavior:**
- Espacio para firma: `border-b border-gray-400 w-48` (linea para firma manuscrita si es impresa)
- Si hay firma digital (`firmaImageUrl`): `<img>` de la firma sobre la linea
- Bajo la linea: "Firma del medico"
- "Dr./Dra. {nombre} — TP # {numero}"
- "Fecha: {fecha en formato texto largo}"
- Margenes equivalentes a un pie de pagina de documento

---

### Component 7: AccionesDocumento

**Type:** Action buttons en el header del modal

**Design System Ref:** `frontend/design-system/design-system.md` Section 4.1

**Props/Variants:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| recetaId | string \| null | null | null si es preview de formulario (no guardado aun) |
| onPrint | function | — | Dispara `window.print()` |
| onDownloadPDF | function | — | Descarga el PDF del backend |
| isPDFLoading | boolean | false | Spinner durante generacion de PDF |

**States:**
- Boton "Imprimir" — siempre disponible (usa CSS print, no requiere backend)
- Boton "Descargar PDF" — solo disponible si `recetaId !== null` (receta ya guardada)
- Boton "Descargar PDF" disabled y tooltip si `recetaId === null`: "Guarda la receta primero para descargar el PDF"

---

## Form Fields

No aplica — esta pantalla es solo visualizacion, sin campos de formulario propios.

---

## API Integration

### Endpoints Used

| Action | Endpoint | Method | Backend Spec | Cache |
|--------|----------|--------|--------------|-------|
| Descargar PDF de receta | `/api/v1/prescriptions/{id}/pdf` | GET | `specs/prescriptions/RX-04-get-prescription-pdf.md` | 1h |
| Datos de la receta (si viene de FE-RX-02) | `/api/v1/prescriptions/{id}` | GET | `specs/prescriptions/RX-03-list-prescriptions.md` | 3min |

### State Management

**Local State (useState):**
- `isPDFLoading: boolean` — durante descarga del PDF
- `pdfError: string | null` — error de descarga

**Global State (Zustand):**
- `patientStore.currentPatient` — datos del paciente (nombre, edad, cedula)
- `authStore.user` — datos del doctor prescriptor
- `tenantStore.clinica` — datos de la clinica (nombre, direccion, logo)

**Server State (TanStack Query):**
- Solo en modo "receta guardada" (desde FE-RX-02):
  - Query key: `['prescription', recetaId]`
  - Stale time: 5 minutos (la receta no cambia una vez guardada)
- En modo "preview" (desde FE-RX-01): datos vienen como props del formulario (sin query)

### Error Code Mapping

| Error Code | HTTP Status | UI Message (es-419) |
|------------|-------------|---------------------|
| `prescription_not_found` | 404 | "Receta no encontrada" |
| `pdf_generation_failed` | 500 | "Error al generar el PDF. Intenta de nuevo." |
| `forbidden` | 403 | "No tienes permisos para ver esta receta" |

---

## Interactions

### User Actions

| Action | Trigger | Result | Feedback |
|--------|---------|--------|----------|
| Imprimir | Click "Imprimir" | `window.print()` → dialogo de impresion | Dialogo del navegador |
| Descargar PDF | Click "Descargar PDF" | GET /pdf → descarga del archivo | Spinner en boton durante generacion |
| Cerrar | Click "X" o Escape | Cierra el modal | Vuelve a la vista de origen |

### CSS `@media print`:
```css
@media print {
  /* Ocultar todo excepto el documento */
  body > * { display: none; }
  .prescription-document { display: block !important; }

  /* Estilos de impresion */
  .prescription-document {
    padding: 20mm;
    font-family: 'Times New Roman', serif;
    font-size: 12pt;
    color: #000;
  }

  /* Sin sombras ni bordes en impresion */
  .prescription-document {
    box-shadow: none;
    border: none;
  }

  /* Forzar salto de pagina si hay muchos medicamentos */
  .prescription-document .page-break {
    page-break-before: always;
  }
}
```

### Animations/Transitions

- Modal: slide-up desde bottom en tablet/mobile, fade-in centrado en desktop
- Spinner de PDF: `animate-spin` en `Loader2`
- Ninguna animacion dentro del documento (es un documento estatico)

---

## Loading & Error States

### Loading State (solo cuando modo "receta guardada")
- Skeleton del documento completo: placeholder de membrete + 3 lineas de medicamentos + pie
- Skeleton con `animate-pulse` y colores `bg-gray-200` / `bg-gray-100`

### Error State
- Error al cargar receta: mensaje de error centrado en el modal con boton "Reintentar"
- Error al descargar PDF: toast de error; el documento sigue visible para imprimir manualmente

### Empty State
- No aplica — el modal siempre tiene datos (del formulario o de la receta guardada)

---

## Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| Mobile (< 640px) | Modal full-screen. Documento full-width sin margen lateral. Botones "Imprimir" y "PDF" en barra inferior sticky. Texto del documento reducido a `text-sm`. |
| Tablet (640-1024px) | Modal 90vh con scroll. Documento con margenes interiores de 24px. Botones en el header del modal. Simulacion de hoja de papel con sombra. |
| Desktop (> 1024px) | Modal `max-w-2xl`. Documento centrado con sombra tipo hoja de papel sobre fondo `bg-gray-100`. Botones en el header. |

**Tablet priority:** High — la impresion de recetas se realiza frecuentemente desde tablets clinicas. Botones de imprimir/PDF con altura minima 44px. El documento del modal tiene scroll si es largo. Dialogo de impresion del sistema se activa desde tablet sin problemas.

---

## Accessibility

- **Focus order:** Boton "Imprimir" → Boton "Descargar PDF" → Boton "Cerrar". El documento mismo no tiene elementos interactivos (es solo lectura).
- **Screen reader:** `role="dialog"` con `aria-label="Previsualizacion de receta medica"`. El documento tiene `role="document"` con `aria-label="Receta medica para {nombre paciente}"`. Boton imprimir: `aria-label="Imprimir receta"`. Boton PDF: `aria-label="Descargar PDF de la receta"` con `aria-busy="true"` durante la descarga.
- **Keyboard navigation:** Tab entre los botones de accion. Escape cierra el modal. El documento no es navegable por teclado (es un documento de solo lectura).
- **Color contrast:** WCAG AA. El documento usa texto negro sobre blanco (maximo contraste) por ser un documento para imprimir. Los botones de accion cumplen 4.5:1.
- **Language:** es-419. Todo el contenido del documento en español. Fechas en formato de texto completo en español ("24 de febrero de 2026").

---

## Design Tokens

**Colores (documento — no usar variables de la app, usar valores absolutos para consistencia de impresion):**
- Fondo del documento: `white` / `#ffffff`
- Texto principal: `#111827` (equivalente a `text-gray-900`)
- Texto secundario: `#4b5563` (equivalente a `text-gray-600`)
- Lineas separadoras: `#d1d5db` (equivalente a `border-gray-300`)
- Encabezado "Rp/": `#111827 font-bold`
- Nombre de clinica: `#111827 font-bold text-lg`

**Tipografia del documento (con serif para simular receta medica):**
- Nombre clinica: `font-serif font-bold text-lg`
- Datos del doctor: `font-sans text-sm`
- Cuerpo medicamentos: `font-sans text-sm`
- Encabezado Rp/: `font-serif font-bold text-base`
- Notas: `font-sans text-sm italic`
- Pie: `font-sans text-xs`

**Tipografia del modal (interfaz de la app):**
- Titulo modal: `text-lg font-semibold text-gray-900`
- Botones: `text-sm font-medium`

**Spacing del documento:**
- Padding del documento en preview: `p-8 md:p-10`
- Padding de impresion (CSS): `padding: 20mm`
- Gap entre secciones del documento: `my-4`
- Gap entre medicamentos en Rp/: `mb-5`

**Border Radius:**
- Modal: `rounded-2xl` (desktop/tablet)
- Documento en preview: `rounded-lg shadow-md`

---

## Implementation Notes

**Dependencies (npm):**
- `@tanstack/react-query` — query de datos de la receta (modo guardada)
- `lucide-react` — Printer, Download, X, Loader2, AlertCircle
- `date-fns` + `date-fns/locale/es` — formateo de fechas en español

**Calculo de cantidad total de unidades:**
```typescript
const calcularCantidadTotal = (
  frecuencia: string,
  duracion_dias: number,
  dosis_cantidad: number
): number | null => {
  const mapFrecuenciaADosis: Record<string, number> = {
    "cada 4 horas": 6,
    "cada 6 horas": 4,
    "cada 8 horas": 3,
    "cada 12 horas": 2,
    "cada 24 horas (una vez al dia)": 1,
    "dos veces al dia": 2,
    "tres veces al dia": 3,
    "antes de dormir": 1,
    "antes de las comidas": 3,
    "despues de las comidas": 3,
  };

  const dosisDia = mapFrecuenciaADosis[frecuencia.toLowerCase()];
  if (!dosisDia) return null; // PRN u otras frecuencias no calculables
  return dosisDia * duracion_dias;
};
```

**CSS de impresion global (en globals.css o layout):**
```css
@media print {
  body > div:not([data-prescription-print]) {
    display: none !important;
  }
  [data-prescription-print] {
    display: block !important;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
  }
}
```

**File Location:**
- Modal: `src/components/prescriptions/PrescriptionPreviewModal.tsx`
- Documento: `src/components/prescriptions/PrescriptionDocument.tsx`
- Membrete: `src/components/prescriptions/MembreteClinica.tsx`
- Cuerpo Rp: `src/components/prescriptions/CuerpoRp.tsx`
- Pie: `src/components/prescriptions/PieDocumento.tsx`
- Hook descarga: `src/hooks/useDownloadPrescriptionPDF.ts`
- Utilidad calculo: `src/lib/utils/prescription-calculations.ts`

**Hooks Used:**
- `useQuery(['prescription', recetaId])` — solo en modo "receta guardada"
- `useAuth()` — datos del doctor
- `useTenantStore()` — datos de la clinica
- `usePatientStore()` — datos del paciente
- `useState` — isPDFLoading, pdfError

**Form Library:** No aplica en esta vista.

---

## Test Cases

### Happy Path
1. Preview desde formulario (datos no guardados)
   - **Given:** Doctor llenando FE-RX-01 con 2 medicamentos
   - **When:** Click "Previsualizar" en el formulario
   - **Then:** Modal abre con el documento formateado con los 2 medicamentos, membrete de la clinica, datos del doctor, datos del paciente y fecha de hoy. Boton "Descargar PDF" aparece disabled con tooltip "Guarda la receta primero".

2. Preview de receta guardada con descarga PDF
   - **Given:** Lista FE-RX-02 con una receta existente
   - **When:** Click en la fila de la receta → modal de preview abre
   - **Then:** Documento completo; boton "Descargar PDF" disponible. Click en "Descargar PDF" → spinner → archivo descargado con nombre "receta_Juan_Perez_20260224.pdf"

3. Imprimir receta
   - **Given:** Modal de preview abierto con el documento completo
   - **When:** Click "Imprimir"
   - **Then:** Se abre el dialogo de impresion del sistema; el documento se ve en el preview de impresion sin el chrome del navegador ni el header/footer del modal

4. Calculo correcto de cantidad total
   - **Given:** Amoxicilina 500mg, frecuencia "Cada 8 horas", duracion 7 dias
   - **When:** Se renderiza el medicamento en Cuerpo Rp/
   - **Then:** "Duracion: 7 dias (21 capsulas)" — calculo correcto: 3 dosis/dia x 7 dias = 21

### Edge Cases
1. Medicamento con frecuencia PRN (condicional)
   - **Given:** Ibuprofeno con frecuencia "Solo si hay dolor (PRN)"
   - **When:** Se renderiza el medicamento
   - **Then:** "Duracion: 5 dias" sin "(N capsulas)" — no se calcula cantidad total para PRN

2. Clinica sin logo configurado
   - **Given:** Tenant sin logo cargado
   - **When:** Se renderiza el membrete
   - **Then:** Solo nombre de la clinica en negrita, sin espacio en blanco donde iria el logo

3. Receta con diagnostico vinculado
   - **Given:** Receta vinculada al diagnostico "K02.1 - Caries de la dentina"
   - **When:** Se renderiza el documento
   - **Then:** Seccion "Diagnostico: K02.1 - Caries de la dentina" aparece entre los medicamentos y las notas

4. Receta con muchos medicamentos (5+)
   - **Given:** Receta con 7 medicamentos
   - **When:** Se renderiza en modo preview
   - **Then:** Documento hace scroll; en modo impresion, si no cabe en una hoja, se genera salto de pagina automatico antes del pie de pagina (pie en la ultima hoja)

### Error Cases
1. Error al descargar PDF
   - **Given:** El servidor retorna 500 al intentar generar el PDF
   - **When:** Click "Descargar PDF"
   - **Then:** Spinner desaparece, boton vuelve a normal, toast: "Error al generar el PDF. Intenta de nuevo." El documento sigue visible para imprimir manualmente.

2. Receta no encontrada (acceso directo a /prescriptions/{id}/print)
   - **Given:** URL con ID de receta que no existe o que no pertenece al tenant
   - **When:** Se intenta cargar
   - **Then:** Pagina de error: "Receta no encontrada" con boton "Volver"

---

## Acceptance Criteria

- [ ] Documento formateado como talonario de receta medica con: membrete (logo + nombre clinica + direccion + telefono), datos del doctor (nombre + especialidad + tarjeta profesional), datos del paciente (nombre + edad + cedula + ciudad + fecha), seccion Rp/ con medicamentos numerados, pie de pagina (linea de firma + nombre doctor + fecha)
- [ ] Cuerpo Rp/ por medicamento: nombre + dosis, sig (instruccion), duracion en dias + cantidad total calculada, via, nota (si aplica)
- [ ] Calculo automatico de cantidad total de unidades para frecuencias conocidas
- [ ] Seccion de diagnostico CIE-10 (si aplica) entre los medicamentos y las notas
- [ ] Notas del medico (si aplica) antes del pie de pagina
- [ ] Boton "Imprimir" funciona con `window.print()` y CSS `@media print` que oculta el chrome
- [ ] Boton "Descargar PDF" disponible solo si la receta esta guardada (tiene ID)
- [ ] Boton "Descargar PDF" disabled con tooltip cuando el modal viene del formulario (preview sin guardar)
- [ ] Spinner en boton PDF durante la descarga; toast de error si falla
- [ ] Logo de la clinica en membrete si esta configurado; solo nombre si no hay logo
- [ ] Tipografia serif para el documento (Times New Roman o equivalente)
- [ ] En CSS `@media print`: solo el documento, sin modal, sin navbar, sin header/footer del navegador
- [ ] Skeleton de carga cuando se abre desde FE-RX-02 (receta guardada)
- [ ] Responsive: full-screen mobile, modal 90vh tablet, modal centrado desktop
- [ ] Boton imprimir/PDF con altura minima 44px
- [ ] Accesibilidad: role="dialog", role="document", aria-label descriptivo, aria-busy en boton PDF
- [ ] Textos del documento en es-419 (fechas en texto completo: "24 de febrero de 2026")

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial spec |
