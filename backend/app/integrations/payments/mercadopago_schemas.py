"""Pydantic v2 schemas for the Mercado Pago payment integration.

All monetary values are in cents (integer) to avoid floating-point issues.
Field names follow DentalOS snake_case convention throughout.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Outbound result DTOs (returned by the service to callers)
# ---------------------------------------------------------------------------


class PreferenceResult(BaseModel):
    """Result after creating a Mercado Pago checkout preference.

    preference_id is the MP-assigned ID.
    init_point is the live checkout URL.
    sandbox_init_point is the sandbox/test checkout URL.
    """

    preference_id: str = Field(..., description="Mercado Pago-assigned preference ID")
    init_point: str = Field(
        ...,
        description="Live checkout URL to redirect the payer to",
    )
    sandbox_init_point: str = Field(
        ...,
        description="Sandbox checkout URL for test environments",
    )


class SubscriptionResult(BaseModel):
    """Result after creating a Mercado Pago recurring subscription (preapproval).

    subscription_id is the MP-assigned preapproval ID.
    status reflects the initial authorization state.
    init_point is the URL where the payer approves the recurring charge.
    """

    subscription_id: str = Field(
        ...,
        description="Mercado Pago preapproval ID for the subscription",
    )
    status: str = Field(
        ...,
        description="Initial subscription status (e.g. 'pending', 'authorized')",
    )
    init_point: str = Field(
        ...,
        description="URL where the payer must authorize the recurring charge",
    )


class PaymentStatusResult(BaseModel):
    """Status of a specific Mercado Pago payment.

    Maps to the GET /v1/payments/{id} response fields.
    payer_email is optional because it is PHI — callers must not log it.
    """

    payment_id: str = Field(..., description="Mercado Pago payment ID")
    status: str = Field(
        ...,
        description=(
            "MP payment status: 'pending', 'approved', 'authorized', "
            "'in_process', 'in_mediation', 'rejected', 'cancelled', "
            "'refunded', 'charged_back'"
        ),
    )
    status_detail: str = Field(
        ...,
        description="Granular status detail code returned by Mercado Pago",
    )
    amount_cents: int = Field(
        ...,
        ge=0,
        description="Transaction amount in cents",
    )
    payer_email: str | None = Field(
        default=None,
        description="Payer email address — PHI, never log this field",
    )


# ---------------------------------------------------------------------------
# Inbound webhook payload DTOs (from Mercado Pago IPN callbacks)
# ---------------------------------------------------------------------------


class MercadoPagoIPNPayload(BaseModel):
    """Payload received from a Mercado Pago IPN (Instant Payment Notification).

    MP sends a minimal envelope; the actual resource must be fetched from
    the API using the ``data_id`` field.

    Reference:
        https://www.mercadopago.com/developers/en/docs/your-integrations/notifications/ipn
    """

    id: str | None = Field(default=None, description="MP notification ID")
    live_mode: bool | None = Field(
        default=None,
        description="True when sent from a live (production) environment",
    )
    type: str = Field(
        ...,
        description=(
            "Notification resource type: 'payment' or 'subscription_preapproval'"
        ),
    )
    date_created: str | None = Field(default=None)
    application_id: str | None = Field(default=None)
    user_id: str | None = Field(default=None)
    version: int | None = Field(default=None)
    api_version: str | None = Field(default=None)
    action: str | None = Field(
        default=None,
        description="Event action, e.g. 'payment.created', 'payment.updated'",
    )
    data: dict = Field(
        default_factory=dict,
        description="Resource data envelope. Always contains 'id' key.",
    )
