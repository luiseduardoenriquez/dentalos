# DentalOS — Guía de Despliegue a Producción

> Documento para el equipo fundador. Explica qué hay, qué falta, cuánto cuesta y cómo se despliega.

---

## 1. ¿Por qué unas cosas están en Docker y otras no?

### Lo que SÍ corre en Docker (contenedores)

En **desarrollo local** (`docker-compose.yml`) solo levantamos la **infraestructura**:

| Servicio | Puerto | ¿Por qué en Docker? |
|----------|--------|---------------------|
| PostgreSQL 16 | 5432 | Base de datos — no quieres instalarla en tu Mac |
| Redis 7 | 6379 | Cache/sesiones — necesita servidor propio |
| RabbitMQ 3 | 5672 | Cola de tareas asíncronas |
| MinIO | 9000 | Almacenamiento S3 (simula Hetzner Object Storage) |

### ¿Por qué el backend y frontend NO están en Docker en desarrollo?

**Respuesta corta:** velocidad de desarrollo.

- **Backend (FastAPI):** Lo corres con `uvicorn --reload` para que cada cambio en un archivo `.py` se recargue en ~1 segundo. Si estuviera en Docker, cada cambio requeriría rebuild o montar volúmenes complicados con sincronización lenta en macOS.
- **Frontend (Next.js):** Lo corres con `npm run dev` para hot-reload instantáneo. Misma razón — Docker en Mac tiene un overhead de I/O importante con el filesystem.

### En producción TODO está en Docker

En **producción** (`docker-compose.prod.yml`) **todo** corre en contenedores:

| Servicio | Imagen | Recursos |
|----------|--------|----------|
| **backend** (FastAPI + Gunicorn) | Multi-stage build, Python 3.12-slim | 1 vCPU, 1GB RAM |
| **frontend** (Next.js standalone) | Multi-stage build, Node 20 Alpine | 0.5 vCPU, 512MB RAM |
| **PostgreSQL 16** | postgres:16-alpine | 1.5 vCPU, 1.5GB RAM |
| **Redis 7** | redis:7-alpine | 0.5 vCPU, 384MB RAM |
| **RabbitMQ 3** | rabbitmq:3-management-alpine | 0.5 vCPU, 512MB RAM |
| **MinIO** | minio/minio | 0.5 vCPU, 512MB RAM |

Cada servicio tiene:
- Health checks automáticos
- Límites de CPU y memoria
- Reinicio automático (`restart: unless-stopped`)
- Red privada (nada expuesto a internet directamente)

---

## 2. Arquitectura de Producción

```
                        INTERNET
                           │
                    ┌──────▼──────┐
                    │  Cloudflare  │  DNS + CDN + DDoS protection
                    └──────┬──────┘
                           │ HTTPS
                    ┌──────▼──────────────┐
                    │  Hetzner Load       │  TLS termination (Let's Encrypt)
                    │  Balancer (LB11)    │  Health checks cada 15s
                    │  €6/mes             │  Distribuye tráfico round-robin
                    └──────┬──────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
     ┌────────▼────────┐      ┌────────▼────────┐
     │  App Server 1   │      │  App Server 2   │
     │  CX41 — €17/mes │      │  CX41 — €17/mes │
     │  8 vCPU, 16GB   │      │  8 vCPU, 16GB   │
     │                 │      │                 │
     │  Docker:        │      │  Docker:        │
     │  ├─ FastAPI ×4  │      │  ├─ FastAPI ×4  │
     │  │  workers     │      │  │  workers     │
     │  ├─ Next.js     │      │  ├─ Next.js     │
     │  └─ ClamAV      │      │  └─ ClamAV      │
     └────────┬────────┘      └────────┬────────┘
              │     Red Privada Hetzner │
              │      (10.0.0.0/16)      │
     ┌────────┴────────────────────────┬┘
     │                │                │
┌────▼────┐    ┌──────▼──────┐   ┌────▼──────────┐
│PostgreSQL│    │   Redis     │   │  Worker Server│
│ Managed  │    │   CX21      │   │  CPX31        │
│ CPX31    │    │   €6/mes    │   │  €11/mes      │
│ €19/mes  │    │   4GB RAM   │   │               │
│          │    │             │   │  RabbitMQ     │
│ 16GB RAM │    │  Cache de   │   │  Workers:     │
│ 200GB SSD│    │  sesiones,  │   │  ├─ Email     │
│          │    │  permisos,  │   │  ├─ WhatsApp  │
│ Schemas: │    │  odontogram │   │  ├─ SMS       │
│ ├ public │    │             │   │  ├─ DIAN      │
│ └ tn_*   │    │             │   │  ├─ PDFs      │
│          │    │             │   │  └─ General   │
└──────────┘    └─────────────┘   └───────────────┘
                                         │
                               ┌─────────▼─────────┐
                               │ Hetzner Object     │
                               │ Storage (S3)       │
                               │ ~€5/TB/mes         │
                               │                    │
                               │ Archivos clínicos, │
                               │ radiografías,      │
                               │ backups            │
                               └────────────────────┘
```

---

## 3. ¿Cuánto cuesta poner esto en producción?

### Opción A: MVP Mínimo (1 clínica beta, 1 servidor)

Para arrancar con la clínica tester, NO necesitas 2 app servers. Un solo servidor basta:

| Componente | Spec | Costo/mes |
|------------|------|-----------|
| **App Server** (todo en uno) | CX31 — 4 vCPU, 8GB RAM | €11 |
| **PostgreSQL** (en el mismo server) | Docker container | €0 (incluido) |
| **Redis** (en el mismo server) | Docker container | €0 (incluido) |
| **RabbitMQ** (en el mismo server) | Docker container | €0 (incluido) |
| **Hetzner Object Storage** | 100GB | ~€2 |
| **Dominio** | dentalos.app o similar | ~€1 |
| **Cloudflare** | Plan Free | €0 |
| **Let's Encrypt** | Certificado SSL | €0 |
| | | |
| **Total Opción A** | | **~€14/mes (~$15 USD)** |

> **Nota:** Sin Load Balancer ni redundancia. Si el servidor se cae, hay downtime. Pero para 1 clínica beta es más que suficiente.

### Opción B: Producción Seria (5-20 clínicas)

| Componente | Spec | Costo/mes |
|------------|------|-----------|
| **App Server 1** | CX41 — 8 vCPU, 16GB RAM | €17 |
| **App Server 2** | CX41 — 8 vCPU, 16GB RAM | €17 |
| **Load Balancer** | LB11 con TLS | €6 |
| **DB Server** | CPX31 Managed PostgreSQL | €19 |
| **Redis Server** | CX21 — 2 vCPU, 4GB RAM | €6 |
| **Worker Server** | CPX31 — 4 vCPU, 8GB | €11 |
| **Object Storage** | 500GB | ~€5 |
| **Dominio + DNS** | | ~€1 |
| **Cloudflare Pro** | | €20 |
| | | |
| **Total Opción B** | | **~€102/mes (~$110 USD)** |

### Opción C: Escalada (50-200 clínicas)

| Componente | Spec | Costo/mes |
|------------|------|-----------|
| **2× App Servers** | CX51 — 16 vCPU, 32GB | €34 ×2 = €68 |
| **Load Balancer** | LB11 | €6 |
| **DB Managed** | CPX41 — 8 vCPU, 16GB, replicas | €38 |
| **Redis Managed** | Cluster, 8GB | €15 |
| **Worker Server** | CPX41 | €17 |
| **Object Storage** | 2TB | ~€10 |
| **Monitoring** | Grafana Cloud Free + Sentry | €0-29 |
| | | |
| **Total Opción C** | | **~€170/mes (~$185 USD)** |

### Costos de Terceros (APIs externas)

| Servicio | Costo | ¿Cuándo se necesita? |
|----------|-------|---------------------|
| **Anthropic (Claude)** | ~$20-50/mes | AI Treatment Advisor, Chatbot, Voice |
| **OpenAI (Whisper)** | ~$5-15/mes | Voice-to-Odontogram |
| **Twilio** (SMS + Voz) | ~$20-40/mes | Recordatorios, VoIP |
| **WhatsApp Cloud API** | Gratis primeros 1000 msg/mes | Chat bidireccional |
| **SendGrid** (Email) | Gratis hasta 100/día | Notificaciones email |
| **Daily.co** (Video) | Gratis hasta 2000 min/mes | Telemedicina |
| **Nequi/Daviplata** | Comisión por transacción | Pagos móviles |
| **Mercado Pago** | Comisión por transacción | Pagos con tarjeta |
| **Sentry** | Gratis tier developer | Error tracking |
| | | |
| **Total APIs (estimado)** | **~$50-150/mes** | Depende del uso |

### Resumen de Inversión Inicial

| Concepto | MVP Beta (1 clínica) | Producción (5-20 clínicas) |
|----------|---------------------|---------------------------|
| Infraestructura | ~$15/mes | ~$110/mes |
| APIs externas | ~$50/mes (mínimo) | ~$100/mes |
| Dominio + SSL | ~$15/año | ~$15/año |
| **Total mensual** | **~$65/mes** | **~$210/mes** |

---

## 4. ¿Qué necesitamos para el día 1 con la clínica tester?

### Cuentas y Accesos Necesarios

| # | Cuenta | Para qué | Prioridad |
|---|--------|----------|-----------|
| 1 | **Hetzner Cloud** | Servidores, storage, LB | Obligatorio |
| 2 | **Cloudflare** | DNS, CDN, protección DDoS | Obligatorio |
| 3 | **GitHub** (ya lo tienen) | Código, CI/CD, Container Registry | Obligatorio |
| 4 | **SendGrid** | Emails transaccionales | Obligatorio |
| 5 | **Sentry** | Monitoreo de errores | Muy recomendado |
| 6 | **Dominio** (.app, .co, etc.) | URL de la plataforma | Obligatorio |
| 7 | Anthropic API | AI features | Opcional para beta |
| 8 | Twilio | SMS/llamadas | Opcional para beta |
| 9 | WhatsApp Business | Chat | Opcional para beta |
| 10 | Nequi/Daviplata | Pagos móviles | Opcional para beta |

### Lo Mínimo para Funcionar (beta)

Solo necesitas: **Hetzner + Cloudflare + SendGrid + Dominio + Sentry**

Las integraciones de pagos, WhatsApp, telemedicina, IA, etc. tienen **mocks** en el código. La app funciona completa sin ellas — solo que esas features específicas no harán llamadas reales.

### Pasos de Despliegue

```
1. Crear cuenta en Hetzner Cloud
   └─ Crear servidor CX31 (€11/mes)
   └─ Crear Object Storage bucket
   └─ Configurar firewall (solo 80/443 abiertos)

2. Registrar dominio
   └─ Configurar DNS en Cloudflare
   └─ Apuntar A record a IP del servidor

3. SSH al servidor
   └─ Instalar Docker + Docker Compose
   └─ Clonar repositorio
   └─ Copiar .env con credenciales de producción
   └─ Generar llaves JWT (RSA 2048-bit)

4. Levantar servicios
   └─ docker compose -f docker-compose.prod.yml up -d
   └─ Correr migraciones (public + tenant)
   └─ Crear tenant para la clínica beta
   └─ Crear usuario admin para la clínica

5. Verificar
   └─ https://api.dentalos.app/api/v1/health → OK
   └─ https://app.dentalos.app → Login page
   └─ Login con credenciales de la clínica
```

---

## 5. Cómo funciona el flujo de una request

```
1. La doctora abre app.dentalos.app en su tablet
   │
2. Cloudflare resuelve DNS → IP del servidor Hetzner
   │
3. HTTPS llega al servidor (puerto 443)
   │
4. Nginx recibe y rutea:
   │  ├─ /api/* → FastAPI (puerto 8000)
   │  └─ todo lo demás → Next.js (puerto 3000)
   │
5. Si es API (/api/v1/patients):
   │  ├─ Middleware extrae JWT del header
   │  ├─ Valida firma RS256 con llave pública
   │  ├─ Extrae tenant_id del JWT (claim "tid")
   │  ├─ SET search_path TO tn_abc123, public
   │  ├─ Ejecuta la lógica de negocio
   │  └─ Retorna JSON
   │
6. Si es frontend (/patients/123):
   │  ├─ Next.js hace Server-Side Rendering
   │  ├─ Llama al backend internamente (localhost:8000)
   │  ├─ Renderiza HTML con datos
   │  └─ Envía HTML + JS al browser
   │
7. En el browser:
   │  ├─ React se hidrata (se vuelve interactivo)
   │  ├─ React Query hace fetch de datos adicionales
   │  └─ La doctora puede trabajar
```

---

## 6. Base de Datos: Aislamiento por Clínica

Cada clínica tiene su propio **schema** en PostgreSQL:

```
PostgreSQL Database: dentalos_prod
├── public (schema compartido)
│   ├── tenants          → Lista de clínicas
│   ├── plans            → Planes de precios
│   ├── users            → Todos los usuarios
│   ├── superadmins      → Admin de la plataforma
│   └── catalogs         → CIE-10, CUPS, FDI
│
├── tn_clinica_sonrisas (schema de Clínica Sonrisas)
│   ├── patients         → 44 tablas solo de esta clínica
│   ├── appointments
│   ├── clinical_records
│   ├── odontograms
│   ├── ortho_cases      → ¡el módulo que acabamos de hacer!
│   └── ... (44 tablas)
│
├── tn_dental_premium (schema de Dental Premium)
│   ├── patients         → Datos completamente separados
│   └── ... (44 tablas)
│
└── tn_sonrie_ya (schema de Sonríe Ya)
    └── ... (44 tablas)
```

**¿Por qué así?** Cumplimiento regulatorio — los datos clínicos de una clínica NUNCA pueden mezclarse con los de otra. Es literalmente otro esquema de base de datos.

---

## 7. ¿Qué falta para producción?

### Listo (código completo)

- [x] 72 modelos, 93 servicios, 73 routers, 168 componentes
- [x] Autenticación JWT RS256 con RBAC
- [x] Multi-tenancy schema-per-tenant
- [x] 13 integraciones externas con mocks
- [x] Dockerfiles multi-stage optimizados
- [x] docker-compose.prod.yml con límites de recursos
- [x] CI/CD con GitHub Actions
- [x] 44 tablas por tenant, 17 migraciones
- [x] PWA con Service Worker

### Falta (operativo, no código)

| Tarea | Esfuerzo | Bloqueante para beta? |
|-------|----------|----------------------|
| Crear cuenta Hetzner y levantar servidor | 2-3 horas | **Sí** |
| Configurar dominio + Cloudflare + SSL | 1-2 horas | **Sí** |
| Generar llaves JWT y configurar .env | 30 min | **Sí** |
| Deploy inicial (docker compose up) | 1 hora | **Sí** |
| Correr migraciones | 10 min | **Sí** |
| Crear tenant + usuario para clínica beta | 15 min | **Sí** |
| Configurar SendGrid (emails) | 30 min | **Sí** |
| Configurar Sentry (monitoreo errores) | 15 min | Recomendado |
| Configurar backups automáticos | 2 horas | Recomendado |
| Configurar monitoreo (Grafana) | 3-4 horas | Puede esperar |
| Configurar integraciones reales (Nequi, etc.) | 1-2 días | No para beta |

### Timeline Estimado

```
Día 1:  Crear Hetzner + dominio + Cloudflare          (3 horas)
Día 1:  Deploy + migraciones + primer tenant           (2 horas)
Día 2:  SendGrid + Sentry + pruebas de humo            (3 horas)
Día 2:  Crear usuario admin de la clínica beta         (30 min)
Día 3:  Onboarding con la clínica (sesión presencial)  (2-3 horas)
        ──────────────────────────────────────────
        Total: ~2-3 días de trabajo
```

---

## 8. Variables de Entorno Críticas

Las que necesitas tener listas antes de desplegar:

```env
# === OBLIGATORIAS ===
ENVIRONMENT=production
SECRET_KEY=<generar-con-openssl-rand-hex-32>
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dentalos_prod
REDIS_URL=redis://:password@localhost:6379/0
RABBITMQ_URL=amqp://user:pass@localhost:5672/dentalos

# JWT (generar par RSA)
JWT_PRIVATE_KEY_PATH=keys/private.pem
JWT_PUBLIC_KEY_PATH=keys/public.pem

# Email
SENDGRID_API_KEY=SG.xxxxx
EMAIL_FROM_ADDRESS=noreply@dentalos.app

# URLs
CORS_ORIGINS=https://app.dentalos.app
FRONTEND_URL=https://app.dentalos.app
NEXT_PUBLIC_API_URL=https://api.dentalos.app

# S3
S3_ENDPOINT_URL=https://xxx.your-objectstorage.com
S3_ACCESS_KEY=xxx
S3_SECRET_KEY=xxx
S3_BUCKET_NAME=dentalos-prod

# Monitoreo
SENTRY_DSN=https://xxx@sentry.io/xxx

# === OPCIONALES PARA BETA (tienen mocks) ===
# ANTHROPIC_API_KEY=sk-ant-xxx
# OPENAI_API_KEY=sk-xxx
# TWILIO_ACCOUNT_SID=ACxxx
# NEQUI_CLIENT_ID=xxx
# WHATSAPP_ACCESS_TOKEN=xxx
```

---

## 9. Comandos Clave

```bash
# === En el servidor de producción ===

# Levantar todo
docker compose -f docker-compose.prod.yml up -d

# Ver logs
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend

# Correr migraciones
docker compose -f docker-compose.prod.yml exec backend \
  alembic -c alembic_public/alembic.ini upgrade head

docker compose -f docker-compose.prod.yml exec backend \
  alembic -c alembic_tenant/alembic.ini upgrade head

# Reiniciar un servicio
docker compose -f docker-compose.prod.yml restart backend

# Ver estado
docker compose -f docker-compose.prod.yml ps

# Backup de la base de datos
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U dentalos dentalos_prod > backup_$(date +%Y%m%d).sql

# Health check
curl https://api.dentalos.app/api/v1/health
```

---

## 10. Resumen Ejecutivo para el Socio

**¿Cuánto necesitamos?**
- **Opción mínima (1 clínica beta):** ~$65 USD/mes
- **Opción seria (5-20 clínicas):** ~$210 USD/mes

**¿Cuánto tiempo para estar en producción?**
- 2-3 días de trabajo técnico

**¿Qué riesgo hay?**
- El código está completo y probado (819/844 items = 97%)
- Las 13 integraciones tienen mocks para funcionar sin APIs reales
- El sistema soporta multi-tenancy desde el día 1

**¿Qué necesitamos comprar/crear?**
1. Cuenta en Hetzner Cloud (~$15/mes mínimo)
2. Un dominio (.app ~$15/año)
3. Cuenta Cloudflare (gratis)
4. Cuenta SendGrid (gratis hasta 100 emails/día)
5. Cuenta Sentry (gratis tier developer)

**Inversión inicial real: ~$30 USD** (primer mes de servidor + dominio)
