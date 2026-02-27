# Guía del Propietario de Clínica — DentalOS

**Versión:** 1.0 | **Actualizado:** Febrero 2026 | **Idioma:** es-419

---

## Tabla de contenido

1. [Bienvenida y primeros pasos](#1-bienvenida-y-primeros-pasos)
2. [Configuración inicial de la clínica](#2-configuración-inicial-de-la-clínica)
3. [Gestión de usuarios](#3-gestión-de-usuarios)
4. [Roles y permisos](#4-roles-y-permisos)
5. [Configuración de servicios y precios](#5-configuración-de-servicios-y-precios)
6. [Facturación electrónica DIAN](#6-facturación-electrónica-dian)
7. [Reportes y analíticas](#7-reportes-y-analíticas)
8. [Configuración del portal de pacientes](#8-configuración-del-portal-de-pacientes)
9. [Gestión de inventario](#9-gestión-de-inventario)
10. [Soporte y contacto](#10-soporte-y-contacto)

---

## 1. Bienvenida y primeros pasos

Bienvenido a DentalOS. Esta plataforma fue diseñada para que su clínica trabaje más rápido que con papel, sin sacrificar la calidad clínica ni el cumplimiento normativo colombiano.

### Lo que puede hacer como Propietario de Clínica

- Configurar toda la operación de su clínica desde un solo lugar.
- Invitar y administrar a su equipo de trabajo.
- Revisar reportes financieros y de producción clínica.
- Configurar la facturación electrónica con la DIAN.
- Activar el portal de pacientes para comunicación directa.

### Primeros pasos recomendados

Siga este orden para tener su clínica operativa en menos de una hora:

1. Complete la **Configuración inicial de la clínica** (sección 2).
2. Cargue el **catálogo de servicios y precios** (sección 5).
3. **Invite a su equipo** (sección 3).
4. Configure la **facturación electrónica** (sección 6).
5. Active el **portal de pacientes** (sección 8).

---

## 2. Configuración inicial de la clínica

![Panel de configuración de la clínica](../assets/config-clinica-panel.png)

### Acceder a la configuración

1. Inicie sesión en DentalOS con su usuario de propietario.
2. En el menú lateral, seleccione **Configuración** → **Mi Clínica**.

### Información básica

Complete los siguientes campos:

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| Nombre de la clínica | Razón social o nombre comercial | Clínica Dental Sonrisa |
| NIT | Número de Identificación Tributaria | 900.123.456-7 |
| Dirección | Dirección física de la sede | Cra 15 #93-47, Bogotá |
| Teléfono | Número de contacto principal | +57 601 234 5678 |
| Email de contacto | Correo para notificaciones y facturas | info@clinicasonrisa.com |
| Sitio web | Opcional | www.clinicasonrisa.com |

### Carga de logo

1. En la sección **Identidad Visual**, haga clic en **Subir Logo**.
2. Seleccione una imagen en formato **PNG o JPG** (máx. 10 MB, fondo transparente recomendado).
3. El logo aparecerá en facturas, consentimientos y el portal de pacientes.

### Configuración de horarios

1. En **Configuración** → **Mi Clínica** → **Horarios de Atención**:
2. Seleccione los días de apertura haciendo clic en cada día.
3. Defina la hora de apertura y cierre para cada día.
4. Puede configurar horarios especiales (festivos, vacaciones) en **Días Especiales**.
5. Haga clic en **Guardar Horarios**.

> **Nota:** Los horarios determinan los intervalos disponibles para agendar citas. Si su clínica tiene múltiples sedes, cada sede puede tener sus propios horarios.

### Configuración de sede

Si tiene más de una sede, puede agregar sedes adicionales:

1. Vaya a **Configuración** → **Sedes**.
2. Haga clic en **Agregar Sede**.
3. Complete la información de la nueva sede.
4. Asigne los usuarios que trabajan en esa sede.

---

## 3. Gestión de usuarios

![Panel de gestión de usuarios](../assets/gestion-usuarios.png)

### Invitar un nuevo usuario

1. En el menú lateral, seleccione **Configuración** → **Equipo**.
2. Haga clic en **Invitar Usuario**.
3. Ingrese el **correo electrónico** del usuario.
4. Seleccione el **rol** que tendrá (ver sección 4).
5. Si tiene varias sedes, seleccione a cuál sede pertenece.
6. Haga clic en **Enviar Invitación**.

El usuario recibirá un correo con un enlace para crear su cuenta. El enlace expira en **48 horas**.

### Administrar usuarios existentes

Desde la tabla de **Equipo** puede:

- **Ver** el estado de cada usuario (activo / pendiente de aceptar invitación).
- **Cambiar el rol** de un usuario haciendo clic en su nombre → **Editar**.
- **Desactivar** un usuario si ya no trabaja en la clínica (no se elimina, se desactiva por cumplimiento normativo).
- **Reenviar invitación** si el correo no llegó o el enlace expiró.

### Desactivar un usuario

1. En **Equipo**, busque al usuario.
2. Haga clic en el menú de opciones (**···**) al lado del usuario.
3. Seleccione **Desactivar**.
4. Confirme la acción.

> **Importante:** Los usuarios desactivados no pueden iniciar sesión, pero su historial de acciones se conserva por requerimientos legales.

---

## 4. Roles y permisos

DentalOS tiene cuatro roles para el equipo de la clínica. Asigne el rol correcto para proteger la información clínica y financiera.

### Resumen de roles

| Rol | Código | Acceso |
|-----|--------|--------|
| Propietario de Clínica | `clinic_owner` | Acceso total a todas las funciones |
| Doctor | `doctor` | Acceso clínico completo (odontograma, registros, prescripciones) |
| Asistente | `assistant` | Apoyo clínico (sin eliminar registros) |
| Recepcionista | `receptionist` | Agenda, facturación, registro de pacientes |

### Detalle de permisos por rol

#### Propietario de Clínica
- Configuración completa de la clínica.
- Gestión de usuarios (invitar, cambiar roles, desactivar).
- Acceso a todos los reportes y analíticas.
- Configuración de facturación electrónica.
- Acceso a todos los módulos clínicos y administrativos.

#### Doctor
- Odontograma: crear y editar hallazgos clínicos.
- Registros clínicos: evoluciones, notas SOAP, adjuntos.
- Planes de tratamiento: crear, aprobar, seguimiento.
- Prescripciones: generar recetas.
- Consentimientos: crear y solicitar firma.
- Agenda: ver citas propias, confirmar, cancelar.
- **No puede:** ver reportes financieros ni configurar la clínica.

#### Asistente
- Todo lo del rol Doctor, excepto:
  - No puede eliminar registros clínicos.
  - No puede firmar consentimientos como responsable médico.
  - No puede emitir prescripciones.

#### Recepcionista
- Registro y búsqueda de pacientes.
- Gestión completa de la agenda.
- Facturación y cotizaciones.
- Notificaciones y recordatorios.
- **No puede:** acceder a registros clínicos ni prescripciones.

---

## 5. Configuración de servicios y precios

El catálogo de procedimientos es la base de las cotizaciones y facturas de su clínica.

![Catálogo de procedimientos](../assets/catalogo-procedimientos.png)

### Agregar un procedimiento

1. Vaya a **Configuración** → **Catálogo de Servicios**.
2. Haga clic en **Agregar Procedimiento**.
3. Complete los campos:
   - **Nombre:** Nombre del procedimiento (ej. *Resina Clase II*).
   - **Código CUPS:** Código de procedimiento (ej. `891501`). Puede buscar por nombre.
   - **Precio estándar:** Precio en pesos colombianos (COP). Se guarda en centavos internamente.
   - **Duración estimada:** Minutos que dura el procedimiento (para la agenda).
   - **Descripción:** Opcional, se muestra al paciente en cotizaciones.
4. Haga clic en **Guardar**.

### Importar catálogo desde archivo

Si ya tiene una lista de procedimientos en Excel:

1. En **Catálogo de Servicios**, haga clic en **Importar CSV**.
2. Descargue la **Plantilla CSV** para ver el formato requerido.
3. Llene la plantilla con sus procedimientos.
4. Suba el archivo y revise la vista previa.
5. Confirme la importación.

### Editar precios

Los precios pueden actualizarse en cualquier momento:

1. Busque el procedimiento en el catálogo.
2. Haga clic en el nombre del procedimiento.
3. Actualice el **Precio estándar**.
4. Haga clic en **Guardar**.

> Los precios anteriores quedan registrados en el historial. Las cotizaciones y facturas ya emitidas conservan el precio al momento de su creación.

---

## 6. Facturación electrónica DIAN

DentalOS integra facturación electrónica conforme a la normativa DIAN a través del proveedor tecnológico MATIAS (habilitado como Casa de Software).

### Requisitos previos

Antes de configurar, tenga a mano:

- NIT de la clínica (con dígito de verificación).
- Número y fecha de la **Resolución de Facturación** otorgada por la DIAN.
- Rango de folios autorizados (ej. del 1 al 1000).
- Certificado digital de firma electrónica (si ya lo tiene).

### Configurar la resolución de facturación

1. Vaya a **Configuración** → **Facturación Electrónica**.
2. En **Resolución DIAN**, ingrese:
   - Número de resolución.
   - Fecha de emisión de la resolución.
   - Prefijo de la factura (ej. `FE`).
   - Rango de numeración (desde / hasta).
   - Fecha de vigencia de la resolución.
3. Haga clic en **Guardar Resolución**.

### Primer envío de prueba

Antes de facturar en producción, DentalOS le permite hacer un envío de prueba:

1. En **Facturación Electrónica**, haga clic en **Ambiente de Pruebas**.
2. Cree una factura de prueba desde **Facturación** → **Nueva Factura**.
3. Revise el resultado del envío en **Estado DIAN**.
4. Cuando todo esté correcto, cambie a **Ambiente de Producción**.

### Proceso de facturación electrónica

Cuando emita una factura desde DentalOS:

1. El sistema genera el XML conforme a UBL 2.1 (estándar DIAN).
2. El XML se firma electrónicamente.
3. Se envía a la DIAN en tiempo real.
4. El CUFE (Código Único de Factura Electrónica) queda registrado.
5. La factura se envía al correo del paciente en PDF con código QR.

> **Nota:** Si la DIAN no responde, la factura queda en estado **Pendiente** y DentalOS reintenta el envío automáticamente hasta 3 veces.

---

## 7. Reportes y analíticas

![Dashboard de analíticas](../assets/dashboard-analiticas.png)

### Dashboard principal

El dashboard muestra un resumen de la operación de su clínica en tiempo real:

- **Citas hoy:** total agendadas, confirmadas, completadas, canceladas.
- **Ingresos del mes:** facturación total, pagos recibidos, cuentas por cobrar.
- **Pacientes activos:** total de pacientes con actividad en los últimos 30 días.
- **Ocupación de agenda:** porcentaje de slots disponibles vs. ocupados.

### Reportes disponibles

Acceda a reportes detallados en **Analíticas**:

| Reporte | Descripción |
|---------|-------------|
| Producción clínica | Procedimientos realizados por doctor y período |
| Facturación | Ingresos, descuentos, formas de pago |
| Agenda | Tasa de ausentismo, cancelaciones, tiempos de espera |
| Pacientes nuevos | Captación por período y fuente |
| Inventario | Consumo de insumos, alertas de reposición |

### Exportar reportes

1. Seleccione el reporte que desea exportar.
2. Defina el rango de fechas.
3. Haga clic en **Exportar** → **CSV** o **PDF**.

---

## 8. Configuración del portal de pacientes

El portal permite que sus pacientes vean sus citas, historial clínico, cotizaciones y firmen consentimientos desde su celular o computador.

### Activar el portal

1. Vaya a **Configuración** → **Portal de Pacientes**.
2. Haga clic en **Activar Portal**.
3. Personalice:
   - **URL del portal:** se genera automáticamente (ej. `dentalos.app/clinicasonrisa`). Puede personalizar el slug.
   - **Logo y colores:** el portal usa el logo y colores de su clínica.
   - **Mensaje de bienvenida:** texto que ven los pacientes al ingresar.

### Compartir el enlace con pacientes

Una vez activo, puede compartir el enlace del portal de varias formas:

- Copiar el enlace desde **Portal** → **Compartir Enlace**.
- Enviar el enlace por WhatsApp o correo directamente desde el perfil del paciente.
- Imprimir el código QR del portal para exhibirlo en recepción.

### Controlar qué puede ver el paciente

En **Configuración** → **Portal de Pacientes** → **Permisos**:

| Funcionalidad | Activar / Desactivar |
|---------------|----------------------|
| Ver historial clínico | ✓ |
| Ver odontograma | ✓ |
| Solicitar citas | ✓ |
| Ver y firmar consentimientos | ✓ |
| Ver cotizaciones y facturas | ✓ |
| Actualizar datos personales | ✓ |

---

## 9. Gestión de inventario

DentalOS incluye un módulo de inventario con **semáforo visual** para controlar el estado de sus insumos.

![Semáforo de inventario](../assets/inventario-semaforo.png)

### Sistema de semáforo

| Color | Significado | Acción recomendada |
|-------|-------------|-------------------|
| Verde | Stock normal, sin vencer | Sin acción |
| Amarillo | Stock bajo O vence en 90 días | Planear reposición |
| Naranja | Stock crítico O vence en 30 días | Reponer urgente |
| Rojo | Sin stock O vencido | Acción inmediata |

### Agregar un insumo

1. Vaya a **Inventario** → **Insumos**.
2. Haga clic en **Agregar Insumo**.
3. Complete:
   - **Nombre del insumo** (ej. *Resina Nanohíbrida A2*).
   - **Unidad de medida** (unidad, caja, ml, gr).
   - **Stock mínimo:** cantidad que activa la alerta amarilla.
   - **Stock actual:** cantidad disponible hoy.
   - **Fecha de vencimiento:** si aplica.
4. Haga clic en **Guardar**.

### Registrar un ingreso de mercancía

1. En **Inventario** → **Entradas**, haga clic en **Registrar Entrada**.
2. Seleccione el insumo.
3. Ingrese la cantidad recibida y la fecha de vencimiento del lote.
4. Haga clic en **Confirmar Entrada**.

### Alertas automáticas

El sistema envía notificaciones automáticas al propietario de la clínica cuando:
- Un insumo entra en estado **Naranja** (stock crítico o vence en 30 días).
- Un insumo entra en estado **Rojo** (sin stock o vencido).

---

## 10. Soporte y contacto

### Canales de soporte

| Canal | Disponibilidad | Cuándo usar |
|-------|---------------|-------------|
| Chat en la plataforma | Lun–Vie 8am–6pm | Preguntas generales y soporte rápido |
| Correo: soporte@dentalos.app | 24/7 (respuesta en 24h) | Problemas complejos o documentación |
| WhatsApp Business | Lun–Vie 9am–5pm | Urgencias operativas |
| Base de conocimiento | 24/7 | Guías y tutoriales |

### Reportar un problema

Al contactar soporte, incluya:
1. Descripción del problema (qué intentaba hacer y qué pasó).
2. Capturas de pantalla si es posible.
3. Nombre de su clínica y el correo con el que inicia sesión.

### Facturación y planes

Para consultas sobre su plan, cambios de suscripción o facturación de DentalOS:
- Vaya a **Configuración** → **Mi Plan**.
- O escriba a: **facturacion@dentalos.app**.

---

*DentalOS — Si no es más rápido que el papel, fallamos.*

*Para sugerencias sobre esta guía: docs@dentalos.app*
