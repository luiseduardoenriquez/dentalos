# AI Contact Center (Unified) Spec

---

## Overview

**Feature:** AI-05 — A single AI agent that handles inbound and outbound patient communication across WhatsApp, VoIP phone calls, and the web chat widget. The agent understands appointment scheduling/rescheduling/cancellation, payment reminders, general clinic questions, and proactive outreach (confirmations, recalls, payment follow-ups). When confidence is low or the situation is complex, the agent escalates to a human receptionist with full context.

**Domain:** ai / contact-center

**Priority:** High (Tier 2 — differentiation vs Dentalink)

**Dependencies:** chatbot (S29-30), whatsapp-chat (S27-28), voip/call-log (S31-32), appointments, billing/invoices, patients, notifications, feature-flags, caching, queue

**Feature Flag:** `ai_contact_center`

**Add-on Gating:** $25/location/mo (separate from existing AI add-ons)

**Model:** Claude Haiku (intent classification + response generation, ~1K input + ~300 output tokens per turn)

**Target Latency:** < 2 seconds per turn (WhatsApp/web), < 1 second for VoIP (real-time voice)

---

## Architecture

The AI Contact Center is an orchestration layer that unifies three existing channel systems into a single AI-powered agent with shared context.

```
                    ┌───────────────────────────────────────────────────────┐
                    │              AI Contact Center Orchestrator            │
                    │           contact_center_service.py                    │
                    │                                                       │
                    │  ┌─────────────┐  ┌──────────┐  ┌──────────────────┐ │
                    │  │ Intent      │  │ Context  │  │ Proactive        │ │
                    │  │ Router      │  │ Manager  │  │ Campaign Engine  │ │
                    │  │ (expanded)  │  │ (Redis)  │  │ (RabbitMQ)       │ │
                    │  └──────┬──────┘  └────┬─────┘  └────────┬─────────┘ │
                    │         │              │                  │           │
                    │  ┌──────┴──────────────┴──────────────────┴─────────┐ │
                    │  │           Unified Conversation Manager            │ │
                    │  │  contact_center_conversations table               │ │
                    │  │  + cross-channel patient context in Redis          │ │
                    │  └──────────────────────────────────────────────────┘ │
                    └──────────┬─────────────────┬──────────────┬───────────┘
                               │                 │              │
                    ┌──────────▼───┐  ┌──────────▼───┐  ┌──────▼──────────┐
                    │  WhatsApp    │  │  VoIP        │  │  Web Chat       │
                    │  Adapter     │  │  Adapter     │  │  Adapter        │
                    │              │  │              │  │                  │
                    │  whatsapp_   │  │  twilio_     │  │  chatbot_       │
                    │  chat_       │  │  voice/      │  │  widget/        │
                    │  service.py  │  │  call_log_   │  │  router.py      │
                    │              │  │  service.py  │  │                  │
                    └──────────────┘  └──────────────┘  └──────────────────┘
                               │                 │              │
                    ┌──────────▼─────────────────▼──────────────▼───────────┐
                    │                  Existing DentalOS Services            │
                    │  appointment_service  │  invoice_service               │
                    │  patient_service      │  notification_service          │
                    └───────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Orchestration, not replacement.** The contact center wraps existing chatbot, WhatsApp, and VoIP services. Channel-specific logic (WhatsApp 24h window, Twilio TwiML, web widget auth) stays in channel adapters. The orchestrator handles intent routing, context management, and action execution.

2. **Shared context via Redis.** A patient's conversation context (recent intents, extracted entities, conversation summaries) is cached in Redis keyed by patient_id, enabling seamless cross-channel continuity. If a patient calls about an appointment they discussed on WhatsApp, the AI already knows.

3. **Proactive outreach via RabbitMQ.** Campaign scheduling (appointment confirmations, recall reminders, payment follow-ups) is managed through the existing `notifications` queue with a new `contact_center.*` job type prefix.

4. **Human escalation with SSE.** When the AI escalates, receptionists are notified in real-time via SSE on the agent dashboard. Full conversation history and context transfer to the human agent.

---

## Intent Taxonomy

The contact center expands the current 8 chatbot intents to 16, organized into categories.

### Appointment Intents

| Intent | Description | Auto-actionable | Example |
|--------|-------------|-----------------|---------|
| `schedule` | Book a new appointment | Yes — check availability, create appointment | "Quiero agendar una cita para limpieza" |
| `reschedule` | Change date/time of existing appointment | Yes — find appointment, show alternatives | "Necesito cambiar mi cita del viernes" |
| `cancel` | Cancel an existing appointment | Yes — find and cancel, apply cancellation policy | "Quiero cancelar mi cita" |
| `confirm` | Confirm an upcoming appointment | Yes — update appointment status | "Si, confirmo mi cita de manana" |
| `availability` | Ask about available times (no commitment) | Yes — query slots | "Que horarios tienen disponibles?" |

### Billing Intents

| Intent | Description | Auto-actionable | Example |
|--------|-------------|-----------------|---------|
| `payment_status` | Ask about outstanding balance or invoice status | Yes — query invoices | "Cuanto debo?" |
| `payment_method` | Ask about accepted payment methods | Yes — from config | "Aceptan Nequi?" |
| `payment_plan` | Ask about financing or payment plans | Partial — show options, escalate for setup | "Puedo pagar en cuotas?" |

### Information Intents

| Intent | Description | Auto-actionable | Example |
|--------|-------------|-----------------|---------|
| `faq` | General question about services, procedures, or prices | Yes — FAQ matching | "Cuanto cuesta una corona?" |
| `hours` | Business hours inquiry | Yes — from config | "A que hora abren los sabados?" |
| `location` | Address or directions inquiry | Yes — from config | "Donde queda la clinica?" |
| `doctor_info` | Ask about a specific doctor or their availability | Yes — from staff directory | "Que doctores atienden ortodoncia?" |

### Escalation Intents

| Intent | Description | Auto-actionable | Example |
|--------|-------------|-----------------|---------|
| `emergency` | Dental emergency or urgent pain | No — immediate escalation | "Me duele mucho una muela, estoy sangrando" |
| `complaint` | Patient complaint or dissatisfaction | No — escalation with context | "No estoy satisfecho con el tratamiento" |
| `human` | Explicit request to speak with a person | No — immediate escalation | "Quiero hablar con alguien de la clinica" |
| `other` | Unclassifiable intent | Conditional — escalate if confidence < 0.5 | Anything else |

### Entity Extraction

For all intents, the AI extracts available entities:

```json
{
  "date": "2026-04-15",
  "time": "10:00",
  "doctor": "Dra. Martinez",
  "procedure": "limpieza",
  "appointment_id": null,
  "amount": null,
  "invoice_number": null
}
```

---

## Channel Adapters

Each channel adapter translates between the channel-specific protocol and the unified orchestrator interface.

### 3.1 WhatsApp Adapter

**Inbound flow:**
1. Meta webhook delivers inbound message to `POST /api/v1/webhooks/whatsapp`
2. Existing `whatsapp_chat_service` creates/updates `WhatsAppConversation` and `WhatsAppMessage`
3. If `ai_contact_center` feature flag is enabled, the webhook handler passes the message to `contact_center_service.handle_inbound()`
4. Orchestrator processes intent, executes actions, returns response text
5. Adapter sends response via WhatsApp Business API (respecting 24h session window)

**Outbound flow (proactive):**
1. Campaign engine publishes `contact_center.whatsapp.outbound` to RabbitMQ
2. Worker sends WhatsApp template message (pre-approved by Meta)
3. If patient replies, inbound flow activates with campaign context

**24h window handling:**
- Within 24h of last patient message: free-form session message
- Outside 24h window: must use pre-approved template message
- Templates managed via existing WhatsApp template admin

**Adapter interface:**
```python
class WhatsAppChannelAdapter:
    async def send_response(self, phone_number: str, message: str, tenant_id: str) -> bool
    async def send_template(self, phone_number: str, template_name: str, params: dict, tenant_id: str) -> bool
    async def get_session_status(self, phone_number: str, tenant_id: str) -> str  # "active" | "expired"
```

### 3.2 VoIP Adapter

**Inbound call flow:**
1. Twilio webhook delivers call to `POST /api/v1/webhooks/twilio/voice`
2. Existing `call_log_service` creates `CallLog` entry, performs patient matching
3. If `ai_contact_center` enabled, TwiML response routes to AI agent:
   - `<Gather>` with speech recognition collects patient utterance
   - Transcribed text sent to `contact_center_service.handle_inbound()`
   - Response text converted to speech via `<Say>` (Twilio TTS, voice: `Polly.Mia` for Latin American Spanish)
4. Conversation continues in gather-respond loop
5. AI can transfer to human via `<Dial>` when escalating

**Outbound call flow (proactive):**
1. Campaign engine publishes `contact_center.voip.outbound` to RabbitMQ
2. Worker initiates outbound call via Twilio REST API
3. When patient answers, AI agent greets with campaign context (e.g., appointment confirmation)
4. Call recorded in `CallLog` with `direction='outbound'`

**Adapter interface:**
```python
class VoIPChannelAdapter:
    def generate_ai_greeting_twiml(self, greeting: str, gather_url: str) -> str
    def generate_ai_response_twiml(self, response: str, gather_url: str) -> str
    def generate_transfer_twiml(self, staff_phone: str) -> str
    async def initiate_outbound_call(self, phone_number: str, greeting: str, tenant_id: str) -> str  # returns call_sid
```

### 3.3 Web Chat Adapter

**Flow:**
1. Patient opens web chat widget on clinic website or patient portal
2. Existing `chatbot_widget_router` handles WebSocket/polling connection
3. If `ai_contact_center` enabled, messages route to `contact_center_service.handle_inbound()` instead of `chatbot_service.handle_message()`
4. Response returned through the widget channel

**Authentication:**
- Anonymous visitors: no patient_id, limited to information intents
- Portal-authenticated patients: full patient_id context, can schedule/reschedule/check balance

**Adapter interface:**
```python
class WebChatChannelAdapter:
    async def send_response(self, conversation_id: uuid.UUID, message: str) -> bool
    async def identify_patient(self, conversation_id: uuid.UUID) -> uuid.UUID | None
```

---

## Conversation Context Management

### 4.1 Redis Context Store

Patient conversation context is stored in Redis for cross-channel continuity.

**Key:** `dentalos:{tid}:contact_center:context:{patient_id}`
**TTL:** 24 hours (refreshed on each interaction)

```json
{
  "patient_id": "uuid",
  "patient_name": "Maria Garcia",
  "last_channel": "whatsapp",
  "last_interaction_at": "2026-04-15T10:30:00Z",
  "active_conversation_id": "uuid",
  "pending_action": {
    "type": "schedule",
    "step": "confirm_time",
    "data": {
      "date": "2026-04-18",
      "time": "10:00",
      "doctor_id": "uuid",
      "procedure": "limpieza"
    }
  },
  "recent_intents": [
    {"intent": "availability", "channel": "whatsapp", "at": "2026-04-15T10:28:00Z"},
    {"intent": "schedule", "channel": "whatsapp", "at": "2026-04-15T10:30:00Z"}
  ],
  "upcoming_appointments": [
    {"id": "uuid", "date": "2026-04-18", "time": "10:00", "procedure": "limpieza"}
  ],
  "outstanding_balance_cents": 150000,
  "conversation_summary": "Paciente pregunto por disponibilidad para limpieza. Eligio viernes 18 a las 10am con Dra. Martinez."
}
```

### 4.2 Multi-Turn State Machine

For actionable intents (scheduling, rescheduling, cancellation), the orchestrator maintains a multi-turn state machine:

**Scheduling State Machine:**
```
start → ask_procedure → ask_date → show_slots → confirm → execute → done
                                       ↑            │
                                       └── reject ───┘
```

**Rescheduling State Machine:**
```
start → identify_appointment → ask_new_date → show_slots → confirm → execute → done
```

**Cancellation State Machine:**
```
start → identify_appointment → confirm_cancel → execute → done
```

State is stored in `pending_action` within the Redis context. If the patient switches channels mid-flow (e.g., starts on WhatsApp, continues on web chat), the state machine resumes from where they left off.

### 4.3 Patient Identification

The orchestrator resolves patient identity across channels:

| Channel | Identification Method | Fallback |
|---------|----------------------|----------|
| WhatsApp | Phone number match on `patients.phone` | Ask for cedula number |
| VoIP | Caller ID match on `patients.phone` via existing screen-pop | Ask for cedula number |
| Web Chat | Portal JWT (if logged in) | Ask for cedula number |

Once identified, the patient_id is linked to the `contact_center_conversations` record and the Redis context.

---

## API Endpoints

### 5.1 Configuration (Staff)

```
GET    /api/v1/contact-center/config
PUT    /api/v1/contact-center/config
```

**Auth:** JWT (clinic_owner, receptionist)

**GET response:**
```json
{
  "enabled": true,
  "channels": {
    "whatsapp": {"enabled": true, "auto_respond": true},
    "voip": {"enabled": true, "auto_respond": true, "max_call_duration_seconds": 300},
    "web_chat": {"enabled": true, "auto_respond": true}
  },
  "ai_greeting": "Hola, soy el asistente virtual de {clinic_name}. Puedo ayudarle a agendar citas, consultar su saldo, o responder preguntas. En que puedo servirle?",
  "ai_voice_greeting": "Bienvenido a {clinic_name}. Soy un asistente virtual. Como puedo ayudarle hoy?",
  "escalation_message": "Entiendo. Le transfiero con un miembro de nuestro equipo. Por favor espere un momento.",
  "business_hours_text": "Lunes a viernes de 8:00 AM a 6:00 PM, sabados de 8:00 AM a 1:00 PM.",
  "outside_hours_message": "Gracias por comunicarse. Nuestro horario de atencion es {business_hours}. Le responderemos en cuanto abramos.",
  "max_ai_turns_before_escalation": 10,
  "confidence_threshold": 0.5,
  "auto_confirm_appointments": false,
  "proactive_campaigns_enabled": true,
  "faq_entries": [
    {"question": "Cuanto cuesta una limpieza?", "answer": "El valor de la limpieza dental es de $80.000 COP."}
  ]
}
```

**PUT request body:** partial update (same shape, only provided fields are merged).

### 5.2 Conversations (Staff)

```
GET    /api/v1/contact-center/conversations
GET    /api/v1/contact-center/conversations/{conversation_id}
POST   /api/v1/contact-center/conversations/{conversation_id}/escalate
POST   /api/v1/contact-center/conversations/{conversation_id}/resolve
POST   /api/v1/contact-center/conversations/{conversation_id}/take-over
POST   /api/v1/contact-center/conversations/{conversation_id}/messages
```

**Auth:** JWT (clinic_owner, receptionist, doctor)

**GET /conversations query params:**
- `?status=active|escalated|resolved|ai_handling` — filter by status
- `?channel=whatsapp|voip|web_chat` — filter by channel
- `?patient_id={uuid}` — filter by patient
- `?assigned_to={uuid}` — filter by assigned staff
- `?page=1&page_size=20` — pagination

**GET /conversations response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "channel": "whatsapp",
      "patient_id": "uuid",
      "patient_name": "Maria Garcia",
      "patient_phone": "+573001234567",
      "status": "ai_handling",
      "assigned_to": null,
      "last_intent": "schedule",
      "intent_confidence": 0.92,
      "message_count": 6,
      "started_at": "2026-04-15T10:28:00Z",
      "last_message_at": "2026-04-15T10:35:00Z",
      "resolved_at": null,
      "outcome": null,
      "ai_actions_taken": ["checked_availability", "created_appointment"]
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

**GET /conversations/{id} response:** Same as list item but with `messages` array included:
```json
{
  "id": "uuid",
  "channel": "whatsapp",
  "patient_id": "uuid",
  "status": "ai_handling",
  "messages": [
    {
      "id": "uuid",
      "role": "user",
      "content": "Quiero agendar una cita para limpieza",
      "intent": "schedule",
      "confidence_score": 0.92,
      "channel": "whatsapp",
      "created_at": "2026-04-15T10:28:00Z"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": "Con gusto. Para que fecha le gustaria agendar su limpieza dental?",
      "intent": "schedule",
      "confidence_score": null,
      "channel": "whatsapp",
      "created_at": "2026-04-15T10:28:02Z"
    }
  ],
  "context": {
    "pending_action": {"type": "schedule", "step": "ask_date"},
    "recent_intents": ["schedule"],
    "cross_channel_history": [
      {"channel": "voip", "summary": "Llamo hace 2 dias preguntando por ortodoncia", "at": "2026-04-13T14:00:00Z"}
    ]
  }
}
```

**POST /conversations/{id}/take-over:** Human staff takes over from AI. Sets `assigned_to` to current user, status to `human_handling`. AI stops auto-responding on this conversation.

```json
{
  "assigned_to": "uuid",
  "status": "human_handling"
}
```

**POST /conversations/{id}/messages:** Staff sends a manual message through the active channel.

Request:
```json
{
  "content": "Hola Maria, soy Ana de la clinica. En que puedo ayudarle?"
}
```

### 5.3 Inbound Message Handling (Internal/Webhook)

These are internal routes called by channel adapters, not exposed publicly.

```
POST   /api/v1/contact-center/inbound/whatsapp
POST   /api/v1/contact-center/inbound/voip
POST   /api/v1/contact-center/inbound/web-chat
```

**Common request body:**
```json
{
  "message": "Quiero agendar una cita",
  "patient_id": "uuid or null",
  "phone_number": "+573001234567",
  "channel_conversation_id": "uuid",
  "metadata": {}
}
```

**Common response:**
```json
{
  "conversation_id": "uuid",
  "response": "Con gusto. Para que fecha le gustaria agendar su cita?",
  "intent": "schedule",
  "confidence": 0.92,
  "escalated": false,
  "action_taken": null,
  "pending_action": {"type": "schedule", "step": "ask_date"}
}
```

### 5.4 Proactive Campaigns (Staff)

```
GET    /api/v1/contact-center/campaigns
POST   /api/v1/contact-center/campaigns
GET    /api/v1/contact-center/campaigns/{campaign_id}
PUT    /api/v1/contact-center/campaigns/{campaign_id}
POST   /api/v1/contact-center/campaigns/{campaign_id}/activate
POST   /api/v1/contact-center/campaigns/{campaign_id}/pause
DELETE /api/v1/contact-center/campaigns/{campaign_id}
```

**Auth:** JWT (clinic_owner, receptionist)

**Campaign types:**

| Type | Trigger | Channel | Description |
|------|---------|---------|-------------|
| `appointment_confirmation` | 24h before appointment | WhatsApp (preferred), SMS fallback | "Hola {name}, le recordamos su cita manana a las {time}. Responda SI para confirmar o NO para reprogramar." |
| `appointment_recall` | N days since last visit (configurable) | WhatsApp | "Hola {name}, han pasado {days} dias desde su ultima visita. Le gustaria agendar una cita de control?" |
| `payment_reminder` | Invoice overdue by N days | WhatsApp | "Hola {name}, tiene un saldo pendiente de {amount}. Puede pagar en linea o en su proxima visita." |
| `post_treatment_followup` | N days after specific procedure | WhatsApp | "Hola {name}, como se ha sentido despues de su {procedure}? Si tiene alguna molestia, no dude en contactarnos." |
| `birthday_greeting` | Patient birthday | WhatsApp | "Feliz cumpleanos {name}! De parte del equipo de {clinic_name}. Tiene un {discount}% de descuento en su proxima visita." |
| `custom` | Manual trigger or scheduled date | WhatsApp, VoIP | Custom message defined by staff |

**POST /campaigns request:**
```json
{
  "name": "Recordatorio de citas 24h",
  "type": "appointment_confirmation",
  "channel": "whatsapp",
  "template_name": "appointment_reminder_24h",
  "schedule": {
    "trigger": "before_appointment",
    "offset_hours": -24
  },
  "target_filter": {
    "appointment_status": ["confirmed", "pending"]
  },
  "message_template": "Hola {patient_name}, le recordamos su cita manana {appointment_date} a las {appointment_time} con {doctor_name}. Responda SI para confirmar.",
  "is_active": true
}
```

### 5.5 Analytics (Staff)

```
GET    /api/v1/contact-center/analytics/summary
GET    /api/v1/contact-center/analytics/conversations
GET    /api/v1/contact-center/analytics/intents
GET    /api/v1/contact-center/analytics/campaigns
```

**Auth:** JWT (clinic_owner, receptionist)

**GET /analytics/summary query params:** `?from=2026-04-01&to=2026-04-30`

**Response:**
```json
{
  "period": {"from": "2026-04-01", "to": "2026-04-30"},
  "total_conversations": 342,
  "by_channel": {
    "whatsapp": 210,
    "voip": 87,
    "web_chat": 45
  },
  "by_outcome": {
    "resolved_by_ai": 278,
    "escalated_to_human": 52,
    "abandoned": 12
  },
  "ai_resolution_rate": 0.81,
  "avg_response_time_ms": 1450,
  "avg_turns_per_conversation": 4.2,
  "appointments_scheduled_by_ai": 89,
  "appointments_rescheduled_by_ai": 23,
  "appointments_cancelled_by_ai": 14,
  "top_intents": [
    {"intent": "schedule", "count": 120, "pct": 0.35},
    {"intent": "faq", "count": 65, "pct": 0.19},
    {"intent": "payment_status", "count": 42, "pct": 0.12}
  ],
  "conversion_funnel": {
    "inquiry": 342,
    "appointment_created": 89,
    "appointment_confirmed": 78,
    "patient_showed_up": 71,
    "conversion_rate": 0.21
  },
  "proactive_campaigns": {
    "messages_sent": 456,
    "responses_received": 234,
    "response_rate": 0.51,
    "appointments_from_campaigns": 45
  },
  "estimated_cost_savings": {
    "hours_saved": 68.4,
    "equivalent_salary_cop": 1200000
  }
}
```

**GET /analytics/intents:** Breakdown of intent distribution with confidence averages, escalation rates per intent, and trends over time.

**GET /analytics/campaigns:** Per-campaign performance: sent, delivered, responded, converted, cost.

### 5.6 Real-Time Agent Dashboard (SSE)

```
GET    /api/v1/contact-center/stream
```

**Auth:** JWT (clinic_owner, receptionist)

Server-Sent Events stream for real-time monitoring. Backed by Redis pub/sub channel `dentalos:{tid}:contact_center:events`.

**Event types:**

| Event | Payload | Description |
|-------|---------|-------------|
| `new_conversation` | `{conversation_id, channel, patient_name}` | New inbound conversation started |
| `message_received` | `{conversation_id, role, content_preview}` | New message in any conversation |
| `escalation` | `{conversation_id, channel, patient_name, reason, intent}` | AI escalated to human — requires attention |
| `action_taken` | `{conversation_id, action, details}` | AI performed an action (scheduled appointment, etc.) |
| `conversation_resolved` | `{conversation_id, outcome}` | Conversation closed |
| `campaign_batch_sent` | `{campaign_id, count}` | Proactive campaign batch dispatched |

---

## Database Schema

### 6.1 New Table: `contact_center_conversations` (tenant schema)

This table is the unified conversation record that links to channel-specific conversations.

```sql
CREATE TABLE contact_center_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Patient link (nullable for unidentified callers)
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,

    -- Channel and channel-specific conversation links
    channel VARCHAR(20) NOT NULL,  -- CHECK: 'whatsapp', 'voip', 'web_chat'
    whatsapp_conversation_id UUID REFERENCES whatsapp_conversations(id) ON DELETE SET NULL,
    chatbot_conversation_id UUID REFERENCES chatbot_conversations(id) ON DELETE SET NULL,
    call_log_id UUID REFERENCES call_logs(id) ON DELETE SET NULL,

    -- Status lifecycle
    status VARCHAR(20) NOT NULL DEFAULT 'ai_handling',
    -- CHECK: 'ai_handling', 'human_handling', 'escalated', 'resolved', 'abandoned'

    -- Assignment
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    escalated_at TIMESTAMPTZ,
    escalation_reason VARCHAR(100),

    -- Outcome tracking
    outcome VARCHAR(30),
    -- CHECK: 'appointment_scheduled', 'appointment_rescheduled', 'appointment_cancelled',
    --        'question_answered', 'payment_info_given', 'escalated_resolved',
    --        'abandoned', 'other'
    ai_actions_taken JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Intent tracking
    last_intent VARCHAR(30),
    intent_confidence NUMERIC(3, 2),
    intent_history JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Proactive campaign link (null for inbound)
    campaign_id UUID REFERENCES contact_center_campaigns(id) ON DELETE SET NULL,

    -- Timestamps
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_message_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_cc_conversations_patient ON contact_center_conversations(patient_id);
CREATE INDEX idx_cc_conversations_status ON contact_center_conversations(status);
CREATE INDEX idx_cc_conversations_channel ON contact_center_conversations(channel);
CREATE INDEX idx_cc_conversations_started ON contact_center_conversations(started_at);
CREATE INDEX idx_cc_conversations_assigned ON contact_center_conversations(assigned_to);
CREATE INDEX idx_cc_conversations_campaign ON contact_center_conversations(campaign_id);

-- Constraints
ALTER TABLE contact_center_conversations
    ADD CONSTRAINT chk_cc_conversations_channel
    CHECK (channel IN ('whatsapp', 'voip', 'web_chat'));

ALTER TABLE contact_center_conversations
    ADD CONSTRAINT chk_cc_conversations_status
    CHECK (status IN ('ai_handling', 'human_handling', 'escalated', 'resolved', 'abandoned'));
```

### 6.2 New Table: `contact_center_messages` (tenant schema)

Unified message log across all channels. This is separate from channel-specific message tables to maintain a single ordered stream.

```sql
CREATE TABLE contact_center_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES contact_center_conversations(id) ON DELETE CASCADE,

    -- Message content
    role VARCHAR(20) NOT NULL,  -- CHECK: 'user', 'assistant', 'system', 'staff'
    content TEXT NOT NULL,

    -- Channel the message was sent/received on
    channel VARCHAR(20) NOT NULL,  -- CHECK: 'whatsapp', 'voip', 'web_chat'

    -- Intent classification (for user messages)
    intent VARCHAR(30),
    confidence_score NUMERIC(3, 2),
    entities JSONB,

    -- AI action taken in response (for assistant messages)
    action_taken JSONB,
    -- e.g., {"type": "appointment_created", "appointment_id": "uuid", "date": "2026-04-18"}

    -- Staff who sent (for staff role messages)
    sent_by UUID REFERENCES users(id) ON DELETE SET NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_cc_messages_conversation ON contact_center_messages(conversation_id, created_at);
CREATE INDEX idx_cc_messages_intent ON contact_center_messages(intent);
```

### 6.3 New Table: `contact_center_campaigns` (tenant schema)

Proactive outreach campaign definitions.

```sql
CREATE TABLE contact_center_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name VARCHAR(200) NOT NULL,
    type VARCHAR(30) NOT NULL,
    -- CHECK: 'appointment_confirmation', 'appointment_recall', 'payment_reminder',
    --        'post_treatment_followup', 'birthday_greeting', 'custom'

    channel VARCHAR(20) NOT NULL DEFAULT 'whatsapp',
    -- CHECK: 'whatsapp', 'voip', 'sms'

    -- Template
    template_name VARCHAR(100),  -- WhatsApp template name (Meta-approved)
    message_template TEXT NOT NULL,  -- Message with {placeholders}

    -- Scheduling
    schedule JSONB NOT NULL,
    -- e.g., {"trigger": "before_appointment", "offset_hours": -24}
    -- e.g., {"trigger": "days_since_last_visit", "days": 180}
    -- e.g., {"trigger": "invoice_overdue_days", "days": 7}

    -- Targeting
    target_filter JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT false,

    -- Stats (denormalized for dashboard performance)
    total_sent INTEGER NOT NULL DEFAULT 0,
    total_responses INTEGER NOT NULL DEFAULT 0,
    total_conversions INTEGER NOT NULL DEFAULT 0,

    -- Audit
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_cc_campaigns_type ON contact_center_campaigns(type);
CREATE INDEX idx_cc_campaigns_active ON contact_center_campaigns(is_active);

ALTER TABLE contact_center_campaigns
    ADD CONSTRAINT chk_cc_campaigns_type
    CHECK (type IN ('appointment_confirmation', 'appointment_recall', 'payment_reminder',
                    'post_treatment_followup', 'birthday_greeting', 'custom'));

ALTER TABLE contact_center_campaigns
    ADD CONSTRAINT chk_cc_campaigns_channel
    CHECK (channel IN ('whatsapp', 'voip', 'sms'));
```

### 6.4 New Table: `contact_center_campaign_logs` (tenant schema)

Individual outreach attempt records per campaign.

```sql
CREATE TABLE contact_center_campaign_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES contact_center_campaigns(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,

    -- Delivery
    channel VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- CHECK: 'pending', 'sent', 'delivered', 'responded', 'converted', 'failed'

    -- Outcome
    conversation_id UUID REFERENCES contact_center_conversations(id) ON DELETE SET NULL,
    response_received BOOLEAN NOT NULL DEFAULT false,
    converted BOOLEAN NOT NULL DEFAULT false,
    conversion_type VARCHAR(30),  -- 'appointment_confirmed', 'appointment_scheduled', 'payment_made'

    -- Error tracking
    error_message TEXT,

    sent_at TIMESTAMPTZ,
    responded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_cc_campaign_logs_campaign ON contact_center_campaign_logs(campaign_id, created_at);
CREATE INDEX idx_cc_campaign_logs_patient ON contact_center_campaign_logs(patient_id);
CREATE INDEX idx_cc_campaign_logs_status ON contact_center_campaign_logs(status);

ALTER TABLE contact_center_campaign_logs
    ADD CONSTRAINT chk_cc_campaign_logs_status
    CHECK (status IN ('pending', 'sent', 'delivered', 'responded', 'converted', 'failed'));
```

### 6.5 Extending Existing Tables

No modifications to existing `chatbot_conversations`, `whatsapp_conversations`, or `call_logs` tables. The contact center conversations table references them via foreign keys, preserving backward compatibility.

---

## Proactive Outreach Engine

### 7.1 Scheduler

A periodic RabbitMQ job (`contact_center.campaign.evaluate`) runs every 15 minutes on the `notifications` queue. For each active campaign:

1. **Query matching patients** based on campaign type and `target_filter`:
   - `appointment_confirmation`: Appointments in next 24h with status `confirmed` or `pending`, not already contacted
   - `appointment_recall`: Patients whose last appointment was N+ days ago, not already contacted in this campaign cycle
   - `payment_reminder`: Invoices overdue by N+ days, not already contacted
   - `post_treatment_followup`: Completed procedures N days ago, not already contacted
   - `birthday_greeting`: Patients with birthday = today, not already contacted
   - `custom`: Manual batch or scheduled date

2. **Create campaign_log entries** with status `pending`

3. **Publish individual outreach messages** to appropriate queue:
   - `contact_center.whatsapp.outbound` for WhatsApp
   - `contact_center.voip.outbound` for VoIP
   - `contact_center.sms.outbound` for SMS

### 7.2 Rate Limiting

- **WhatsApp:** Max 100 template messages per hour per phone number (Meta limit), plus internal limit of 500/day per tenant
- **VoIP:** Max 10 concurrent outbound calls per tenant, max 200/day
- **Overall:** Outbound messages throttled to avoid spam perception

### 7.3 Opt-Out Handling

- Patients can opt out of proactive messages by replying "NO" or "PARAR"
- Opt-out stored in `patients.communication_preferences` (JSONB)
- All campaigns check opt-out status before sending
- Opt-out list downloadable for compliance

---

## Human Escalation Flow

### 8.1 Automatic Escalation Triggers

The AI escalates to a human when any of the following conditions are met:

| Trigger | Condition | Priority |
|---------|-----------|----------|
| Low confidence | Confidence < `confidence_threshold` (default 0.5) for 2+ consecutive messages | Normal |
| Emergency intent | Intent classified as `emergency` | Urgent |
| Complaint intent | Intent classified as `complaint` | High |
| Human request | Intent classified as `human` or escalation keywords detected | Normal |
| Max turns exceeded | AI has responded `max_ai_turns_before_escalation` times without resolution | Normal |
| Action failure | AI attempted an action (e.g., schedule appointment) and it failed | High |
| Sensitive topic | Patient mentions legal, malpractice, insurance dispute | Urgent |

### 8.2 Escalation Process

1. AI sends escalation message to patient (configurable text)
2. Conversation status changes to `escalated`
3. SSE event `escalation` published to agent dashboard
4. If no staff responds within 5 minutes, push notification sent to receptionist(s)
5. If no staff responds within 15 minutes, notification escalated to clinic_owner
6. Staff clicks "Take Over" on dashboard to assume conversation
7. Full AI conversation history and context displayed to staff
8. Staff responds through the original channel (WhatsApp/VoIP/web)

### 8.3 Context Handoff

When a human takes over, they receive:
- Full message history (ordered, across channels if applicable)
- Patient record summary (name, phone, last visit, balance)
- AI's intent classification and confidence for each message
- Pending action state (e.g., "patient was in the middle of scheduling for Friday 10am")
- Cross-channel history summary
- Suggested response based on context

---

## Error Codes

Domain: `CONTACT_CENTER`

| Code | HTTP | Description |
|------|------|-------------|
| `CONTACT_CENTER_not_enabled` | 403 | Feature flag `ai_contact_center` is disabled for this tenant |
| `CONTACT_CENTER_addon_required` | 403 | Tenant does not have the AI Contact Center add-on |
| `CONTACT_CENTER_conversation_not_found` | 404 | Conversation UUID does not exist |
| `CONTACT_CENTER_conversation_not_active` | 409 | Cannot perform action on a resolved/abandoned conversation |
| `CONTACT_CENTER_escalation_failed` | 409 | Conversation is not in a state that allows escalation |
| `CONTACT_CENTER_takeover_failed` | 409 | Conversation is not escalated or is already assigned |
| `CONTACT_CENTER_channel_not_configured` | 400 | The requested channel is not configured for this tenant |
| `CONTACT_CENTER_patient_not_identified` | 400 | Cannot perform patient-specific action without identified patient |
| `CONTACT_CENTER_campaign_not_found` | 404 | Campaign UUID does not exist |
| `CONTACT_CENTER_campaign_invalid_schedule` | 422 | Campaign schedule configuration is invalid |
| `CONTACT_CENTER_campaign_already_active` | 409 | Campaign is already active |
| `CONTACT_CENTER_campaign_already_paused` | 409 | Campaign is already paused |
| `CONTACT_CENTER_rate_limited` | 429 | Too many messages from this patient/channel in a short time |
| `CONTACT_CENTER_action_failed` | 500 | AI attempted an action (e.g., create appointment) that failed |
| `CONTACT_CENTER_ai_unavailable` | 503 | Claude API is unavailable; fallthrough to escalation |

---

## Security and Privacy

### 10.1 PHI Rules

- **Never log** patient message content, names, phone numbers, or document numbers
- **Never cache** message content in Redis context — only summaries and structured data
- **AI prompts** use anonymized identifiers: patient referred to as "el paciente" in prompts, never by name
- **VoIP recordings** are NOT stored by default. If call recording is enabled (separate consent), recordings are stored in tenant-isolated S3 with signed URLs (15-min expiry)
- **Redis context** TTL is 24h maximum — no long-term PII in cache
- **Campaign logs** store patient_id (UUID) only, never PII fields

### 10.2 AI Safety

- AI responses are constrained to dental clinic operations — system prompt explicitly prohibits medical diagnoses, prescriptions, or clinical advice
- Emergency intent triggers immediate escalation, never AI self-handling
- AI cannot access or disclose other patients' information
- AI cannot modify clinical records (odontogram, diagnoses, evolution notes)
- AI can only create/modify appointments and check billing — never alter billing amounts

### 10.3 Consent

- Patients interacting via WhatsApp or VoIP are informed they are speaking with an AI agent at the start of every conversation
- Proactive outreach respects communication preferences and opt-out status
- First proactive message includes opt-out instructions: "Responda PARAR para no recibir mas mensajes."

### 10.4 Rate Limiting

- Inbound: Max 30 messages per patient per hour across all channels
- Outbound proactive: Max 3 campaign messages per patient per day
- AI API calls: Max 1000 Claude calls per tenant per hour (configurable)

### 10.5 Audit Trail

Every AI interaction logged in `audit_logs`:
- `action`: `contact_center.message_processed`, `contact_center.action_taken`, `contact_center.escalated`, `contact_center.campaign_sent`
- `details`: intent, confidence, action_type (no PHI)
- `user_id`: null for AI, staff UUID for human takeover

---

## Feature Flag Gating

### 11.1 Flag Configuration

```json
{
  "ai_contact_center": {
    "category": "ai",
    "default": false,
    "requires_addon": "ai_contact_center",
    "addon_price_cents": 2500,
    "addon_billing": "per_location_monthly"
  }
}
```

### 11.2 Activation Requirements

Before enabling `ai_contact_center`, the tenant must have:

1. **Active subscription** (Starter+ plan)
2. **AI Contact Center add-on** purchased ($25/location/mo)
3. **At least one channel configured:**
   - WhatsApp: WhatsApp Business API credentials in tenant settings
   - VoIP: Twilio credentials in tenant settings
   - Web Chat: always available (no external config needed)

### 11.3 Fallback When Disabled

When `ai_contact_center` is disabled:
- WhatsApp messages handled by existing `chatbot_service` (if Pro+ plan with chatbot enabled) or routed to staff inbox
- VoIP calls handled by existing `call_log_service` (screen pop, no AI)
- Web chat handled by existing `chatbot_widget_router`
- No proactive campaigns
- No cross-channel context

---

## Frontend

### 12.1 Agent Dashboard Page

**Route:** `/dashboard/contact-center`

**Layout:** Three-column layout (conversation list | active conversation | patient context panel)

**Left column — Conversation List:**
- Filterable by status (AI Handling, Escalated, Human Handling, Resolved)
- Filterable by channel (WhatsApp icon, phone icon, chat icon)
- Each item shows: patient name, channel icon, last message preview, time, status badge
- Escalated conversations highlighted with red badge and pulse animation
- Real-time updates via SSE

**Center column — Active Conversation:**
- Chat-style message view with role indicators (AI bot, patient, staff)
- Channel indicator per message (shows if conversation crossed channels)
- AI intent/confidence shown as subtle annotation on patient messages
- Action badges when AI performed actions ("Cita agendada para viernes 18 a las 10:00")
- Staff input area at bottom (only active for escalated/human_handling)
- "Take Over" button for escalated conversations
- "Resolve" button to close conversation

**Right column — Patient Context:**
- Patient card (name, phone, photo, last visit)
- Upcoming appointments
- Outstanding balance
- Recent conversation history across channels
- AI's pending action state (if mid-flow)
- Quick actions: "Schedule Appointment", "Send Payment Link"

### 12.2 Configuration Page

**Route:** `/dashboard/contact-center/settings`

**Sections:**
- **General:** Enable/disable, greeting messages, escalation message, confidence threshold
- **Channels:** Toggle WhatsApp/VoIP/Web Chat, channel-specific settings
- **FAQ Management:** CRUD for FAQ entries (question + answer pairs)
- **Proactive Campaigns:** Campaign list with create/edit/activate/pause/delete
- **Business Hours:** Hours configuration (reuses existing clinic settings)

### 12.3 Analytics Page

**Route:** `/dashboard/contact-center/analytics`

**Visualizations:**
- **Summary cards:** Total conversations, AI resolution rate, avg response time, appointments scheduled
- **Channel distribution:** Pie chart (WhatsApp / VoIP / Web Chat)
- **Intent distribution:** Horizontal bar chart
- **Conversion funnel:** Inquiry > Appointment Created > Confirmed > Show-up
- **Campaign performance:** Table with sent/responded/converted per campaign
- **Trend line:** Conversations per day over selected period
- **Cost savings estimate:** Hours saved, equivalent salary

### 12.4 Components

| Component | Location | Description |
|-----------|----------|-------------|
| `ContactCenterDashboard` | `app/(dashboard)/contact-center/page.tsx` | Main 3-column agent dashboard |
| `ConversationList` | `components/contact-center/conversation-list.tsx` | Filterable conversation list with real-time updates |
| `ConversationView` | `components/contact-center/conversation-view.tsx` | Chat-style message view with AI annotations |
| `PatientContextPanel` | `components/contact-center/patient-context-panel.tsx` | Patient info sidebar |
| `CampaignManager` | `components/contact-center/campaign-manager.tsx` | Campaign CRUD interface |
| `ContactCenterAnalytics` | `app/(dashboard)/contact-center/analytics/page.tsx` | Analytics dashboard |
| `ContactCenterSettings` | `app/(dashboard)/contact-center/settings/page.tsx` | Configuration page |
| `IntentBadge` | `components/contact-center/intent-badge.tsx` | Visual intent indicator |
| `ChannelIcon` | `components/contact-center/channel-icon.tsx` | WhatsApp/phone/chat icon |
| `EscalationAlert` | `components/contact-center/escalation-alert.tsx` | Pulsing alert for escalated conversations |

### 12.5 Hooks

| Hook | File | Description |
|------|------|-------------|
| `useContactCenterStream` | `lib/hooks/use-contact-center-stream.ts` | SSE connection for real-time events |
| `useContactCenterConversations` | `lib/hooks/use-contact-center-conversations.ts` | React Query for conversation list |
| `useContactCenterAnalytics` | `lib/hooks/use-contact-center-analytics.ts` | React Query for analytics data |
| `useContactCenterConfig` | `lib/hooks/use-contact-center-config.ts` | React Query for config CRUD |
| `useCampaigns` | `lib/hooks/use-campaigns.ts` | React Query for campaign CRUD |

---

## Test Plan

### 13.1 Backend Unit Tests

| Test File | Coverage |
|-----------|----------|
| `tests/unit/test_contact_center_service.py` | Orchestrator logic: intent routing, context management, state machine, escalation triggers |
| `tests/unit/test_contact_center_intent_router.py` | Expanded intent classification with all 16 intents |
| `tests/unit/test_contact_center_context.py` | Redis context CRUD, cross-channel context merge, TTL behavior |
| `tests/unit/test_contact_center_state_machine.py` | Multi-turn scheduling/rescheduling/cancellation flows |
| `tests/unit/test_contact_center_campaigns.py` | Campaign CRUD, schedule evaluation, target filtering |
| `tests/unit/test_channel_adapters.py` | WhatsApp/VoIP/WebChat adapter methods, 24h window, TwiML generation |

### 13.2 Backend Integration Tests

| Test File | Coverage |
|-----------|----------|
| `tests/integration/test_contact_center_api.py` | All API endpoints: config, conversations, campaigns, analytics |
| `tests/integration/test_contact_center_whatsapp.py` | End-to-end WhatsApp inbound message > AI response > action taken |
| `tests/integration/test_contact_center_voip.py` | Twilio webhook > AI response > TwiML output |
| `tests/integration/test_contact_center_escalation.py` | Automatic and manual escalation flows, SSE events |
| `tests/integration/test_contact_center_proactive.py` | Campaign evaluation, message dispatch, response handling |
| `tests/integration/test_contact_center_cross_channel.py` | Patient starts on WhatsApp, continues on web chat with context |

### 13.3 Frontend Tests

| Test File | Coverage |
|-----------|----------|
| `tests/components/contact-center-dashboard.test.tsx` | Dashboard rendering, conversation selection, real-time updates |
| `tests/components/conversation-view.test.tsx` | Message rendering, intent badges, take-over flow |
| `tests/components/campaign-manager.test.tsx` | Campaign CRUD forms, activation/pause |
| `tests/hooks/use-contact-center-stream.test.ts` | SSE connection, reconnection, event parsing |

### 13.4 E2E Scenarios

| Scenario | Steps |
|----------|-------|
| Happy path: WhatsApp appointment scheduling | Patient sends WhatsApp > AI classifies schedule > asks procedure > asks date > shows slots > patient confirms > appointment created > confirmation sent |
| Cross-channel continuity | Patient calls (VoIP) asking about availability > hangs up > messages on WhatsApp "quiero la de las 10" > AI remembers VoIP context > confirms appointment |
| Escalation to human | Patient asks complex insurance question > AI confidence low > escalates > receptionist gets SSE alert > takes over > resolves on WhatsApp |
| Proactive appointment confirmation | Campaign triggers 24h before > WhatsApp template sent > patient replies "SI" > AI confirms appointment > log updated |
| Proactive payment reminder | Campaign triggers for overdue invoice > WhatsApp sent > patient asks "cuanto debo?" > AI provides balance > patient asks for payment link |
| Opt-out | Patient replies "PARAR" to proactive message > opt-out recorded > no further proactive messages > inbound still works |
| VoIP full flow | Patient calls > Twilio webhook > AI greets > patient says "quiero cancelar mi cita" > AI identifies appointment > confirms cancellation > appointment cancelled > call ends |

### 13.5 Load Testing

- Simulate 50 concurrent conversations across all channels
- Verify Redis context operations < 5ms
- Verify Claude API calls < 2s p95
- Verify SSE event delivery < 500ms
- Verify campaign batch of 500 messages dispatches within 5 minutes

---

## Files to Create

### Backend

| File | Description |
|------|-------------|
| `backend/app/models/tenant/contact_center.py` | ContactCenterConversation, ContactCenterMessage, ContactCenterCampaign, ContactCenterCampaignLog models |
| `backend/app/schemas/contact_center.py` | Pydantic schemas: ConfigResponse, ConfigUpdate, ConversationResponse, CampaignCreate, CampaignResponse, AnalyticsSummary, InboundMessage, InboundResponse |
| `backend/app/services/contact_center_service.py` | Main orchestrator: handle_inbound, manage_context, execute_action, escalate |
| `backend/app/services/contact_center_intent_router.py` | Expanded intent classifier (16 intents) using Claude Haiku |
| `backend/app/services/contact_center_context.py` | Redis context manager: get, set, merge, invalidate |
| `backend/app/services/contact_center_campaign_service.py` | Campaign CRUD, schedule evaluation, batch dispatch |
| `backend/app/services/contact_center_state_machine.py` | Multi-turn state machine for scheduling/rescheduling/cancellation |
| `backend/app/services/channel_adapters/whatsapp_adapter.py` | WhatsApp channel adapter |
| `backend/app/services/channel_adapters/voip_adapter.py` | VoIP channel adapter (TwiML generation) |
| `backend/app/services/channel_adapters/web_chat_adapter.py` | Web chat channel adapter |
| `backend/app/api/v1/contact_center/router.py` | Config, conversations, campaigns, analytics endpoints |
| `backend/app/api/v1/contact_center/stream_router.py` | SSE endpoint for real-time events |

### Frontend

| File | Description |
|------|-------------|
| `frontend/app/(dashboard)/contact-center/page.tsx` | Agent dashboard (3-column layout) |
| `frontend/app/(dashboard)/contact-center/settings/page.tsx` | Configuration page |
| `frontend/app/(dashboard)/contact-center/analytics/page.tsx` | Analytics dashboard |
| `frontend/components/contact-center/conversation-list.tsx` | Conversation list with filters |
| `frontend/components/contact-center/conversation-view.tsx` | Chat message view |
| `frontend/components/contact-center/patient-context-panel.tsx` | Patient context sidebar |
| `frontend/components/contact-center/campaign-manager.tsx` | Campaign CRUD |
| `frontend/components/contact-center/intent-badge.tsx` | Intent visual indicator |
| `frontend/components/contact-center/channel-icon.tsx` | Channel icon component |
| `frontend/components/contact-center/escalation-alert.tsx` | Escalation notification |
| `frontend/lib/hooks/use-contact-center-stream.ts` | SSE hook |
| `frontend/lib/hooks/use-contact-center-conversations.ts` | Conversations React Query hook |
| `frontend/lib/hooks/use-contact-center-analytics.ts` | Analytics React Query hook |
| `frontend/lib/hooks/use-contact-center-config.ts` | Config React Query hook |
| `frontend/lib/hooks/use-campaigns.ts` | Campaigns React Query hook |

### Migration

| File | Description |
|------|-------------|
| `backend/alembic_tenant/versions/016_add_contact_center_tables.py` | Tenant migration for all 4 new tables |

---

## Dentalink Comparison

| Capability | Dentalink | DentalOS |
|-----------|-----------|----------|
| WhatsApp AI | Yes — auto scheduling | Yes — scheduling + billing + FAQ + proactive |
| VoIP AI | Yes — auto scheduling | Yes — full intent set, TTS/STT |
| Web Chat AI | Unknown | Yes — widget + portal authenticated |
| Cross-channel context | No (channels are independent) | Yes — patient context shared across all channels |
| Proactive outreach | Manual campaigns | AI-driven campaigns with auto-scheduling triggers |
| Human escalation | Unknown | Full context handoff with SSE real-time alerts |
| Campaign analytics | Basic | Conversion funnel: inquiry > appointment > show-up |
| Configurable by clinic | Yes (assistant name, personality) | Yes (greeting, FAQ, confidence threshold, campaigns) |
| Deep system integration | Scheduling only | Scheduling + billing + patient records + appointments |
| Cost savings tracking | No | Yes — hours saved, equivalent salary estimate |
