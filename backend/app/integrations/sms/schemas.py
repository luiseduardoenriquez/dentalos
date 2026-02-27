"""Twilio SMS schemas — INT-02."""

from pydantic import BaseModel, Field


class SMSSend(BaseModel):
    """SMS send request."""

    to_phone: str = Field(..., pattern=r"^\+?[0-9]{7,15}$")
    body: str = Field(..., min_length=1, max_length=1600)


class SMSOTPSend(BaseModel):
    """OTP send request."""

    to_phone: str = Field(..., pattern=r"^\+?[0-9]{7,15}$")
    code: str = Field(..., pattern=r"^[0-9]{4,8}$")


class TwilioWebhookStatus(BaseModel):
    """Twilio delivery status webhook payload."""

    MessageSid: str = ""
    MessageStatus: str = ""
    To: str = ""
    ErrorCode: str | None = None
    ErrorMessage: str | None = None
