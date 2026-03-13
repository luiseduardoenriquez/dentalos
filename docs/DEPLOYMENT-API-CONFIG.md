# DentalOS — Configuracion de APIs para Produccion (Estrategia A)

> **Estrategia A:** Todo en 1 servidor Hetzner CX31 (4 vCPU, 8 GB RAM, 80 GB SSD, ~$15/mes).
> La IA se resuelve con llamadas API a Anthropic (Claude) y OpenAI (Whisper).
> No se necesita GPU ni modelos locales.

---

## Variables auto-generadas por `setup-server.sh`

El script `scripts/deploy/setup-server.sh` genera estos secretos automaticamente.
**No necesitas configurarlos manualmente.**

| Variable | Que genera |
|----------|------------|
| `POSTGRES_PASSWORD` | Password de PostgreSQL (48 hex chars) |
| `REDIS_PASSWORD` | Password de Redis (48 hex chars) |
| `RABBITMQ_PASSWORD` | Password de RabbitMQ (48 hex chars) |
| `MINIO_ROOT_PASSWORD` / `S3_SECRET_KEY` | Password de MinIO — storage de archivos (48 hex chars) |
| `SECRET_KEY` | Llave maestra de la app (64 hex chars) |
| `PASSWORD_PEPPER` | Pepper para bcrypt (32 hex chars) |
| `PROMETHEUS_TOKEN` | Token bearer del endpoint `/metrics` (48 hex chars) |
| JWT keys | `private.pem` + `public.pem` — RSA 2048-bit en `/opt/dentalos/keys/` |

---

## APIs obligatorias para el MVP beta

Estas **4 variables** son las que debes llenar en `/opt/dentalos/.env` (reemplazan los `CHANGE_ME`).

### 1. OpenAI — Whisper STT (voz a texto)

| Variable | Valor |
|----------|-------|
| `OPENAI_API_KEY` | `sk-...` |

- **Para que se usa:** Transcripcion de audio a texto (Voice-to-Odontogram, dictado clinico)
- **Donde obtenerla:** [platform.openai.com](https://platform.openai.com) → API Keys
- **Costo estimado:** ~$2-5/mes (1 clinica, 2-3 doctores)
- **Modelo usado:** Whisper Large v3 (via API)

### 2. Anthropic — Claude AI

| Variable | Valor |
|----------|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` |

- **Para que se usa:** Chatbot, Treatment Advisor, AI Reports, NLP de voz
- **Donde obtenerla:** [console.anthropic.com](https://console.anthropic.com) → API Keys
- **Costo estimado:** ~$3-8/mes (1 clinica, 2-3 doctores)
- **Modelos configurados:**
  - `ANTHROPIC_MODEL=claude-haiku-4-5-20251001` — chatbot, NLP de voz (rapido, barato)
  - `ANTHROPIC_MODEL_TREATMENT=claude-sonnet-4-5-20250514` — treatment advisor, AI reports (mas capaz)

### 3. SendGrid — Emails transaccionales

| Variable | Valor |
|----------|-------|
| `SENDGRID_API_KEY` | `SG....` |
| `SENDGRID_FROM_EMAIL` | `noreply@dentalos.co` |
| `SENDGRID_FROM_NAME` | `DentalOS` |

- **Para que se usa:** Verificacion de cuenta, reset de password, notificaciones por email, recordatorios de cita
- **Donde obtenerla:** [app.sendgrid.com](https://app.sendgrid.com) → Settings → API Keys
- **Costo:** Plan gratuito = 100 emails/dia (suficiente para beta)
- **Prerequisito:** Verificar el dominio sender en SendGrid (DNS records)

### 4. Sentry — Monitoreo de errores

| Variable | Valor |
|----------|-------|
| `SENTRY_DSN` | `https://...@sentry.io/...` |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.1` |
| `SENTRY_ENVIRONMENT` | `production` |

- **Para que se usa:** Captura automatica de errores y excepciones en backend y frontend
- **Donde obtenerla:** [sentry.io](https://sentry.io) → Create Project → Settings → Client Keys (DSN)
- **Costo:** Plan gratuito = 5K errores/mes (suficiente para beta)

> **Nota:** La app funciona sin SendGrid y Sentry, pero no enviara emails y no reportara errores.
> Las unicas 2 APIs **criticas** para que la IA funcione son `OPENAI_API_KEY` y `ANTHROPIC_API_KEY`.

---

## APIs opcionales (activar segun necesidad)

Estas APIs habilitan features adicionales. Se pueden configurar despues del lanzamiento.

### Comunicaciones

| Variable(s) | Servicio | Feature | Prioridad |
|-------------|----------|---------|-----------|
| `WHATSAPP_ACCESS_TOKEN` | Meta Cloud API | Chat WhatsApp bidireccional | Alta |
| `WHATSAPP_APP_SECRET` | Meta Cloud API | Verificacion de webhooks | Alta |
| `WHATSAPP_PHONE_NUMBER_ID` | Meta Cloud API | Numero de envio | Alta |
| `TWILIO_ACCOUNT_SID` | Twilio | SMS transaccional | Media |
| `TWILIO_AUTH_TOKEN` | Twilio | Autenticacion SMS | Media |
| `TWILIO_FROM_NUMBER` | Twilio | Numero de envio SMS | Media |

- **WhatsApp:** [developers.facebook.com](https://developers.facebook.com) → WhatsApp Business API
- **Twilio:** [twilio.com/console](https://www.twilio.com/console)

### Pagos

| Variable(s) | Servicio | Feature | Prioridad |
|-------------|----------|---------|-----------|
| `NEQUI_CLIENT_ID` | Nequi | Pagos con billetera Nequi | Cuando actives pagos |
| `NEQUI_CLIENT_SECRET` | Nequi | Autenticacion | Cuando actives pagos |
| `NEQUI_API_KEY` | Nequi | API key | Cuando actives pagos |
| `NEQUI_WEBHOOK_SECRET` | Nequi | Verificacion webhooks | Cuando actives pagos |
| `DAVIPLATA_CLIENT_ID` | Daviplata | Pagos con Daviplata | Cuando actives pagos |
| `DAVIPLATA_CLIENT_SECRET` | Daviplata | Autenticacion | Cuando actives pagos |
| `DAVIPLATA_WEBHOOK_SECRET` | Daviplata | Verificacion webhooks | Cuando actives pagos |
| `MERCADOPAGO_ACCESS_TOKEN` | Mercado Pago | Pagos online (tarjeta, PSE) | Cuando actives pagos |
| `MERCADOPAGO_WEBHOOK_SECRET` | Mercado Pago | Verificacion webhooks | Cuando actives pagos |

- **Nequi:** Portal de desarrolladores Nequi (sandbox → produccion)
- **Daviplata:** API empresarial Daviplata
- **Mercado Pago:** [mercadopago.com.co/developers](https://www.mercadopago.com.co/developers)

### Telemedicina

| Variable(s) | Servicio | Feature | Prioridad |
|-------------|----------|---------|-----------|
| `DAILY_API_KEY` | Daily.co | Videollamadas (telemedicina) | Baja (add-on) |

- **Daily.co:** [dashboard.daily.co](https://dashboard.daily.co) → Developers → API Keys

### VoIP

| Variable(s) | Servicio | Feature | Prioridad |
|-------------|----------|---------|-----------|
| `TWILIO_VOICE_NUMBER` | Twilio Voice | Llamadas VoIP + screen pop | Baja |
| `TWILIO_VOICE_WEBHOOK_URL` | Twilio Voice | URL del webhook | Baja |

### Integraciones gobierno Colombia

| Variable(s) | Servicio | Feature | Prioridad |
|-------------|----------|---------|-----------|
| `ADRES_API_KEY` | ADRES/BDUA | Verificacion cobertura EPS | Cuando integres seguros |
| `RETHUS_APP_TOKEN` | RETHUS | Verificacion registro profesional | Baja |
| `MATIAS_CLIENT_ID` | MATIAS/DIAN | Facturacion electronica | Cuando necesites FE |
| `MATIAS_SECRET` | MATIAS/DIAN | Autenticacion | Cuando necesites FE |
| `EPS_CLAIMS_API_KEY` | EPS | Radicacion de cuentas medicas | Cuando integres seguros |

### Otras

| Variable(s) | Servicio | Feature | Prioridad |
|-------------|----------|---------|-----------|
| `GOOGLE_CLIENT_ID` | Google | Sync Google Calendar | Baja |
| `GOOGLE_CLIENT_SECRET` | Google | Autenticacion OAuth | Baja |
| `EXCHANGE_RATE_API_KEY` | Banco de la Republica | Tasa de cambio COP/USD/EUR | Baja |
| `ADDI_API_KEY` | Addi | Financiacion para pacientes | Baja |
| `SISTECREDITO_API_KEY` | Sistecredito | Financiacion para pacientes | Baja |
| `TELEGRAM_BOT_TOKEN` | Telegram | Alertas de monitoreo | Opcional |
| `TELEGRAM_CHAT_ID` | Telegram | Canal de alertas | Opcional |

---

## Configuracion de dominio y CORS

Estas variables **no son API keys** pero debes ajustarlas a tu dominio real:

```bash
# En /opt/dentalos/.env
ALLOWED_HOSTS=app.dentalos.co
CORS_ORIGINS=https://app.dentalos.co
FRONTEND_URL=https://app.dentalos.co
SENDGRID_FROM_EMAIL=noreply@dentalos.co   # Debe estar verificado en SendGrid
```

---

## Flujo de despliegue completo

```
1. Provisionar CX31 en Hetzner (Ubuntu 22.04)
   └─ 4 vCPU, 8 GB RAM, 80 GB SSD (~$15/mes)

2. Ejecutar setup-server.sh
   └─ Instala Docker, genera passwords/JWT keys, configura firewall + Nginx

3. Editar /opt/dentalos/.env
   └─ Llenar los 4 CHANGE_ME obligatorios:
      ├─ OPENAI_API_KEY
      ├─ ANTHROPIC_API_KEY
      ├─ SENDGRID_API_KEY
      └─ SENTRY_DSN

4. Apuntar DNS a la IP del servidor
   └─ En Cloudflare: A record → app.dentalos.co → IP_SERVIDOR

5. Obtener certificado TLS
   └─ sudo certbot --nginx -d app.dentalos.co

6. Ejecutar first-deploy.sh
   └─ Build de imagenes, migraciones de DB, arranque de servicios
```

---

## Costo mensual estimado (Estrategia A — 1 clinica beta)

| Concepto | Costo/mes |
|----------|-----------|
| Hetzner CX31 | ~$15 |
| OpenAI Whisper API | ~$2-5 |
| Anthropic Claude API | ~$3-8 |
| SendGrid | $0 (plan gratuito) |
| Sentry | $0 (plan gratuito) |
| Cloudflare | $0 (plan gratuito) |
| **Total estimado** | **~$20-28/mes** |
