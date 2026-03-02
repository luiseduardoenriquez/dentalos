"""QR payment request/response schemas for Nequi/Daviplata."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PaymentQRRequest(BaseModel):
    """Request to generate a QR payment code."""

    provider: str = Field(
        ...,
        pattern=r"^(nequi|daviplata)$",
        description="Payment provider: nequi or daviplata",
    )


class PaymentQRResponse(BaseModel):
    """QR code response with payment details."""

    model_config = ConfigDict(from_attributes=True)

    qr_code_base64: str = Field(..., description="Base64-encoded PNG QR code image")
    payment_id: str = Field(..., description="Provider-assigned payment identifier")
    provider: str = Field(..., description="nequi or daviplata")
    amount_cents: int = Field(..., gt=0, description="Amount in COP cents")
    expires_at: datetime = Field(..., description="UTC timestamp when the QR code expires")
    invoice_id: str = Field(..., description="DentalOS invoice UUID")
