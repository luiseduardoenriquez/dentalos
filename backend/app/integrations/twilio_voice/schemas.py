"""Pydantic schemas for Twilio Voice webhook payloads -- VP-18."""

from pydantic import BaseModel


class IncomingCallEvent(BaseModel):
    """Normalised representation of a Twilio incoming call webhook.

    Twilio sends form-encoded fields with PascalCase names.  We translate
    them here to snake_case so the rest of the service layer stays consistent
    with DentalOS conventions.
    """

    call_sid: str
    from_number: str
    to_number: str
    call_status: str
    direction: str = "inbound"


class TwilioVoiceCallResponse(BaseModel):
    """Response schema for Twilio Voice call operations."""

    call_sid: str
    status: str


class CallStatusEvent(BaseModel):
    """Normalised representation of a Twilio call status callback.

    Used internally when mapping form-encoded status callbacks to service
    calls.  duration is None until the call ends.
    """

    call_sid: str
    call_status: str
    call_duration: str | None = None
