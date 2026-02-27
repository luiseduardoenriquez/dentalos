# Guía de la Recepcionista — DentalOS

**Versión:** 1.0 | **Actualizado:** Febrero 2026 | **Idioma:** es-419

---

## Tabla de contenido

1. [Inicio rápido](#1-inicio-rápido)
2. [Registro de pacientes nuevos](#2-registro-de-pacientes-nuevos)
3. [Búsqueda de pacientes](#3-búsqueda-de-pacientes)
4. [Gestión de citas](#4-gestión-de-citas)
5. [Vista de agenda](#5-vista-de-agenda)
6. [Facturación](#6-facturación)
7. [Cotizaciones](#7-cotizaciones)
8. [Portal de pacientes](#8-portal-de-pacientes)
9. [Notificaciones](#9-notificaciones)
10. [Preguntas frecuentes](#10-preguntas-frecuentes)

---

## 1. Inicio rápido

### Primer ingreso

1. Revise su correo electrónico y busque la invitación de DentalOS.
2. Haga clic en el enlace de la invitación y cree su contraseña.
3. Inicie sesión en [app.dentalos.app](https://app.dentalos.app).

### Panel de recepción

Al ingresar, verá el **Panel de Recepción**, diseñado para manejar la operación diaria sin necesidad de navegar por varios menús:

![Panel de recepción](../assets/panel-recepcion.png)

| Sección | Qué muestra |
|---------|-------------|
| **Citas de hoy** | Lista completa de citas del día con estado (agendada, confirmada, en sala de espera, completada) |
| **Lista de espera** | Pacientes que ya llegaron y están esperando |
| **Acciones rápidas** | Botones: Nuevo Paciente, Agendar Cita, Nueva Factura |
| **Alertas** | Citas sin confirmar, pagos pendientes, consentimientos por firmar |

### Atajo de teclado más útil

Desde cualquier pantalla, presione **Ctrl+K** (o **Cmd+K** en Mac) para abrir la barra de búsqueda rápida. Desde allí puede buscar cualquier paciente o acción sin usar el menú.

---

## 2. Registro de pacientes nuevos

### Iniciar el registro

1. En el panel principal o el menú lateral, haga clic en **Pacientes** → **Nuevo Paciente**.
2. O use el botón **Nuevo Paciente** en los accesos rápidos del panel.

### Formulario de registro

Complete la información del paciente en las siguientes secciones:

#### Datos personales (obligatorios)

| Campo | Descripción |
|-------|-------------|
| **Tipo de documento** | Cédula de ciudadanía, tarjeta de identidad, cédula extranjera, pasaporte |
| **Número de documento** | Solo números, sin puntos ni guiones (ej. `1020304050`) |
| **Primer nombre** | |
| **Segundo nombre** | Opcional |
| **Primer apellido** | |
| **Segundo apellido** | |
| **Fecha de nacimiento** | Formato DD/MM/AAAA |
| **Sexo** | Masculino / Femenino / Otro |

#### Datos de contacto (obligatorios)

| Campo | Descripción |
|-------|-------------|
| **Teléfono celular** | Con indicativo de Colombia: `+57 300 123 4567` |
| **Correo electrónico** | Para notificaciones y acceso al portal |

#### Datos de contacto adicional (opcionales)

| Campo | Descripción |
|-------|-------------|
| **Teléfono fijo** | |
| **Dirección** | Ciudad, barrio, calle |
| **Contacto de emergencia** | Nombre y teléfono |
| **Parentesco** | Relación con el contacto de emergencia |

#### EPS y datos de salud (opcionales)

| Campo | Descripción |
|-------|-------------|
| **EPS** | Entidad Promotora de Salud |
| **Número de afiliación** | |
| **Tipo de afiliado** | Cotizante / Beneficiario |
| **Observaciones** | Cualquier nota relevante para recepción |

### Verificar si el paciente ya existe

Antes de crear un nuevo registro, DentalOS verifica automáticamente si ya existe un paciente con el mismo número de documento. Si encuentra un duplicado, le mostrará una alerta.

### Guardar el registro

1. Revise que toda la información sea correcta.
2. Haga clic en **Guardar Paciente**.
3. El sistema asigna automáticamente un número de historia clínica.
4. Se abre directamente el perfil del paciente recién creado.

### Documentos requeridos para Colombia

Para la historia clínica digital, tenga a mano (se pueden adjuntar más adelante):
- Copia del documento de identidad.
- Carnet de EPS (si aplica).
- Ficha de consentimiento de tratamiento de datos (opcional si el paciente firma en el portal).

---

## 3. Búsqueda de pacientes

### Búsqueda rápida

Use la barra de búsqueda en la parte superior de la pantalla:
- Busque por **nombre**, **apellido**, **número de cédula** o **número de teléfono**.
- Los resultados aparecen en tiempo real mientras escribe.

### Búsqueda avanzada

1. Vaya a **Pacientes** → **Buscar Pacientes**.
2. Use los filtros disponibles:
   - Nombre o apellido.
   - Número de documento.
   - Teléfono.
   - Fecha de nacimiento.
   - EPS.
   - Doctor tratante.
3. Haga clic en **Buscar**.

### Ver el perfil de un paciente

Al encontrar el paciente:
1. Haga clic en su nombre.
2. Se abre el perfil del paciente con sus datos personales y acceso a su historia clínica.
3. Desde el perfil puede: editar datos, agendar una cita, crear una factura o enviar el enlace del portal.

---

## 4. Gestión de citas

### Agendar una cita en 3 pasos

DentalOS está diseñado para que agendar una cita tome máximo 3 clics:

**Paso 1 — Seleccione el paciente:**
1. Haga clic en **Agendar Cita** (en el panel principal o en el perfil del paciente).
2. Busque y seleccione el paciente.

**Paso 2 — Seleccione el doctor, servicio y horario:**
1. Seleccione el **Doctor**.
2. Seleccione el **Procedimiento / Servicio** (la duración se calcula automáticamente).
3. El calendario muestra los horarios disponibles. Haga clic en el horario que prefiera.

**Paso 3 — Confirme:**
1. Revise el resumen de la cita.
2. Haga clic en **Confirmar Cita**.
3. El paciente recibe automáticamente una notificación de recordatorio.

![Agendar cita en 3 pasos](../assets/agendar-cita.png)

### Reprogramar una cita

1. En la agenda, ubique la cita que desea reprogramar.
2. Haga clic en el menú de opciones (**···**) de la cita.
3. Seleccione **Reprogramar**.
4. Elija la nueva fecha y hora en el calendario.
5. Haga clic en **Confirmar Reprogramación**.
6. El paciente recibe una notificación con la nueva fecha.

### Cancelar una cita

1. En la agenda, ubique la cita.
2. Haga clic en **···** → **Cancelar Cita**.
3. Seleccione el motivo de cancelación:
   - Paciente solicitó cancelar.
   - Doctor no disponible.
   - Emergencia.
   - Otro (campo de texto).
4. Haga clic en **Confirmar Cancelación**.

> Las citas canceladas quedan registradas en el historial y no se pueden eliminar.

### Registrar llegada del paciente

Cuando el paciente llega a la clínica:
1. En la agenda, busque la cita del paciente.
2. Haga clic en **···** → **Marcar Llegada**.
3. El paciente pasa a la lista de **En sala de espera** y el doctor recibe una notificación.

---

## 5. Vista de agenda

### Cambiar la vista

Use los botones en la parte superior de la agenda para cambiar la vista:

| Vista | Cuándo usar |
|-------|-------------|
| **Día** | Vista detallada del día actual, hora a hora |
| **Semana** | Planificación semanal, ver disponibilidad general |
| **Doctor** | Ver la agenda de un doctor específico |

### Filtrar por doctor

Si la clínica tiene varios doctores:
1. En la vista de agenda, use el menú desplegable **Doctor**.
2. Seleccione uno o más doctores para ver sus agendas simultáneamente (útil para coordinar).

### Identificar el estado de las citas por color

| Color | Estado |
|-------|--------|
| Gris | Agendada (sin confirmar) |
| Azul | Confirmada |
| Verde | En sala de espera / Siendo atendida |
| Morado | Completada |
| Rojo | Cancelada |

![Vista de agenda semanal](../assets/agenda-semanal.png)

### Imprimir o exportar la agenda

1. En la vista de agenda, haga clic en **Exportar** (esquina superior derecha).
2. Seleccione **Imprimir** para llevar la lista impresa, o **Exportar CSV** para guardar el archivo.

---

## 6. Facturación

### Crear una factura

1. En el menú lateral, seleccione **Facturación** → **Nueva Factura**.
2. Busque y seleccione el paciente.
3. Agregue los servicios prestados:
   - Haga clic en **Agregar Servicio**.
   - Busque el procedimiento del catálogo.
   - Verifique el precio (puede ajustarlo para esta factura si tiene autorización).
   - Repita para cada servicio.
4. Seleccione la **forma de pago**:
   - Efectivo.
   - Tarjeta débito / crédito.
   - Transferencia bancaria.
   - Mixto (varios métodos en la misma factura).
5. Si aplica, agregue un **descuento**.
6. Revise el total.
7. Haga clic en **Emitir Factura**.

> La factura electrónica se envía automáticamente a la DIAN y al correo del paciente (si está configurado el módulo de facturación electrónica).

### Registrar un pago parcial

Si el paciente paga una parte:
1. En **Agregar Pago**, ingrese el monto pagado.
2. Seleccione la forma de pago.
3. El saldo pendiente queda registrado como **Cuenta por cobrar**.

### Ver facturas de un paciente

1. En el perfil del paciente, seleccione la pestaña **Facturación**.
2. Verá todas las facturas con su estado: **Pagada**, **Pendiente**, **Anulada**.

### Anular una factura

1. En la lista de facturas, ubique la factura a anular.
2. Haga clic en el menú de opciones (**···**) → **Anular Factura**.
3. Ingrese el motivo de anulación.
4. Confirme.

> Solo se pueden anular facturas del día en curso o con autorización del propietario. Las facturas electrónicas DIAN se anulan siguiendo el proceso normativo.

---

## 7. Cotizaciones

Las cotizaciones permiten presentar al paciente el costo estimado del tratamiento antes de comenzar.

### Crear una cotización

1. En el menú lateral, seleccione **Facturación** → **Nueva Cotización**.
2. Busque y seleccione el paciente.
3. Agregue los procedimientos del plan de tratamiento:
   - Si el doctor ya creó un plan de tratamiento, haga clic en **Importar desde Plan**.
   - O agregue los procedimientos manualmente con **Agregar Procedimiento**.
4. Ajuste los precios si es necesario.
5. Agregue notas o condiciones (vigencia de la cotización, formas de pago aceptadas).
6. Haga clic en **Guardar Cotización**.

### Enviar la cotización al paciente

1. En la cotización guardada, haga clic en **Enviar al Paciente**.
2. Seleccione el método de envío:
   - **Correo electrónico:** se envía el PDF directamente.
   - **WhatsApp:** se genera un enlace para compartir.
   - **Portal del paciente:** el paciente puede verla en su cuenta.
3. Haga clic en **Enviar**.

### Convertir cotización en factura

Cuando el paciente acepta la cotización y comienza el tratamiento:
1. En la cotización, haga clic en **Convertir en Factura**.
2. Revise los servicios y precios.
3. Emita la factura normalmente.

---

## 8. Portal de pacientes

El portal de pacientes es una plataforma digital donde los pacientes pueden ver sus citas, historial y documentos.

### Cómo guiar al paciente para registrarse

Cuando un paciente quiera acceder al portal por primera vez:

1. En el perfil del paciente, haga clic en **Enviar Acceso al Portal**.
2. El sistema envía al correo del paciente un enlace de registro.
3. Indíquele al paciente que:
   - Revise su correo (incluyendo la carpeta de spam).
   - Haga clic en el enlace para crear su contraseña.
   - Inicie sesión en el portal con su correo y contraseña.

### Enlace directo de la clínica

También puede compartir el enlace del portal de la clínica directamente:
1. En el panel principal, haga clic en **Compartir Portal**.
2. Copie el enlace o muestre el código QR al paciente.
3. El paciente ingresa al portal y busca su registro con su número de cédula.

### Qué puede hacer el paciente en el portal

- Ver sus próximas citas y el historial de citas pasadas.
- Solicitar una nueva cita.
- Ver su historia clínica y odontograma.
- Firmar consentimientos informados.
- Ver cotizaciones y facturas.
- Actualizar sus datos de contacto.

### Si el paciente no recibe el correo de invitación

1. Verifique que el correo esté correctamente registrado en su perfil.
2. En el perfil del paciente, haga clic en **···** → **Reenviar Invitación al Portal**.
3. Si el problema persiste, indíquele al paciente que revise la carpeta de spam o correo no deseado.

---

## 9. Notificaciones

DentalOS envía notificaciones automáticas a los pacientes para reducir el ausentismo. No necesita hacer nada adicional, el sistema lo hace por usted.

### Notificaciones automáticas al paciente

| Momento | Tipo | Mensaje |
|---------|------|---------|
| Al agendar | Correo / WhatsApp | Confirmación de cita con fecha, hora y doctor |
| 48 horas antes | Correo / WhatsApp | Recordatorio de cita |
| 2 horas antes | WhatsApp | Recordatorio final |
| Al cancelar | Correo / WhatsApp | Notificación de cancelación |
| Al reprogramar | Correo / WhatsApp | Nueva fecha y hora |

### Ver el estado de las notificaciones

1. En el menú lateral, seleccione **Notificaciones**.
2. Puede ver si los mensajes fueron enviados y si el paciente los leyó (para correo y WhatsApp Business).

### Enviar un mensaje manual al paciente

Si necesita contactar a un paciente fuera de los recordatorios automáticos:
1. En el perfil del paciente, haga clic en **Enviar Mensaje**.
2. Seleccione el canal: correo o WhatsApp.
3. Seleccione una plantilla de mensaje o escriba uno personalizado.
4. Haga clic en **Enviar**.

### Configurar los canales de notificación

El propietario de la clínica puede activar o desactivar los canales de notificación desde **Configuración** → **Notificaciones**. Consulte con el propietario si necesita ajustar la configuración.

---

## 10. Preguntas frecuentes

**¿Qué hago si el sistema no me deja crear una cita porque el horario está ocupado?**
Revise la vista de agenda para ese doctor y fecha. Si necesita forzar una cita en un horario ocupado (ej. consulta urgente), consulte con el propietario para que habilite esa opción.

**¿Puedo modificar los datos de un paciente ya registrado?**
Sí. En el perfil del paciente, haga clic en **Editar Datos**. Todos los cambios quedan registrados en el historial de auditoría.

**¿Qué hago si el paciente llega y no tiene cita?**
1. Cree una cita en el momento actual (cita de urgencia).
2. Seleccione el tipo de cita como **Urgencia** o **Sin cita previa**.
3. Asigne el doctor disponible.
4. El doctor verá al paciente aparecer en su lista inmediatamente.

**¿Puedo ver el historial clínico del paciente?**
No. Como recepcionista, solo tiene acceso a los datos de contacto, citas y facturación del paciente. Los registros clínicos son exclusivos para el equipo médico.

**¿Cómo anulo un cobro incorrecto?**
Contacte al propietario de la clínica. Solo el propietario puede autorizar la anulación de facturas del día anterior o anteriores.

**¿Qué hago si un paciente quiere cancelar desde el portal?**
Las cancelaciones desde el portal generan una notificación automática a recepción y al doctor. Recibirá una alerta en su panel principal. Si necesita gestionar el slot liberado, agéndelo con otro paciente.

**¿Cómo sé qué citas no han sido confirmadas por el paciente?**
En la agenda, las citas sin confirmar aparecen en color **gris**. En el panel principal también hay un listado de **Citas sin confirmar** en la sección de alertas.

**¿Puedo generar una factura antes de que el doctor registre la evolución?**
Sí. La facturación es independiente del registro clínico. Sin embargo, para reportes de RIPS y cumplimiento, se recomienda que la evolución esté registrada antes de facturar.

**¿Qué hago si el sistema está lento o no carga?**
1. Recargue la página (F5 o Ctrl+R).
2. Verifique la conexión a internet.
3. Si el problema persiste, contacte a soporte: chat en la plataforma o WhatsApp de soporte.

---

*DentalOS — Si no es más rápido que el papel, fallamos.*

*Para sugerencias sobre esta guía: docs@dentalos.app*
