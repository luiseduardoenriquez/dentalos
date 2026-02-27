# Guía del Doctor — DentalOS

**Versión:** 1.0 | **Actualizado:** Febrero 2026 | **Idioma:** es-419

---

## Tabla de contenido

1. [Inicio rápido](#1-inicio-rápido)
2. [Panel principal](#2-panel-principal)
3. [Odontograma](#3-odontograma)
4. [Registro clínico](#4-registro-clínico)
5. [Voz a Odontograma](#5-voz-a-odontograma)
6. [Plan de tratamiento](#6-plan-de-tratamiento)
7. [Prescripciones](#7-prescripciones)
8. [Consentimientos informados](#8-consentimientos-informados)
9. [Historial del paciente](#9-historial-del-paciente)
10. [Agenda](#10-agenda)

---

## 1. Inicio rápido

### Primer ingreso

1. Revise su correo electrónico y busque la invitación de DentalOS.
2. Haga clic en el enlace de la invitación y cree su contraseña.
3. Inicie sesión en [app.dentalos.app](https://app.dentalos.app) con su correo y contraseña.

### Si trabaja en varias clínicas (multi-clínica)

Al iniciar sesión, DentalOS le mostrará el **Selector de Clínica**:

![Selector de clínica](../assets/selector-clinica.png)

1. Seleccione la clínica con la que va a trabajar hoy.
2. Haga clic en **Ingresar**.

> Puede cambiar de clínica en cualquier momento desde el menú superior derecho → icono de clínica → **Cambiar Clínica**. Cada sesión de trabajo queda registrada para la clínica correspondiente.

### Cerrar sesión

- Haga clic en su nombre (esquina superior derecha) → **Cerrar Sesión**.
- Por seguridad, la sesión expira automáticamente después de 15 minutos de inactividad si cierra el navegador.

---

## 2. Panel principal

El panel principal muestra su agenda y actividad clínica del día.

![Panel principal del doctor](../assets/panel-doctor.png)

### Elementos del panel

| Elemento | Descripción |
|----------|-------------|
| **Mis citas de hoy** | Lista de pacientes agendados para el día, con hora y estado |
| **Pacientes en espera** | Pacientes que han llegado a la clínica y esperan ser atendidos |
| **Próxima cita** | Tarjeta destacada con el próximo paciente |
| **Accesos rápidos** | Botones para acciones frecuentes: Nueva Evolución, Buscar Paciente |

### Atender un paciente

1. En **Mis citas de hoy**, haga clic en el nombre del paciente.
2. Se abre la historia clínica del paciente con todas sus secciones.
3. Al finalizar la atención, haga clic en **Marcar como Atendida**.

---

## 3. Odontograma

El odontograma es la representación visual de la boca del paciente. DentalOS ofrece dos vistas: **Clásica** (diagrama esquemático) y **Anatómica** (ilustración 3D en tema oscuro).

### Acceder al odontograma de un paciente

1. Busque al paciente (desde la agenda o la búsqueda superior).
2. En la historia clínica, seleccione la pestaña **Odontograma**.

![Odontograma anatómico](../assets/odontograma-anatomico.png)

### Registrar un hallazgo

1. Haga clic sobre el diente en el diagrama.
2. Se abre el panel lateral del diente.
3. Seleccione el tipo de hallazgo:
   - **Caries** (cara afectada: mesial, distal, oclusal, vestibular, palatino/lingual)
   - **Obturación** existente (material: resina, amalgama, incrustación)
   - **Corona**
   - **Puente** (seleccione dientes pilar y póntico)
   - **Extracción indicada**
   - **Diente ausente**
   - **Fractura**
   - **Endodoncia**
   - **Implante**
   - **Otros** (campo de texto libre)
4. Ingrese notas adicionales si es necesario.
5. Haga clic en **Guardar Hallazgo**.

El hallazgo aparece inmediatamente en el diagrama con el color correspondiente.

### Convención de colores

| Color | Significado |
|-------|-------------|
| Rojo | Caries o lesión activa |
| Azul | Obturación existente |
| Amarillo | Tratamiento indicado |
| Gris | Diente ausente |
| Verde | Implante |
| Morado | Extracción indicada |

### Cambiar entre vista Clásica y Anatómica

- Use el botón **Vista** (esquina superior derecha del odontograma) para alternar entre las dos vistas.
- La vista anatómica usa tema oscuro por defecto para mayor contraste clínico.

### Historial de cambios del odontograma

Cada modificación al odontograma queda registrada con fecha, hora y usuario. Para ver el historial:
1. Haga clic en **Historial** (esquina superior derecha del odontograma).
2. Seleccione una fecha pasada para ver cómo estaba el odontograma en ese momento.

---

## 4. Registro clínico

### Crear una nueva evolución

1. En la historia del paciente, seleccione la pestaña **Registros Clínicos**.
2. Haga clic en **Nueva Evolución**.
3. Seleccione el **procedimiento realizado** del catálogo (busque por nombre o código CUPS).
4. Seleccione el **diente(s) tratado(s)** (se vincula con el odontograma).
5. Complete la nota clínica:

![Editor de evolución clínica](../assets/nueva-evolucion.png)

### Estructura SOAP

DentalOS organiza las notas bajo el formato SOAP:

| Sección | Qué registrar |
|---------|---------------|
| **S — Subjetivo** | Lo que el paciente reporta: dolor, molestias, motivo de consulta |
| **O — Objetivo** | Hallazgos al examen clínico: signos vitales, observaciones |
| **A — Análisis** | Diagnóstico o impresión clínica (puede usar CIE-10) |
| **P — Plan** | Tratamiento realizado y próximos pasos |

### Usar plantillas de evolución

Las plantillas agilizan el registro de procedimientos frecuentes:

1. En el editor de evolución, haga clic en **Usar Plantilla**.
2. Seleccione la plantilla (ej. *Resina compuesta*, *Extracción simple*, *Limpieza*).
3. La plantilla completa automáticamente la estructura SOAP con texto base.
4. Ajuste el contenido según el paciente.
5. Haga clic en **Guardar Evolución**.

> **Tip:** El propietario de la clínica puede crear plantillas personalizadas desde **Configuración** → **Plantillas de Evolución**.

### Adjuntar archivos a la evolución

- Haga clic en **Adjuntar** dentro del editor de evolución.
- Puede subir **radiografías** (DICOM, JPG, PNG), **fotografías clínicas** o **documentos** (PDF).
- Tamaño máximo: 10 MB por imagen, 25 MB por documento.

### Diagnósticos CIE-10

Para agregar un diagnóstico oficial:
1. En la sección **A — Análisis**, haga clic en **Agregar Diagnóstico**.
2. Busque el código CIE-10 por nombre o código (ej. *K02.1 — Caries de la dentina*).
3. Seleccione el diagnóstico y haga clic en **Confirmar**.

---

## 5. Voz a Odontograma

> Esta función está disponible en el plan **Pro** y superiores (add-on **AI Voz**, $10/doctor/mes).

La función de Voz a Odontograma le permite dictar sus hallazgos en lenguaje natural y DentalOS los registra automáticamente en el odontograma del paciente.

### Activar el dictado por voz

1. Abra el odontograma del paciente.
2. Haga clic en el botón **Dictar** (icono de micrófono, esquina superior del odontograma).
3. Conceda permiso de micrófono si el navegador lo solicita.

![Dictado por voz activado](../assets/voz-odontograma-activo.png)

### Cómo dictar

- Hable con claridad a una distancia normal del micrófono.
- Use lenguaje odontológico estándar en español.
- Mencione el diente por su número FDI o su nombre.

**Ejemplos de dictado:**

> "Diente once, caries oclusal, indicar resina."

> "Molar inferior derecho, extracción indicada, diente cuarenta y seis."

> "Trece al veintitrés, puente de cerámica, estado aceptable."

### Revisión antes de guardar

Después de cada dictado:
1. DentalOS muestra una vista previa de los hallazgos interpretados.
2. Revise que los hallazgos sean correctos.
3. Haga clic en **Confirmar y Guardar** si está de acuerdo, o **Editar** para corregir.

> Nunca se guarda automáticamente sin su confirmación. Usted siempre tiene la última palabra.

### Consejos para mejor reconocimiento

- Dicte en un ambiente sin ruido de fondo.
- Si el sistema no interpreta bien un hallazgo, use el teclado para corregirlo.
- Puede combinar dictado y registro manual en la misma sesión.

---

## 6. Plan de tratamiento

El plan de tratamiento organiza todos los procedimientos que el paciente necesita, con su secuencia, costo estimado y seguimiento.

### Crear un plan de tratamiento

1. En la historia del paciente, seleccione la pestaña **Plan de Tratamiento**.
2. Haga clic en **Nuevo Plan**.
3. Asigne un nombre al plan (ej. *Rehabilitación oral completa 2026*).
4. Agregue procedimientos:
   - Haga clic en **Agregar Procedimiento**.
   - Busque el procedimiento en el catálogo.
   - Seleccione el diente y la cara (si aplica).
   - Asigne la prioridad (urgente, alta, media, baja).
5. Reorganice el orden de los procedimientos arrastrando las filas.
6. Haga clic en **Guardar Plan**.

![Plan de tratamiento](../assets/plan-tratamiento.png)

### Generar cotización desde el plan

Una vez creado el plan:
1. Haga clic en **Generar Cotización**.
2. Revise los precios (se toman del catálogo, pero puede ajustarlos para este paciente).
3. Agregue descuentos si aplica.
4. Haga clic en **Enviar al Paciente** para que la vea en el portal, o **Imprimir** para entregar en físico.

### Marcar procedimientos como completados

Conforme avanza el tratamiento:
1. En el plan, ubique el procedimiento completado.
2. Haga clic en el ícono de verificación (**✓**) al lado del procedimiento.
3. Seleccione la fecha de realización.
4. El procedimiento queda marcado como completado y se vincula con la evolución clínica.

### Aprobar el plan

Los planes de tratamiento requieren aprobación del propietario o del mismo doctor:
1. Haga clic en **Aprobar Plan**.
2. Ingrese su contraseña para confirmar (firma digital implícita).
3. El plan queda en estado **Aprobado** y el paciente puede verlo en su portal.

---

## 7. Prescripciones

### Generar una receta médica

1. En la historia del paciente, seleccione la pestaña **Prescripciones**.
2. Haga clic en **Nueva Prescripción**.
3. Agregue los medicamentos:
   - Busque el medicamento por nombre genérico o comercial.
   - Especifique: dosis, frecuencia, duración y vía de administración.
   - Agregue indicaciones especiales si es necesario.
4. Agregue una nota para el paciente (opcional).
5. Haga clic en **Generar Receta**.

![Generador de prescripción](../assets/nueva-prescripcion.png)

### Firmar y emitir la receta

1. Revise la receta en la vista previa.
2. Haga clic en **Firmar y Emitir**.
3. La receta se genera en PDF con:
   - Sus datos profesionales y registro médico.
   - Datos del paciente.
   - Lista de medicamentos.
   - Fecha de emisión.
   - Código de verificación.
4. Puede imprimir la receta o enviarla al correo/WhatsApp del paciente.

---

## 8. Consentimientos informados

Los consentimientos informados son documentos legales que el paciente firma antes de un procedimiento.

### Crear un consentimiento

1. En la historia del paciente, seleccione la pestaña **Consentimientos**.
2. Haga clic en **Nuevo Consentimiento**.
3. Seleccione la plantilla de consentimiento (ej. *Extracción dental*, *Endodoncia*, *Blanqueamiento*).
4. Revise el documento generado.
5. Haga clic en **Solicitar Firma**.

### Firma digital del paciente

El paciente puede firmar de dos maneras:

**Opción A — Firma en pantalla (en la clínica):**
1. Rote la tableta o computador hacia el paciente.
2. El paciente lee el consentimiento en pantalla.
3. El paciente firma directamente en la pantalla con el dedo o un lápiz.
4. Haga clic en **Confirmar Firma**.

**Opción B — Firma desde el portal (remota):**
1. Haga clic en **Enviar al Portal**.
2. El paciente recibe una notificación en su correo/WhatsApp.
3. El paciente firma desde su celular o computador.
4. Usted recibe una notificación cuando el paciente firma.

### Ver consentimientos firmados

En la pestaña **Consentimientos** puede ver todos los consentimientos con su estado:
- **Pendiente:** esperando firma del paciente.
- **Firmado:** firmado digitalmente, con fecha y hora registradas.
- Puede descargar el PDF del consentimiento firmado en cualquier momento.

---

## 9. Historial del paciente

### Navegar la historia clínica

La historia clínica está organizada en pestañas:

| Pestaña | Contenido |
|---------|-----------|
| **Resumen** | Datos personales, alergias, antecedentes médicos |
| **Odontograma** | Diagrama actualizado de la boca |
| **Registros Clínicos** | Todas las evoluciones ordenadas por fecha |
| **Plan de Tratamiento** | Planes activos y completados |
| **Prescripciones** | Recetas emitidas |
| **Consentimientos** | Documentos firmados |
| **Citas** | Historial de citas pasadas y futuras |
| **Adjuntos** | Radiografías, fotografías, documentos |
| **Cotizaciones y Facturas** | Historial financiero del paciente |

### Buscar en el historial

- Use la barra de búsqueda dentro de **Registros Clínicos** para buscar por palabra clave, fecha o procedimiento.
- Filtre por rango de fechas para ver un período específico.

### Antecedentes médicos

Al abrir por primera vez la historia de un paciente, complete:
1. **Antecedentes sistémicos** (diabetes, hipertensión, coagulopatías, etc.).
2. **Alergias** (medicamentos, materiales dentales, látex).
3. **Medicamentos actuales** (que el paciente toma de forma regular).

Esta información aparece destacada en la parte superior de la historia clínica para que nunca pase por alto un antecedente importante.

---

## 10. Agenda

### Ver la agenda del día

1. En el menú lateral, seleccione **Agenda**.
2. La vista por defecto es **diaria**, mostrando solo sus citas.
3. Use los botones de navegación (← →) para cambiar de día.

![Vista de agenda diaria](../assets/agenda-diaria.png)

### Confirmar una cita

1. En la lista de citas, ubique la cita que desea confirmar.
2. Haga clic en el menú de opciones (**···**) de la cita.
3. Seleccione **Confirmar Cita**.
4. El paciente recibe automáticamente una notificación de confirmación por correo o WhatsApp.

### Cancelar una cita

1. En la lista de citas, ubique la cita a cancelar.
2. Haga clic en **···** → **Cancelar Cita**.
3. Seleccione el motivo de cancelación.
4. El sistema notifica automáticamente al paciente.

> **Nota:** Las citas canceladas quedan registradas en el historial. No se eliminan.

### Iniciar atención desde la agenda

Para mayor eficiencia, puede abrir directamente la historia clínica del paciente desde la agenda:
1. Haga clic en el nombre del paciente en la cita.
2. Se abre la historia clínica en una nueva pestaña.
3. Al terminar, marque la cita como **Completada** desde la historia clínica o la agenda.

---

*DentalOS — Si no es más rápido que el papel, fallamos.*

*Para sugerencias sobre esta guía: docs@dentalos.app*
