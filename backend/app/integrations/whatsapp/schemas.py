"""WhatsApp webhook and message schemas -- INT-01."""

from pydantic import BaseModel, Field


# --- Outbound Template Message ------------------------------------------------


class WhatsAppTemplateParam(BaseModel):
    """A single template parameter."""

    type: str = "text"
    text: str


class WhatsAppTemplateComponent(BaseModel):
    """Template component (body, header, button)."""

    type: str = "body"
    parameters: list[WhatsAppTemplateParam] = Field(default_factory=list)


class WhatsAppTemplateSend(BaseModel):
    """Outbound template message payload."""

    to_phone: str = Field(..., pattern=r"^\+?[0-9]{7,15}$")
    template_name: str = Field(..., min_length=1, max_length=512)
    language_code: str = Field(default="es", max_length=10)
    parameters: dict[str, str] = Field(default_factory=dict)


# --- Webhook Events (from Meta) -----------------------------------------------


class WhatsAppWebhookStatus(BaseModel):
    """Delivery status from webhook."""

    id: str
    status: str  # "sent", "delivered", "read", "failed"
    timestamp: str
    recipient_id: str


class WhatsAppWebhookEntry(BaseModel):
    """Single webhook entry."""

    id: str
    changes: list[dict] = Field(default_factory=list)


class WhatsAppWebhookPayload(BaseModel):
    """Full webhook payload from Meta."""

    object: str = "whatsapp_business_account"
    entry: list[WhatsAppWebhookEntry] = Field(default_factory=list)
