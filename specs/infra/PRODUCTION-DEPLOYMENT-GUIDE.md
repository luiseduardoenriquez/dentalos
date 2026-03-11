# DentalOS — Guia de Despliegue a Produccion

> Estrategia completa para llevar DentalOS de desarrollo a produccion.
> Incluye tres opciones: **Opcion A** (IA via API), **Opcion B** (IA local en el servidor), y **Opcion C** (VPS con GPU dedicada).

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Arquitectura General](#2-arquitectura-general)
3. [Inventario de Features de IA](#3-inventario-de-features-de-ia)
4. [Opcion A: IA via API Externa](#4-opcion-a-ia-via-api-externa)
5. [Opcion B: IA Local en Produccion](#5-opcion-b-ia-local-en-produccion)
6. [Opcion C: VPS con GPU Dedicada](#6-opcion-c-vps-con-gpu-dedicada)
7. [Comparativa A vs B vs C](#7-comparativa-a-vs-b-vs-c)
8. [Archivos de Infraestructura](#8-archivos-de-infraestructura)
9. [Proceso de Despliegue Paso a Paso](#9-proceso-de-despliegue-paso-a-paso)
10. [Seguridad](#10-seguridad)
11. [Monitoreo y Mantenimiento](#11-monitoreo-y-mantenimiento)
12. [Costos](#12-costos)
13. [Decision y Recomendacion](#13-decision-y-recomendacion)

---

## 1. Resumen Ejecutivo

DentalOS es un SaaS multi-tenant de gestion dental para LATAM (Colombia primero). El MVP esta completo (~97%). Necesitamos desplegarlo en produccion para la clinica beta.

**Lo que necesitamos correr:**

| Servicio | Funcion |
|----------|---------|
| PostgreSQL 16 | Base de datos principal (schema-per-tenant) |
| Redis 7 | Cache, sesiones, pub/sub para SSE |
| RabbitMQ 3 | Cola de mensajes para workers async |
| MinIO | Almacenamiento S3-compatible (archivos, imagenes) |
| Backend (FastAPI) | API REST, autenticacion, logica de negocio |
| Worker | 5 workers de background (notificaciones, compliance, voz, importacion, mantenimiento) |
| Frontend (Next.js) | Interfaz web, PWA, SSR |
| Nginx | Reverse proxy, TLS, headers de seguridad |

**La IA en DentalOS** consiste en 5 features que pueden correr como llamadas API externas (Anthropic + OpenAI) o como modelos locales (Ollama + faster-whisper). Las 3 features que solo tienen modo API (Treatment Advisor, Reports, Chatbot) siempre necesitan `ANTHROPIC_API_KEY` sin importar la opcion.

---

## 2. Arquitectura General

### En Desarrollo (tu Mac)

Solo la infraestructura corre en Docker. Backend y frontend corren nativos para hot-reload:

```
[tu Mac]
├── docker-compose.yml (infra solamente)
│   ├── postgres:5432
│   ├── redis:6379
│   ├── rabbitmq:5672
│   └── minio:9000
├── uvicorn --reload (backend, puerto 8000)
└── npm run dev (frontend, puerto 3000)
```

### En Produccion (Hetzner)

**Todo** corre en Docker, con Nginx nativo como entry point:

```
                    Internet
                       |
                  [Cloudflare]  (DNS + DDoS protection)
                       |
               [Hetzner Server]
                       |
                    [Nginx]     (TLS termination, reverse proxy)
                    /      \
                   /        \
           :3000  /          \  :8000
        [Frontend]          [Backend]
        (Next.js)           (FastAPI + Gunicorn)
                               |
                            [Worker]
                            (5 queues)
                               |
              +-------+--------+--------+--------+
              |       |        |        |        |
           [PgSQL] [Redis] [RabbitMQ] [MinIO] [Ollama]*
                                                  |
                                              (Solo Opcion B)
```

### Flujo de una Request

```
1. La doctora abre app.dentalos.co en su tablet
2. Cloudflare resuelve DNS → IP del servidor Hetzner
3. HTTPS llega al servidor (puerto 443)
4. Nginx recibe y rutea:
   ├── /api/* → FastAPI (puerto 8000)
   └── todo lo demas → Next.js (puerto 3000)
5. Si es API (/api/v1/patients):
   ├── Middleware extrae JWT del header Authorization
   ├── Valida firma RS256 con llave publica
   ├── Extrae tenant_id del JWT (claim "tid")
   ├── SET search_path TO tn_abc123, public
   ├── Ejecuta la logica de negocio (servicio → ORM → PostgreSQL)
   └── Retorna JSON
6. Si es frontend (/patients/123):
   ├── Next.js hace Server-Side Rendering
   ├── Llama al backend internamente (localhost:8000)
   ├── Renderiza HTML con datos
   └── Envia HTML + JS al browser
```

### Base de Datos: Aislamiento por Clinica

Cada clinica tiene su propio **schema** en PostgreSQL:

```
PostgreSQL Database: dentalos
├── public (schema compartido)
│   ├── tenants          → Lista de clinicas
│   ├── plans            → Planes de precios
│   ├── users            → Todos los usuarios
│   ├── superadmins      → Admin de la plataforma
│   └── catalogs         → CIE-10, CUPS, FDI
├── tn_clinica_sonrisas (schema de Clinica Sonrisas)
│   ├── patients         → 44+ tablas solo de esta clinica
│   ├── appointments
│   ├── clinical_records
│   ├── odontograms
│   └── ... (completamente aislado)
└── tn_dental_premium (schema de Dental Premium)
    └── ... (44+ tablas, datos separados)
```

**Por que asi?** Cumplimiento regulatorio colombiano — los datos clinicos de una clinica NUNCA pueden mezclarse con los de otra. Es literalmente otro esquema de base de datos.

---

## 3. Inventario de Features de IA

DentalOS tiene **5 features de IA**. Cada una puede configurarse independientemente.

### 3.1 Voice-to-Odontogram: STT (Speech-to-Text)

| Aspecto | Detalle |
|---------|---------|
| **Que hace** | Transcribe audio del dentista dictando hallazgos en espanol a texto |
| **Archivo** | `backend/app/services/voice_stt.py` |
| **Config** | `VOICE_STT_PROVIDER` = `"local"` o `"openai"` |
| **Modo local** | `faster-whisper` (CTranslate2, INT8 cuantizado, CPU). Ya instalado en el proyecto |
| **Modo API** | OpenAI Whisper API (`whisper-1`, $0.006/min) |
| **Gating** | Add-on: AI Voice ($10/doctor/mes) |

El modo local usa `device="cpu"`, `compute_type="int8"` — no necesita GPU. El modelo se descarga automaticamente de HuggingFace la primera vez.

**Modelos locales de Whisper disponibles:**

| Modelo | Parametros | Disco (INT8) | RAM en uso | Precision para espanol clinico |
|--------|-----------|-------------|------------|-------------------------------|
| `tiny` | 39M | ~75 MB | ~200 MB | Baja — no recomendado |
| `base` (default) | 74M | ~145 MB | ~300 MB | Media — aceptable para beta |
| `small` | 244M | ~490 MB | ~700 MB | Buena — recomendado para produccion |
| `medium` | 769M | ~1.5 GB | ~2 GB | Alta — si hay RAM disponible |

### 3.2 Voice-to-Odontogram: NLP (Extraccion Estructurada)

| Aspecto | Detalle |
|---------|---------|
| **Que hace** | Toma el texto transcrito y extrae hallazgos dentales estructurados: diente (FDI), zona, condicion, confianza |
| **Archivo** | `backend/app/services/voice_nlp.py` |
| **Config** | `VOICE_NLP_PROVIDER` = `"local"` o `"anthropic"` |
| **Modo local** | Ollama con Qwen 2.5, endpoint OpenAI-compatible (`/v1/chat/completions`) |
| **Modo API** | Anthropic Claude Haiku (`claude-haiku-4-5-20251001`) |
| **Gating** | Add-on: AI Voice ($10/doctor/mes) |

El prompt es un system message detallado con formato FDI, zonas dentales, y codigos de condicion. Espera respuesta JSON.

**Modelos locales de Qwen via Ollama:**

| Modelo | VRAM (GPU, Q4) | RAM (CPU, Q4) | Velocidad en CPU | Calidad |
|--------|---------------|---------------|-------------------|---------|
| `qwen2.5:7b` | ~5 GB | ~6 GB | 10-30 seg | Buena |
| `qwen2.5:14b` | ~9 GB | ~10 GB | 30-90 seg | Muy buena |
| `qwen2.5:32b` (default config) | ~20 GB | ~22 GB | 2-5 min | Excelente |

> **Nota:** El default `qwen2.5:32b` es impractico en CPU. Para Opcion B sin GPU, usar `qwen2.5:7b`.

### 3.3 AI Treatment Advisor

| Aspecto | Detalle |
|---------|---------|
| **Que hace** | Dado el odontograma + historia del paciente + catalogo CUPS de la clinica, sugiere tratamientos priorizados con costo, confianza y justificacion |
| **Archivo** | `backend/app/services/ai_treatment_service.py` |
| **Modelo** | Claude Sonnet (`claude-sonnet-4-5-20250514`) |
| **Modo local** | **No existe** — solo API |
| **Tokens** | max 4096, temperature 0.2 |
| **Seguridad** | Nunca envia PII — solo edad, tipo sangre, flags booleanos, codigos FDI y CUPS |
| **Gating** | Add-on: AI Voice ($10/doctor/mes) |

### 3.4 AI Natural Language Reports

| Aspecto | Detalle |
|---------|---------|
| **Que hace** | Recibe preguntas en espanol ("cuanto se facturo este mes") y las mapea a 1 de 10 queries SQL predefinidas. Claude NUNCA genera SQL — solo selecciona un `query_key` |
| **Archivo** | `backend/app/services/ai_report_service.py` |
| **Modelo** | Claude Haiku (`claude-haiku-4-5-20251001`) |
| **Modo local** | **No existe** — solo API |
| **Tokens** | max 1024, temperature 0.1 |
| **Gating** | Plan Pro+ |

Las 10 queries disponibles:

1. `revenue_by_period` — facturacion por periodo
2. `top_procedures` — procedimientos mas realizados (CUPS)
3. `appointment_no_show_rate` — tasa de inasistencia
4. `patient_retention_rate` — retencion de pacientes
5. `revenue_by_doctor` — ingreso por doctor
6. `treatment_completion_rate` — completitud de planes de tratamiento
7. `unpaid_invoices_aging` — cartera por vencer (0-30, 30-60, 60-90, 90+ dias)
8. `daily_appointment_count` — tendencia de citas por dia
9. `insurance_distribution` — distribucion de pacientes por EPS
10. `patients_by_age_group` — demografia por rango de edad

### 3.5 Chatbot / Recepcionista Virtual

| Aspecto | Detalle |
|---------|---------|
| **Que hace** | Chatbot para WhatsApp/portal con 8 intents: agendar, reagendar, cancelar, FAQ, pagos, horarios, ubicacion, emergencia |
| **Archivo** | `backend/app/services/chatbot_engine.py` |
| **Modelo** | Claude Haiku (`claude-haiku-4-5-20251001`) |
| **Modo local** | **No existe** — solo API |
| **Tokens** | max 512, temperature 0.1 |
| **Confianza** | Si confidence < 0.5, escala a humano automaticamente |
| **Gating** | Plan Pro+ |

### Resumen: Que se puede correr local vs API

| Feature | Modo Local | Modo API | Implementado |
|---------|-----------|---------|--------------|
| Voice STT | faster-whisper (CPU) | OpenAI Whisper API | Ambos |
| Voice NLP | Ollama + Qwen | Claude Haiku | Ambos |
| Treatment Advisor | -- | Claude Sonnet | Solo API |
| AI Reports | -- | Claude Haiku | Solo API |
| Chatbot | -- | Claude Haiku | Solo API |

**Conclusion:** Incluso en Opcion B (local), 3 de 5 features siguen necesitando `ANTHROPIC_API_KEY`. Lo que se ahorra es el costo de OpenAI Whisper y las llamadas Claude para NLP de voz.

---

## 4. Opcion A: IA via API Externa

### Concepto

Todo corre en **1 servidor Hetzner CX31** (4 vCPU, 8 GB RAM, 80 GB SSD, ~$15/mes). La IA se resuelve con llamadas API a Anthropic (Claude) y OpenAI (Whisper). No se necesita GPU ni modelos locales. Es la opcion mas simple y barata.

### Servidor: Hetzner CX31

| Spec | Valor |
|------|-------|
| CPU | 4 vCPU (Intel Xeon, shared) |
| RAM | 8 GB |
| Disco | 80 GB SSD |
| Red | 20 TB trafico incluido |
| Precio | ~13.49 EUR/mes (~$15 USD/mes) |
| Ubicacion | Falkenstein (Alemania) o Ashburn (US) |

### Distribucion de Recursos

| Servicio | RAM | CPU | Notas |
|----------|-----|-----|-------|
| PostgreSQL 16 | 1.5 GB | 1.0 | Schema-per-tenant, extensiones UUID/trgm/unaccent |
| Redis 7 | 256 MB | 0.25 | Cache, sesiones, pub/sub SSE |
| RabbitMQ 3 | 384 MB | 0.25 | 5 colas, management UI |
| MinIO | 384 MB | 0.25 | S3-compatible, archivos clinicos |
| Backend (2 gunicorn workers) | 768 MB | 0.75 | Gunicorn + UvicornWorker, WEB_WORKERS=2 |
| Worker (5 queues en 1 contenedor) | 512 MB | 0.5 | notification, compliance, voice, import, maintenance |
| Frontend (Next.js) | 384 MB | 0.25 | SSR + static, PWA |
| Nginx + OS | ~500 MB | -- | Nativo (no Docker), TLS, reverse proxy |
| **Total** | **~4.7 GB / 8 GB** | **~3.25 / 4** | **Holgado para 1 clinica beta** |

Sobran ~3 GB de RAM y ~0.75 CPU. Hay margen suficiente para picos de trafico.

### Configuracion de IA en `.env`

```env
# Voice: usar APIs externas
VOICE_STT_PROVIDER=openai
VOICE_NLP_PROVIDER=anthropic

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Modelos
ANTHROPIC_MODEL=claude-haiku-4-5-20251001          # Reports, Chatbot, Voice NLP
ANTHROPIC_MODEL_TREATMENT=claude-sonnet-4-5-20250514  # Treatment Advisor (mas potente)
```

### Costo Estimado de API por Mes (1 clinica, 2-3 doctores)

| Feature | Uso estimado/mes | Costo API/mes |
|---------|-----------------|--------------|
| Whisper STT (OpenAI) | ~50 dictados x 30s = 25 min | $0.15 |
| Claude Haiku (NLP voz) | ~50 calls x ~800 tokens | $0.04 |
| Claude Haiku (Reports) | ~100 calls x ~500 tokens | $0.05 |
| Claude Haiku (Chatbot) | ~200 calls x ~300 tokens | $0.06 |
| Claude Sonnet (Treatment) | ~50 calls x ~2000 tokens | $2.25 |
| **Total IA** | | **~$2.55/mes** |

> El costo de IA es insignificante comparado con el servidor. Incluso con 10 clinicas serian ~$25/mes en APIs.

### Diagrama de la Opcion A

```
[Servidor CX31 - 4 vCPU, 8 GB RAM]
│
├── Docker Network (dentalos-prod)
│   ├── postgres       (1.5 GB)  ← schema-per-tenant
│   ├── redis          (256 MB)  ← cache + sesiones + pub/sub
│   ├── rabbitmq       (384 MB)  ← 5 colas async
│   ├── minio          (384 MB)  ← archivos S3
│   ├── backend        (768 MB)  ──→ HTTPS ──→ api.anthropic.com (Claude)
│   │                            ──→ HTTPS ──→ api.openai.com (Whisper)
│   ├── worker         (512 MB)  ──→ HTTPS ──→ api.openai.com (transcripcion)
│   │                            ──→ HTTPS ──→ api.anthropic.com (NLP)
│   └── frontend       (384 MB)  ← Next.js SSR + PWA
│
└── Nginx (nativo, ~100 MB)      ← TLS, reverse proxy, security headers
```

### Ventajas de la Opcion A

1. **Simplicidad operativa:** 0 operaciones de IA — solo configuras API keys y ya
2. **Costo de servidor minimo:** $15/mes para toda la plataforma
3. **Mejor precision:** Whisper Large v3 (API) y Claude son los mejores modelos disponibles
4. **Mejor velocidad:** 1-5s latencia por llamada de IA
5. **Escalabilidad infinita de IA:** no te quedas sin GPU/RAM
6. **Sin mantenimiento de modelos:** no hay que actualizar pesos, no hay out-of-memory, no hay drivers CUDA
7. **Menor superficie de error:** menos cosas que pueden fallar

### Desventajas de la Opcion A

1. **Dependencia externa:** si Anthropic o OpenAI se caen, las features de IA no funcionan (el resto de la app si)
2. **Datos salen del servidor:** el audio del dictado y el texto transcrito viajan a servidores de terceros
3. **Regulatorio:** potencial conflicto con Ley 1581 de 2012 (proteccion de datos personales) y Resolucion 1995 de 1999 (historia clinica). El audio de voz es dato clinico protegido (PHI)
4. **Latencia variable:** depende de la red y la carga de los proveedores
5. **Costo escala linealmente:** con 100+ clinicas, el costo de API crece

---

## 5. Opcion B: IA Local en Produccion

### Concepto

Los modelos de STT (Whisper) y NLP (Qwen) corren **dentro del servidor de produccion**. El audio y el texto clinico nunca salen del servidor.

Las 3 features que solo tienen modo API (Treatment Advisor, Reports, Chatbot) **siguen necesitando Anthropic API** — no hay implementacion local para ellas.

### Que cambia vs Opcion A

| Componente | Opcion A | Opcion B |
|-----------|---------|---------|
| Whisper STT | API OpenAI ($0.006/min) | faster-whisper local (CPU, INT8) |
| Voice NLP | API Claude Haiku | Ollama + Qwen local |
| Treatment Advisor | API Claude Sonnet | API Claude Sonnet (sin cambio) |
| AI Reports | API Claude Haiku | API Claude Haiku (sin cambio) |
| Chatbot | API Claude Haiku | API Claude Haiku (sin cambio) |
| Servidor | CX31 (4 vCPU, 8 GB) | CCX33+ (8 vCPU, 32 GB) |
| Contenedor extra | -- | Ollama |

### Sub-opcion B1: Solo CPU (sin GPU) — Hetzner CCX33

Para correr Ollama en CPU se necesita mucha RAM. El modelo `qwen2.5:7b` (el mas practico sin GPU) necesita ~8 GB solo para el modelo cargado en memoria.

| Spec | Hetzner CCX33 |
|------|---------------|
| CPU | 8 vCPU (AMD EPYC, **dedicados**) |
| RAM | 32 GB |
| Disco | 240 GB SSD |
| Precio | ~52 EUR/mes (~$57 USD/mes) |
| GPU | Ninguna |

**Distribucion de recursos en CCX33:**

| Servicio | RAM | Notas |
|----------|-----|-------|
| PostgreSQL | 2 GB | Mas headroom para queries complejas |
| Redis | 256 MB | |
| RabbitMQ | 384 MB | |
| MinIO | 384 MB | |
| Backend (2 workers) | 768 MB | |
| Worker (5 queues) | 768 MB | faster-whisper base (~300 MB) corre dentro del worker |
| Frontend | 384 MB | |
| **Ollama + qwen2.5:7b** | **8 GB** | Modelo cargado permanentemente en RAM |
| Nginx + OS | 1 GB | |
| **Total** | **~14 GB / 32 GB** | Buffer amplio para picos |

**Rendimiento esperado en CPU (8 vCPU AMD EPYC):**

| Tarea | Modelo | Tiempo estimado | Experiencia de usuario |
|-------|--------|----------------|----------------------|
| Whisper STT (audio 30s) | `base` (int8) | 3-8 segundos | Aceptable |
| Whisper STT (audio 30s) | `small` (int8) | 8-15 segundos | Aceptable con spinner |
| Qwen NLP (extraccion dental) | `7b` (Q4, CPU) | 10-30 segundos | Lento pero funcional |
| Qwen NLP (extraccion dental) | `14b` (Q4, CPU) | 30-90 segundos | Demasiado lento |
| Qwen NLP (extraccion dental) | `32b` (Q4, CPU) | 2-5 minutos | **Impractico** |

> **Veredicto B1:** Funcional pero lento para NLP. El doctor dicta, espera 15-30 segundos, y ve los hallazgos poblados en el odontograma. Aceptable para beta si se usa `qwen2.5:7b`. El modelo `32b` del default NO funciona en CPU.

### Sub-opcion B2: Con GPU — Servidor Dedicado

Hetzner no ofrece GPU en servidores cloud compartidos. Opciones reales:

| Proveedor | GPU | VRAM | RAM | Precio/mes |
|-----------|-----|------|-----|------------|
| Hetzner Auction (dedicado) | GTX 1080 / RTX 2080 | 8-11 GB | 64 GB | ~$60-90 |
| Hetzner Configurador (dedicado) | RTX A4000 | 16 GB | 64 GB | ~$120-180 |
| RunPod / Vast.ai | RTX 4090 | 24 GB | 32 GB | ~$0.40/hr = ~$290/mes |
| Lambda Cloud | A10G | 24 GB | 64 GB | ~$0.75/hr = ~$540/mes |

**Rendimiento con GPU:**

| Tarea | Modelo | RTX 3090 (24 GB) | RTX 4090 (24 GB) |
|-------|--------|------------------|-------------------|
| Whisper STT (30s audio) | `small` | < 1 segundo | < 0.5 segundos |
| Whisper STT (30s audio) | `medium` | 1-2 segundos | < 1 segundo |
| Qwen NLP | `7b` | 1-3 segundos | < 1 segundo |
| Qwen NLP | `14b` | 3-8 segundos | 1-3 segundos |
| Qwen NLP | `32b` | 5-15 segundos | 3-8 segundos |

> **Veredicto B2:** Rendimiento excelente, experiencia identica a APIs. Pero el costo es 4-20x mayor.

### Configuracion de IA Local en `.env`

```env
# Voice: usar modelos locales
VOICE_STT_PROVIDER=local
VOICE_NLP_PROVIDER=local

# Whisper local (corre dentro del worker process)
WHISPER_MODEL_SIZE=small          # "base" para menos RAM, "small" para mejor precision

# Ollama local (contenedor separado)
OLLAMA_BASE_URL=http://ollama:11434    # Nombre del servicio Docker
OLLAMA_MODEL=qwen2.5:7b               # 7b para CPU, 14b/32b si tienes GPU
OLLAMA_TIMEOUT_SECONDS=120             # 120s timeout por request

# Anthropic (SIGUE SIENDO NECESARIO para Treatment Advisor, Reports, Chatbot)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_MODEL_TREATMENT=claude-sonnet-4-5-20250514
```

### docker-compose.prod.yml: Servicio Ollama adicional

Para Opcion B, agregar al compose:

```yaml
  # ── Ollama (Local LLM inference) ──────────────────────────────────────────
  ollama:
    image: ollama/ollama:latest
    container_name: dentalos-ollama-prod
    restart: unless-stopped
    networks:
      - dentalos-network
    ports:
      - "127.0.0.1:11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    # --- GPU NVIDIA (descomentar si tienes GPU) ---
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]
    # --- CPU-only ---
    deploy:
      resources:
        limits:
          memory: 10g        # 8 GB para modelo + 2 GB buffer
          cpus: "4.0"        # Necesita CPUs dedicados para inference
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:11434/api/tags || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
```

Y agregar el volumen:

```yaml
volumes:
  ollama_data:
    name: dentalos_ollama_data
```

Despues del primer `docker compose up -d ollama`, descargar el modelo:

```bash
docker compose -f docker-compose.prod.yml exec ollama ollama pull qwen2.5:7b
# Tarda ~5 min la primera vez (descarga ~4.7 GB)
```

### Ventajas de la Opcion B

1. **Privacidad total de datos clinicos:** audio y texto de dictados nunca salen del servidor. Cumplimiento total con Ley 1581/2012 y Resolucion 1995/1999
2. **Sin dependencia de OpenAI para voz:** STT + NLP funcionan sin internet
3. **Costo predecible:** no hay costo variable por llamada de API para voz
4. **Capacidad offline:** si se pierde internet, la voz sigue funcionando (las otras 3 features de IA no)

### Desventajas de la Opcion B

1. **Costo de servidor 3-4x mayor:** $57/mes (CPU) o $90-180/mes (GPU) vs $15/mes
2. **Complejidad operativa:** hay que mantener Ollama, descargar/actualizar modelos, monitorear memoria, riesgo de OOM
3. **Menor precision en NLP:** Qwen 7B es bueno pero inferior a Claude Haiku para extraccion estructurada dental en espanol
4. **Latencia mayor en CPU:** 15-30s por dictado completo vs 2-8s con API
5. **Solo cubre 2 de 5 features:** Treatment Advisor, Reports y Chatbot SIGUEN necesitando Anthropic API. No se elimina la dependencia
6. **Riesgo de OOM:** si el modelo consume mas memoria de lo esperado, puede tumbar PostgreSQL u otros servicios
7. **Modelo default impractico:** el config actual dice `qwen2.5:32b` (22 GB RAM) — hay que cambiarlo a `7b` para CPU

---

## 6. Opcion C: VPS con GPU Dedicada

### Concepto

En lugar de usar Hetzner Cloud (sin GPU) o servidores dedicados caros via subastas, contratar un **VPS con GPU dedicada** de un proveedor especializado en GPU hosting. Estos proveedores ofrecen servidores con tarjetas NVIDIA dedicadas a precios mensuales fijos, ideales para correr Ollama + faster-whisper con rendimiento de GPU real.

**La idea:** separar la infraestructura en dos servidores:

1. **Hetzner CX31** ($15/mes) — corre todo excepto IA (PostgreSQL, Redis, RabbitMQ, MinIO, Backend, Frontend)
2. **GPU VPS** ($76-184/mes) — corre solo Ollama + faster-whisper, expuesto internamente via VPN/WireGuard

O alternativamente, consolidar **todo en un solo GPU VPS** que tenga suficiente RAM y CPU para correr la stack completa + modelos de IA.

### Proveedores Investigados (Marzo 2026)

#### Tier 1: Budget ($76-100/mes) — Entrada minima con GPU

| Proveedor | GPU | VRAM | CPU | RAM | Disco | Precio/mes |
|-----------|-----|------|-----|-----|-------|-----------|
| **Hostkey** (Islandia) | GTX 1080 Ti | 11 GB | E5-26xx (8 cores) | 32 GB | 240 GB SSD | **$76** |
| **TensorDock** (marketplace) | RTX 3060 | 12 GB | Variable | Variable | Variable | **~$100** |

**Rendimiento estimado Tier 1 (GTX 1080 Ti / RTX 3060):**

| Tarea | Modelo | Tiempo | Viable? |
|-------|--------|--------|---------|
| Whisper STT (30s audio) | `small` (int8) | 1-3 s | Si |
| Whisper STT (30s audio) | `medium` (int8) | 2-5 s | Si |
| Qwen NLP | `qwen2.5:7b` (Q4) | 2-5 s | Si |
| Qwen NLP | `qwen2.5:14b` (Q4) | No cabe en 11 GB VRAM | No (1080 Ti) |

> **GTX 1080 Ti:** Solo sirve para modelos 7B. Los 11 GB de VRAM limitan a modelos Q4 de hasta ~8B parametros. Pero para Whisper + Qwen 7B es suficiente y la experiencia de usuario es rapida (< 8s por dictado).

> **RTX 3060:** Con 12 GB de VRAM tiene un poco mas de margen. Modelos 7B corren fluidos. Modelos 13-14B apretados.

#### Tier 2: Sweet Spot ($136-184/mes) — Recomendado para DentalOS

| Proveedor | GPU | VRAM | CPU | RAM | Disco | Precio/mes |
|-----------|-----|------|-----|-----|-------|-----------|
| **Hostkey** (Paises Bajos) | RTX A4000 | 16 GB | EPYC 7402 (8 cores) | 32 GB | 240 GB SSD | **$136** |
| **DatabaseMart** | RTX A4000 | 16 GB | 24 cores | 32 GB | 320 GB SSD | **$179** |
| **Hetzner GEX44** (Alemania) | RTX 4000 SFF Ada | 20 GB | i5-13500 (14 cores) | 64 GB | 2x1.92 TB NVMe | **~$184 (€170)** |

**Rendimiento real benchmarked en A4000 (16 GB VRAM):**

| Modelo | Parametros | Tokens/s | GPU Util | Viable? |
|--------|-----------|----------|----------|---------|
| Qwen 2.5 7B (Q4) | 7B | **52.68 t/s** | 12% | Excelente |
| LLaMA 3.1 8B | 8B | 51.35 t/s | 78% | Excelente |
| LLaMA 2 13B | 13B | 38.46 t/s | 89% | Muy bueno |
| DeepSeek-Coder 16B | 16B | 22.89 t/s | 40% | Aceptable |
| Gemma2 27B | 27B | 2.38 t/s | 1% | **Impractico** |

> **La A4000 es el sweet spot** para DentalOS: corre `qwen2.5:7b` a 52+ tokens/s (respuesta en 1-2s) y `qwen2.5:14b` cabe comodo en 16 GB VRAM con buen rendimiento. Whisper `medium` corre en < 1s.

> **El Hetzner GEX44 es la mejor relacion calidad/precio** si quieres todo en un solo servidor: 20 GB VRAM (RTX 4000 Ada), 64 GB RAM (sobra para toda la stack), 2x1.92 TB NVMe, y es del mismo proveedor que ya conocemos. Precio: ~€170/mes (antes de aumento en abril 2026 sube a ~€212/mes).

#### Tier 3: Premium ($272+/mes) — Maxima calidad

| Proveedor | GPU | VRAM | CPU | RAM | Disco | Precio/mes |
|-----------|-----|------|-----|-----|-------|-----------|
| **Hostkey** (Islandia) | RTX 4090 | 24 GB | EPYC 7402 (8 cores) | 64 GB | 240 GB NVMe | **$272** |
| **RunPod** (on-demand) | RTX 4090 | 24 GB | Variable | Variable | Variable | **~$430** |
| **Vast.ai** (marketplace) | RTX 4090 | 24 GB | Variable | Variable | Variable | **~$175-440** |

**Rendimiento estimado Tier 3 (RTX 4090):**

| Tarea | Modelo | Tiempo | Viable? |
|-------|--------|--------|---------|
| Whisper STT (30s) | `medium` | < 0.5 s | Si |
| Qwen NLP | `qwen2.5:7b` | < 1 s | Si |
| Qwen NLP | `qwen2.5:14b` | 1-3 s | Si |
| Qwen NLP | `qwen2.5:32b` | 3-8 s | Si |

> La RTX 4090 con 24 GB VRAM puede correr **todos los modelos** incluyendo `qwen2.5:32b`. Pero el costo es prohibitivo para beta.

### Arquitectura Recomendada: Opcion C con Hetzner GEX44 (Todo en Uno)

El GEX44 tiene suficientes recursos (64 GB RAM, 14 cores CPU, 20 GB VRAM) para correr **toda la stack de DentalOS + modelos de IA** en un solo servidor:

```
[Hetzner GEX44 — i5-13500, 64 GB RAM, RTX 4000 Ada 20 GB VRAM]
│
├── Docker Network (dentalos-prod)
│   ├── postgres       (2 GB RAM)   ← schema-per-tenant
│   ├── redis          (256 MB)     ← cache + sesiones + pub/sub
│   ├── rabbitmq       (384 MB)     ← 5 colas async
│   ├── minio          (384 MB)     ← archivos S3
│   ├── backend        (768 MB)     ← Gunicorn + UvicornWorker
│   ├── worker         (1 GB RAM)   ← faster-whisper medium (~2 GB en GPU)
│   ├── frontend       (384 MB)     ← Next.js SSR + PWA
│   └── ollama         (GPU)        ← qwen2.5:14b (~9 GB VRAM)
│                                      Whisper medium (~2 GB VRAM)
│                                      Total VRAM: ~11 GB / 20 GB
│
└── Nginx (nativo)                  ← TLS, reverse proxy
```

**Distribucion de recursos en GEX44:**

| Servicio | RAM | VRAM (GPU) | Notas |
|----------|-----|-----------|-------|
| PostgreSQL | 2 GB | -- | Mas headroom que CX31 |
| Redis | 256 MB | -- | |
| RabbitMQ | 384 MB | -- | |
| MinIO | 384 MB | -- | |
| Backend (2 workers) | 768 MB | -- | |
| Worker (5 queues) | 1 GB | -- | faster-whisper corre en GPU via Ollama |
| Frontend | 384 MB | -- | |
| **Ollama** | 2 GB (overhead) | **~11 GB** | qwen2.5:14b + whisper medium |
| Nginx + OS | 1 GB | -- | |
| **Total** | **~8.2 GB / 64 GB** | **~11 GB / 20 GB** | **Sobra muchisimo** |

> Con 64 GB de RAM y solo ~8 GB usados, hay margen para escalar a multiples clinicas, agregar mas workers, o subir PostgreSQL shared_buffers. Con 20 GB de VRAM y ~11 GB usados, se podria hasta subir a `qwen2.5:32b` (Q4, ~20 GB) si se quita whisper de GPU.

### Arquitectura Alternativa: Dos Servidores (Hetzner CX31 + GPU VPS Hostkey)

Si se prefiere separar la infraestructura base de la IA:

```
[Hetzner CX31 — $15/mes]                    [Hostkey A4000 — $136/mes]
├── postgres, redis, rabbitmq, minio         ├── ollama (qwen2.5:14b)
├── backend, worker, frontend                └── (expone :11434 via WireGuard)
└── nginx
         |                                            |
         └──────── WireGuard VPN tunnel ──────────────┘
                   Backend llama a Ollama via VPN
```

**Ventaja:** Si la GPU VPS falla, la app sigue funcionando (solo pierde Voice NLP local, fallback a API). **Desventaja:** Complejidad de red (WireGuard), latencia inter-servidor (~5-20ms), dos facturas.

### Configuracion de IA en `.env` (Opcion C)

```env
# Voice: usar modelos locales con GPU
VOICE_STT_PROVIDER=local
VOICE_NLP_PROVIDER=local

# Whisper local — modelo medium viable gracias a GPU
WHISPER_MODEL_SIZE=medium          # "medium" para GPU (mejor precision), "small" si 1080 Ti
WHISPER_DEVICE=cuda                # Usar GPU para Whisper (requiere faster-whisper con CUDA)

# Ollama local con GPU
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:14b          # 14b viable con >=16 GB VRAM, 7b si 1080 Ti (11 GB)
OLLAMA_TIMEOUT_SECONDS=30         # Timeout mas bajo porque GPU es rapido

# Anthropic (SIGUE SIENDO NECESARIO para Treatment Advisor, Reports, Chatbot)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_MODEL_TREATMENT=claude-sonnet-4-5-20250514
```

### docker-compose.prod.yml: Ollama con GPU

```yaml
  # ── Ollama (Local LLM inference con GPU) ─────────────────────────────────
  ollama:
    image: ollama/ollama:latest
    container_name: dentalos-ollama-prod
    restart: unless-stopped
    networks:
      - dentalos-network
    ports:
      - "127.0.0.1:11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
        limits:
          memory: 4g          # Solo overhead de proceso, modelos van a VRAM
          cpus: "2.0"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:11434/api/tags || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s       # Mas tiempo para cargar modelo en GPU
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - OLLAMA_NUM_PARALLEL=2  # Permite 2 requests concurrentes
```

**Prerequisito:** Instalar NVIDIA Container Toolkit en el servidor:

```bash
# En el servidor GPU VPS (Ubuntu 22.04):
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Rendimiento Esperado: Opcion C vs A vs B1

| Tarea | Opcion A (API) | Opcion B1 (CPU) | Opcion C (GPU VPS) |
|-------|---------------|----------------|-------------------|
| **Whisper STT (30s)** | 1-3s | 3-8s (base) / 8-15s (small) | **< 1s (medium)** |
| **Qwen NLP** | 1-5s (Haiku) | 10-30s (7b CPU) | **1-3s (14b GPU)** |
| **Latencia total dictado** | **2-8s** | **15-30s** | **1-4s** |
| **Precision STT** | Excelente (Large v3) | Buena (base/small) | **Muy alta (medium GPU)** |
| **Precision NLP** | Excelente (Haiku) | Buena (7b) | **Muy buena (14b)** |

> **Opcion C iguala o supera la latencia de APIs** (1-4s vs 2-8s) y usa un modelo NLP mas grande (14b vs 7b en CPU) con mejor precision, manteniendo la privacidad de datos clinicos.

### Proveedores: Tabla Comparativa Completa

| Proveedor | GPU | VRAM | RAM | Disco | Precio/mes | Ubicacion | Deploy | Ideal para |
|-----------|-----|------|-----|-------|-----------|-----------|--------|------------|
| **Hostkey** | 1080 Ti | 11 GB | 32 GB | 240 GB SSD | **$76** | Islandia | 15 min | Beta minimo |
| **TensorDock** | RTX 3060 | 12 GB | Variable | Variable | **~$100** | Variable | Minutos | Beta minimo |
| **Hostkey** | A4000 | 16 GB | 32 GB | 240 GB SSD | **$136** | Paises Bajos | 15 min | Produccion (solo GPU) |
| **Hetzner GEX44** | RTX 4000 Ada | 20 GB | 64 GB | 3.84 TB NVMe | **~$184** | Alemania | Horas | **Todo en uno** |
| **DatabaseMart** | A4000 | 16 GB | 32 GB | 320 GB SSD | **$179** | USA | Horas | Produccion |
| **Hostkey** | RTX 4090 | 24 GB | 64 GB | 240 GB NVMe | **$272** | Islandia | 15 min | Premium |
| **Vast.ai** | RTX 4090 | 24 GB | Variable | Variable | **$175-440** | Variable | Minutos | No recomendado* |
| **RunPod** | RTX 4090 | 24 GB | Variable | Variable | **~$430** | Variable | Minutos | No recomendado* |

> *Vast.ai y RunPod son **marketplaces** con precios variables, hardware no garantizado, y riesgo de interrupcion. **No recomendados para produccion de un SaaS de salud.** Utiles para experimentacion y desarrollo.

### Ventajas de la Opcion C

1. **Mejor rendimiento que B1:** GPU acelera inference 10-30x vs CPU. Latencia de 1-4s vs 15-30s
2. **Mejor que B2 en costo/beneficio:** $136-184/mes por un servidor GPU dedicado con soporte, vs $90-180/mes por un Hetzner Auction sin garantia de GPU especifica
3. **Privacidad total:** igual que B — audio y texto clinico nunca salen del servidor
4. **Modelo mas grande viable:** `qwen2.5:14b` en GPU vs `qwen2.5:7b` en CPU = mejor precision en extraccion dental
5. **Whisper medium:** viable en GPU (< 1s) vs impractico en CPU (8-15s). Mejor precision en espanol clinico
6. **Proveedores especializados:** Hostkey, DatabaseMart, Hetzner GEX son estables, con SLA, no son marketplaces volatiles
7. **GEX44 todo en uno:** 64 GB RAM y 20 GB VRAM = corre la stack completa sin necesidad de 2 servidores
8. **Mismo proveedor (Hetzner):** si se elige GEX44, se mantiene la relacion con Hetzner. Facturacion unificada, misma red, mismos data centers

### Desventajas de la Opcion C

1. **Costo 7-10x vs Opcion A:** $136-184/mes vs $18/mes — significativo para beta
2. **Complejidad operativa:** hay que mantener drivers NVIDIA, CUDA toolkit, Ollama, modelos. Mas que A, similar a B2
3. **Disponibilidad limitada:** los GPU VPS baratos se agotan rapido (Hostkey muestra "3 servers remaining"). Hay que reservar pronto
4. **Solo cubre 2 de 5 features:** igual que B — Treatment Advisor, Reports, Chatbot siguen en API
5. **Vendor lock-in de GPU:** si Hostkey sube precios o se queda sin stock, hay que migrar
6. **Hetzner GEX44 sube de precio:** a partir de abril 2026, pasa de €170 a ~€212/mes (~$230/mes)
7. **Overhead de NVIDIA stack:** nvidia-container-toolkit, drivers CUDA, compatibilidad de versiones — mas superficie de error

---

## 7. Comparativa A vs B vs C

### Tabla Completa

| Dimension | Opcion A (API) | Opcion B1 (Local CPU) | Opcion C (GPU VPS) |
|-----------|---------------|----------------------|-------------------|
| **Servidor** | CX31 (4 vCPU, 8 GB) | CCX33 (8 vCPU, 32 GB) | GEX44 (14 cores, 64 GB, RTX 4000 Ada) |
| **Costo servidor/mes** | ~$15 | ~$57 | ~$136-184 |
| **Costo IA APIs/mes** | ~$2.55 | ~$0.50 (solo Anthropic 3 features) | ~$0.50 |
| **Costo total/mes** | **~$18** | **~$58** | **~$137-185** |
| **Latencia STT** | 1-3s (API) | 3-8s (CPU, base) | **< 1s (medium, GPU)** |
| **Latencia NLP** | 1-5s (Haiku) | 10-30s (7b, CPU) | **1-3s (14b, GPU)** |
| **Latencia total dictado** | **2-8s** | **15-30s** | **1-4s** |
| **Precision STT** | Excelente (Whisper Large v3) | Buena-Muy buena (base/small) | **Muy alta (medium GPU)** |
| **Precision NLP** | Excelente (Claude Haiku) | Buena (Qwen 7B) | **Muy buena (Qwen 14B)** |
| **Privacidad audio/texto** | Sale del servidor | Queda local | **Queda local** |
| **Dependencia internet IA** | 5/5 features | 3/5 features | 3/5 features |
| **Complejidad ops** | Minima | Media | Media-Alta |
| **Riesgo de fallo IA** | Bajo (proveedores estables) | Medio (OOM, modelo lento) | Bajo (GPU dedicada) |
| **Escalabilidad IA** | Infinita | Limitada por RAM | Limitada por VRAM |
| **Modelo NLP maximo** | Claude Haiku (cloud) | Qwen 7B | **Qwen 14B (16 GB VRAM) / 32B (24 GB)** |

### Arbol de Decision (actualizado con Opcion C)

```
¿Cuantos dictados de voz se hacen al mes?
├── < 200 (tipico 1-3 clinicas)
│   └── ¿Hay requisito regulatorio estricto de residencia de datos?
│       ├── SI → ¿Es importante la velocidad de respuesta?
│       │       ├── SI → Opcion C ($136-184/mes) — GPU, 1-4s, privacidad total
│       │       └── NO → Opcion B1 ($57/mes) — CPU, 15-30s, privacidad total
│       └── NO → Opcion A ($18/mes) — mas simple y barato
│
├── 200-2000 (5-20 clinicas)
│   └── ¿El costo de API > $50/mes?
│       ├── SI → Opcion C ($136-184/mes) — GPU, mejor rendimiento que B1
│       └── NO → Opcion A sigue siendo mas barato
│
└── > 2000 (20+ clinicas)
    └── ¿Prioridad?
        ├── Rendimiento + privacidad → Opcion C con RTX 4090 ($272/mes)
        └── Minimo costo → Opcion B1 con CCX33 ($57/mes)
```

### Punto de Equilibrio (Breakeven)

```
Costo A  = $15 (server) + $X (API calls)
Costo B1 = $57 (server) + $0.50 (API parcial)
Costo C  = $136-184 (GPU VPS) + $0.50 (API parcial)

Breakeven A vs B1: $X = $42.50/mes → ~5,000 dictados/mes → ~50-100 clinicas
Breakeven A vs C:  $X = $121-169/mes → ~16,000-22,000 dictados/mes → ~160-220 clinicas

Pero C NO se justifica solo por ahorro — se justifica por:
  1. Privacidad de datos clinicos (regulatorio)
  2. Rendimiento superior (1-4s vs 15-30s de B1)
  3. Precision superior (14B vs 7B de B1)
  4. Independencia parcial de APIs externas
```

**Conclusion:**
- **Opcion A** es la mejor para beta y primeras clinicas ($18/mes, simple, rapido)
- **Opcion B1** tiene sentido solo si el regulatorio exige datos locales Y el presupuesto es limitado
- **Opcion C** es la mejor opcion cuando se necesita **privacidad + rendimiento**: cuesta mas que B1 pero la experiencia de usuario es dramaticamente mejor (1-4s vs 15-30s)

---

## 8. Archivos de Infraestructura

### Estructura de archivos creados

```
dentalos/
├── docker-compose.prod.yml          # 7 servicios Docker con resource limits
├── .env.production                  # Template de variables de produccion
├── nginx/
│   └── dentalos.conf                # Nginx reverse proxy + TLS + security headers
├── scripts/
│   └── deploy/
│       ├── setup-server.sh          # Setup inicial del servidor
│       └── first-deploy.sh          # Primer despliegue completo
└── .github/
    └── workflows/
        └── cd.yml                   # CI/CD: build → push GHCR → deploy via SSH
```

### docker-compose.prod.yml

Define 7 servicios con resource limits ajustados para CX31:

| Servicio | Imagen | RAM limit | CPU limit | Healthcheck |
|----------|--------|-----------|-----------|-------------|
| postgres | postgres:16-alpine | 1536m | 1.0 | pg_isready |
| redis | redis:7-alpine | 256m | 0.25 | redis-cli ping |
| rabbitmq | rabbitmq:3-management-alpine | 384m | 0.25 | rabbitmq-diagnostics |
| minio | minio/minio:latest | 384m | 0.25 | curl /minio/health/live |
| backend | dentalos-backend:latest | 768m | 0.75 | curl /api/v1/health |
| worker | dentalos-backend:latest | 512m | 0.5 | -- |
| frontend | dentalos-frontend:latest | 384m | 0.25 | wget localhost:3000 |

El **worker** usa la misma imagen Docker del backend pero con un comando diferente: `python -m app.workers.main`. Esto levanta los 5 workers (notification, compliance, voice, import, maintenance) en un solo proceso async. Para beta con 1 clinica es suficiente.

Todos los puertos escuchan en `127.0.0.1` — nunca expuestos al internet.

### .env.production

Template organizado por secciones con valores `CHANGE_ME` donde van secrets:

- Docker Compose vars (passwords de PostgreSQL, Redis, RabbitMQ, MinIO)
- Aplicacion (ENVIRONMENT=production, LOG_LEVEL=WARNING, ALLOWED_HOSTS)
- Seguridad (SECRET_KEY, PASSWORD_PEPPER)
- JWT (RS256 key paths, TTLs, bcrypt rounds)
- CORS y frontend URL
- S3 (MinIO credentials y bucket name)
- IA (providers, API keys, modelos Claude)
- Email (SendGrid API key, from address)
- Monitoreo (Sentry DSN, Prometheus token)

### nginx/dentalos.conf

- Redirect HTTP :80 → HTTPS :443
- TLS con Let's Encrypt (certbot --nginx)
- Proxy `/api/` → backend:8000 con soporte SSE (buffering off, read timeout 300s)
- Proxy `/` → frontend:3000 con soporte WebSocket
- Cache de assets estaticos (`/_next/static/` → 365 dias, immutable)
- Service worker sin cache agresivo (`/sw.js`, `/serwist/`)
- Rate limiting: 10 req/s por IP en `/api/` (burst 20)
- Security headers: HSTS (2 anos, preload), X-Frame-Options SAMEORIGIN, X-Content-Type-Options nosniff, X-XSS-Protection, Referrer-Policy, Permissions-Policy
- Client max body size: 25 MB
- Deny access a archivos ocultos (dotfiles)

### scripts/deploy/setup-server.sh

Script **idempotente** (seguro de correr multiples veces) que:

1. Actualiza paquetes del sistema (apt-get upgrade)
2. Instala Docker CE + Docker Compose plugin (si no estan)
3. Crea `/opt/dentalos/` con subdirectorios: keys/, backups/, logs/
4. Genera llaves JWT RSA 2048-bit con OpenSSL (si no existen)
5. Genera `.env` con passwords seguros (`openssl rand -hex`) para cada servicio + placeholders CHANGE_ME para API keys
6. Configura UFW firewall: allow 22 (SSH), 80 (HTTP), 443 (HTTPS), deny todo lo demas
7. Instala Nginx + certbot, copia la config si esta disponible

### scripts/deploy/first-deploy.sh

Script para el primer despliegue que:

1. Verifica prerequisitos (.env, compose file, JWT keys)
2. Copia JWT keys al build context del backend
3. Build imagenes Docker en paralelo (`docker compose build --parallel`)
4. Levanta infra primero (postgres, redis, rabbitmq, minio) y espera healthchecks
5. Corre migraciones public + tenant (`alembic upgrade head`)
6. Crea bucket S3 en MinIO via `mc` CLI
7. Levanta backend, worker, frontend
8. Ejecuta seed de datos iniciales (planes, catalogos CIE-10/CUPS, tenant demo, usuarios)
9. Verifica todos los servicios y imprime resumen con URLs y credenciales

### .github/workflows/cd.yml

Pipeline de CD que en cada push a master:

1. Build imagenes backend y frontend en paralelo (GitHub Actions)
2. Push a GitHub Container Registry (GHCR) con tag SHA
3. SSH al servidor de produccion
4. Pull imagenes nuevas, tag como :latest
5. `docker compose up -d --no-build backend frontend worker` ← **worker incluido**
6. Health check del API
7. Cleanup de imagenes viejas

---

## 9. Proceso de Despliegue Paso a Paso

### Pre-requisitos

| # | Item | Obligatorio? |
|---|------|-------------|
| 1 | Cuenta Hetzner Cloud | Si |
| 2 | Dominio (ej: dentalos.co) | Si |
| 3 | Cuenta Cloudflare (DNS) | Si (gratis) |
| 4 | API key Anthropic | Si (para IA) |
| 5 | API key OpenAI | Solo Opcion A |
| 6 | API key SendGrid | Si (para emails) |
| 7 | Proyecto Sentry | Recomendado |
| 8 | Repo en GitHub | Si (para CI/CD) |

### Paso 1: Crear Servidor en Hetzner

```
En Hetzner Cloud Console:
- Tipo: CX31 (Opcion A) o CCX33 (Opcion B1)
- OS: Ubuntu 22.04 LTS
- Location: Falkenstein (Alemania) o Ashburn (US)
- SSH Key: agregar tu llave publica
- Firewall: crear con reglas 22, 80, 443 TCP inbound
```

### Paso 2: Configurar DNS

```
En Cloudflare:
- Agregar dominio (ej: dentalos.co)
- A record: app.dentalos.co → IP del servidor
- Proxy status: DNS Only (gris, no naranja) — para que certbot funcione
```

### Paso 3: Setup Inicial del Servidor

```bash
# Desde tu maquina local:
ssh root@YOUR_SERVER_IP

# Clonar repo
git clone https://github.com/tu-org/dentalos.git /opt/dentalos
cd /opt/dentalos

# Ejecutar setup (instala Docker, genera secrets, configura firewall)
chmod +x scripts/deploy/setup-server.sh
./scripts/deploy/setup-server.sh
```

### Paso 4: Configurar Secrets

```bash
# Editar .env con valores reales
nano /opt/dentalos/.env

# Llenar estos CHANGE_ME:
# - OPENAI_API_KEY=sk-...        (solo Opcion A)
# - ANTHROPIC_API_KEY=sk-ant-... (siempre necesario)
# - SENDGRID_API_KEY=SG....
# - SENTRY_DSN=https://...@sentry.io/...
```

### Paso 5: SSL / TLS

```bash
# Verificar que DNS apunta al servidor
dig app.dentalos.co    # debe retornar la IP del servidor

# Obtener certificado SSL
sudo certbot --nginx -d app.dentalos.co

# Verificar renovacion automatica
sudo certbot renew --dry-run
```

### Paso 6: Primer Despliegue

```bash
cd /opt/dentalos
chmod +x scripts/deploy/first-deploy.sh
./scripts/deploy/first-deploy.sh

# El script:
# - Build imagenes (~5-10 min la primera vez)
# - Levanta infra y espera healthchecks
# - Corre migraciones
# - Crea bucket MinIO
# - Levanta app
# - Seed datos iniciales
# - Imprime URLs y credenciales
```

### Paso 7: Verificacion

```bash
# Health check del API
curl https://app.dentalos.co/api/v1/health
# → {"status": "ok"}

# Verificar todos los contenedores
docker compose -f docker-compose.prod.yml ps
# → 7 servicios "Up (healthy)"

# Verificar worker
docker compose -f docker-compose.prod.yml logs worker --tail 20
# → "All workers started"

# Verificar headers de seguridad
curl -I https://app.dentalos.co/ | grep -E "Strict|X-Frame|X-Content"
# → Strict-Transport-Security: max-age=63072000
# → X-Frame-Options: SAMEORIGIN
# → X-Content-Type-Options: nosniff
```

### Paso 8: Configurar CI/CD

En GitHub → Settings → Secrets and variables → Actions:

| Secret | Valor |
|--------|-------|
| `DEPLOY_HOST` | IP del servidor Hetzner |
| `DEPLOY_USER` | root (o usuario deploy) |
| `DEPLOY_SSH_KEY` | Contenido de la llave SSH privada |

Despues de configurar estos secrets, cada push a `master` despliega automaticamente.

---

## 10. Seguridad

### Nivel de Red

- UFW firewall: solo puertos 22, 80, 443 abiertos
- Todos los servicios Docker en 127.0.0.1 (no accesibles desde internet)
- Nginx como unico punto de entrada publico
- TLS 1.2+ con Let's Encrypt (auto-renovacion via certbot timer)
- Rate limiting en /api/: 10 req/s por IP (burst 20)
- Cloudflare para DDoS protection y DNS

### Nivel de Aplicacion

- JWT RS256 con llaves RSA 2048-bit
- Access token: 15 min TTL (en memoria JS, no localStorage)
- Refresh token: 30 dias, HttpOnly cookie, hasheado SHA-256 en DB
- Passwords con bcrypt (12 rounds) + pepper
- CORS restringido al dominio de produccion
- Security headers (HSTS 2 anos preload, X-Frame-Options, nosniff, XSS-Protection)
- Input sanitization con bleach para rich text
- Regex validation para cedulas, telefonos, FDI, CIE-10, CUPS

### Nivel de Datos

- Schema-per-tenant: aislamiento total entre clinicas a nivel de base de datos
- Soft delete para datos clinicos (nunca hard delete — regulacion colombiana)
- S3 paths aislados por tenant: `/{tenant_id}/{patient_id}/{type}/{uuid}.ext`
- Never log PHI: nombres, cedulas, telefonos, notas clinicas, diagnosticos
- `.env` con permisos 600 (solo root)
- JWT keys con permisos 600

### Backups Recomendados

```bash
# Agregar al crontab del servidor (crontab -e):

# PostgreSQL backup diario a las 3 AM (UTC)
0 3 * * * docker exec dentalos-postgres-prod pg_dump -U dentalos dentalos | gzip > /opt/dentalos/backups/db-$(date +\%Y\%m\%d).sql.gz

# Retener ultimos 30 dias
0 4 * * * find /opt/dentalos/backups/ -name "db-*.sql.gz" -mtime +30 -delete

# MinIO backup semanal (domingos 4 AM)
0 4 * * 0 docker run --rm -v dentalos_minio_data:/data -v /opt/dentalos/backups:/backup alpine tar czf /backup/minio-$(date +\%Y\%m\%d).tar.gz /data
```

---

## 11. Monitoreo y Mantenimiento

### Monitoreo Activo

| Que monitorear | Como | Cuando alertar |
|----------------|------|----------------|
| API uptime | `curl /api/v1/health` cada 1 min | 3 fallos consecutivos |
| Frontend uptime | `curl /` cada 1 min | 3 fallos consecutivos |
| Errores de aplicacion | Sentry (backend + frontend) | Cualquier error nuevo |
| Espacio en disco | `df -h` via cron | > 80% uso |
| RAM por contenedor | `docker stats` | > 90% del limite |
| Queue depth (RabbitMQ) | Management API :15672 | > 100 mensajes > 5 min |
| Certificado SSL | certbot auto-renew | Si falla renovacion |
| Worker health | `docker compose logs worker` | Si se reinicia |

### Comandos de Mantenimiento Frecuentes

```bash
# Ver estado de todos los contenedores
docker compose -f docker-compose.prod.yml ps

# Ver logs en tiempo real de un servicio
docker compose -f docker-compose.prod.yml logs -f backend --tail 100
docker compose -f docker-compose.prod.yml logs -f worker --tail 50

# Reiniciar un servicio especifico
docker compose -f docker-compose.prod.yml restart backend

# Correr migraciones despues de una actualizacion
docker compose -f docker-compose.prod.yml exec backend \
  alembic -c alembic_public/alembic.ini upgrade head
docker compose -f docker-compose.prod.yml exec backend \
  alembic -c alembic_tenant/alembic.ini upgrade head

# Ver uso de recursos en tiempo real
docker stats

# Limpiar imagenes Docker viejas
docker image prune -f

# Backup manual de la base de datos
docker exec dentalos-postgres-prod pg_dump -U dentalos dentalos > backup_manual.sql
```

### Actualizaciones (manual, sin CI/CD)

```bash
cd /opt/dentalos
git pull origin master

# Rebuild y redeploy
docker compose -f docker-compose.prod.yml build --parallel
docker compose -f docker-compose.prod.yml up -d backend worker frontend

# Correr migraciones si hay nuevas
docker compose -f docker-compose.prod.yml exec backend \
  alembic -c alembic_tenant/alembic.ini upgrade head

# Verificar
curl http://localhost:8000/api/v1/health
```

### Rollback

```bash
# Antes de actualizar, guardar la imagen actual
docker tag dentalos-backend:latest dentalos-backend:previous

# Si algo falla despues del update:
docker tag dentalos-backend:previous dentalos-backend:latest
docker compose -f docker-compose.prod.yml up -d backend worker
```

---

## 12. Costos

### Opcion A: Todo API (recomendada para beta)

| Item | Costo/mes |
|------|----------|
| Hetzner CX31 (4 vCPU, 8 GB) | $15 |
| Dominio .co (anualizado) | ~$3 |
| IA APIs — Anthropic + OpenAI (1 clinica) | ~$3 |
| SendGrid (free tier: 100 emails/dia) | $0 |
| Sentry (free tier: 5K events/mes) | $0 |
| Cloudflare (free plan) | $0 |
| **Total** | **~$21/mes** |

### Opcion B1: IA Local CPU

| Item | Costo/mes |
|------|----------|
| Hetzner CCX33 (8 vCPU, 32 GB) | $57 |
| Dominio .co (anualizado) | ~$3 |
| IA APIs — solo Anthropic (3 features) | ~$0.50 |
| SendGrid, Sentry, Cloudflare | $0 |
| **Total** | **~$61/mes** |

### Opcion C1: GPU VPS Budget (Hostkey 1080 Ti)

| Item | Costo/mes |
|------|----------|
| Hostkey GPU VPS (1080 Ti, 32 GB RAM) | $76 |
| Hetzner CX31 (app stack) | $15 |
| Dominio .co | ~$3 |
| IA APIs — solo Anthropic (3 features) | ~$0.50 |
| SendGrid, Sentry, Cloudflare | $0 |
| **Total** | **~$95/mes** |

### Opcion C2: GPU VPS Sweet Spot (Hostkey A4000)

| Item | Costo/mes |
|------|----------|
| Hostkey GPU VPS (A4000, 32 GB RAM) | $136 |
| Dominio .co | ~$3 |
| IA APIs — solo Anthropic (3 features) | ~$0.50 |
| SendGrid, Sentry, Cloudflare | $0 |
| **Total** | **~$140/mes** |

> Opcion: correr todo en el GPU VPS ($136/mes, solo 1 servidor) o separar app en CX31 + GPU VPS ($136+$15 = $151/mes, 2 servidores con redundancia).

### Opcion C3: GPU VPS Todo en Uno (Hetzner GEX44)

| Item | Costo/mes |
|------|----------|
| Hetzner GEX44 (RTX 4000 Ada, 64 GB RAM) | ~$184 (€170, sube a €212 en abril 2026) |
| Dominio .co | ~$3 |
| IA APIs — solo Anthropic (3 features) | ~$0.50 |
| SendGrid, Sentry, Cloudflare | $0 |
| **Total** | **~$188/mes** (sube a ~$233/mes post-abril) |

### Costos de APIs Externas (aplica a todas las opciones)

| Servicio | Costo | Cuando se activa |
|----------|-------|-----------------|
| Anthropic (Claude) | ~$2-3/mes por clinica | Treatment Advisor, Reports, Chatbot |
| OpenAI (Whisper) | ~$0.15/mes por clinica | Solo Opcion A |
| Twilio (SMS + VoIP) | ~$20-40/mes | Recordatorios, llamadas |
| WhatsApp Cloud API | Gratis 1000 msg/mes | Chat bidireccional |
| SendGrid | Gratis 100/dia | Emails transaccionales |
| Daily.co (video) | Gratis 2000 min/mes | Telemedicina |
| Nequi/Daviplata | Comision por tx | Pagos moviles |
| Mercado Pago | Comision por tx | Pagos con tarjeta |

### Proyeccion de Costos por Escala

| Clinicas | Opcion A (API) | Opcion B1 (CPU) | Opcion C2 (A4000) | Opcion C3 (GEX44) |
|----------|---------------|----------------|-------------------|-------------------|
| 1 | $21/mes | $61/mes | $140/mes | $188/mes |
| 5 | $28/mes | $63/mes | $141/mes | $189/mes |
| 20 | $65/mes | $68/mes | $143/mes | $190/mes |
| 50 | $140/mes | $80/mes | $150/mes | $197/mes |
| 100 | $270/mes | $100/mes | $160/mes | $207/mes |

> A partir de ~50 clinicas, B1 es mas barata que A. A ~100 clinicas, C2 y C3 tambien se vuelven competitivas vs A, pero con mucho mejor rendimiento y privacidad.

---

## 13. Decision y Recomendacion

### Para el Beta Inmediato (1 clinica, 2026)

**Recomendacion: Opcion A (IA via API)**

| Factor | Justificacion |
|--------|--------------|
| Costo | $21/mes vs $61-188/mes — 3-9x mas barato |
| Simplicidad | Cero operaciones de IA que mantener |
| Riesgo | Menor superficie de error y fallo |
| Precision | Los mejores modelos disponibles (Claude Sonnet/Haiku, Whisper Large v3) |
| Velocidad | 2-8s latencia total de voz vs 15-30s (CPU local) |
| Tiempo de setup | 2-3 horas vs 4-6 horas (con Ollama/GPU) |

### Cuando Migrar a Opcion B o C

Escenarios que justificarian la migracion:

1. **Requisito regulatorio formal:** la Superintendencia de Salud o la SIC exigen que datos clinicos de audio no salgan del servidor → **Opcion C** (GPU VPS, rendimiento bueno) o **Opcion B1** (CPU, mas barato pero lento)
2. **Volumen > $50/mes en APIs de voz:** ~50+ clinicas activas usando dictado → **B1 o C** segun presupuesto
3. **Clinicas en zonas rurales:** donde internet es inestable y la voz necesita funcionar offline → **C** (GPU, rapido) preferible a B1 (CPU, lento)
4. **Experiencia de usuario critica:** si los doctores se quejan de latencia de 15-30s en B1 → **Upgrade a C** ($136-184/mes, 1-4s)

### Plan de Migracion Gradual

```
Mes 1-3 (beta):
  → Opcion A ($21/mes)
  → Validar producto, recolectar metricas de uso de IA
  → Medir: cuantos dictados/mes, latencia promedio, precision percibida

Mes 4-6 (si hay requisito regulatorio):
  RUTA BARATA:
  → Upgrade a Opcion B1: CCX33 ($57/mes, CPU, Qwen 7B)
  → Pro: barato. Contra: lento (15-30s por dictado)

  RUTA RAPIDA:
  → Upgrade a Opcion C: Hostkey A4000 ($136/mes) o Hetzner GEX44 ($184/mes)
  → Pro: rapido (1-4s), mejor precision (Qwen 14B). Contra: 7-10x costo de A

Mes 6+ (si se necesita TODO local):
  → Modificar ai_claude_client.py para soportar Ollama como backend
  → Usar modelo grande (Qwen 32B o Llama 70B) para Treatment Advisor
  → Requiere GPU VPS con >=24 GB VRAM (Hostkey RTX 4090, $272/mes)
  → Evaluar si el costo se justifica vs las APIs
```

### La Transicion es Trivial

Cambiar de API a local es **1 linea en `.env`** para STT y NLP:

```env
# De API (Opcion A)...
VOICE_STT_PROVIDER=openai
VOICE_NLP_PROVIDER=anthropic

# ...a local (Opcion B o C):
VOICE_STT_PROVIDER=local
VOICE_NLP_PROVIDER=local

# Diferencia entre B y C: en C agregar WHISPER_DEVICE=cuda
WHISPER_DEVICE=cuda              # Solo Opcion C (GPU)
OLLAMA_MODEL=qwen2.5:14b         # 14b viable en GPU, usar 7b en CPU (Opcion B)
```

El codigo ya soporta ambos modos. No hay que cambiar nada en la aplicacion. Solo agregar el contenedor de Ollama, instalar NVIDIA Container Toolkit (Opcion C), y descargar el modelo.

### Resumen Final para el Socio

| Pregunta | Respuesta |
|----------|-----------|
| **Cuanto cuesta arrancar?** | ~$21 USD/mes (Opcion A) |
| **Cuanto tiempo para estar live?** | 2-3 dias de trabajo tecnico |
| **Se necesita GPU?** | No para beta. La IA son llamadas API |
| **Y si quiero IA local barata?** | Opcion B1: $57/mes (CPU), funciona pero lento (15-30s) |
| **Y si quiero IA local rapida?** | Opcion C: $136-184/mes (GPU VPS), rapido (1-4s), privacidad total |
| **Mejores proveedores GPU?** | Hostkey ($76-272/mes), Hetzner GEX44 ($184/mes), DatabaseMart ($179/mes) |
| **Que riesgo hay?** | Codigo completo (97%), 13 integraciones con mocks, multi-tenancy desde dia 1 |
| **Puedo migrar a GPU despues?** | Si, es 1 linea de config + instalar NVIDIA toolkit. El codigo ya lo soporta |

---

> Documento generado: 2026-03-11 | Actualizado: 2026-03-11
> Aplica a: DentalOS MVP v1.0
> Servidor objetivo: Hetzner CX31 (Opcion A) | CCX33 (Opcion B1) | GPU VPS Hostkey/GEX44 (Opcion C)
