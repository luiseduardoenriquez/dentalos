"""Pydantic schemas for the Patient Portal (PP-01 through PP-13)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from typing import Literal


# ─── Auth Schemas (PP-01) ────────────────────────────────────────────────────


class PortalLoginRequest(BaseModel):
    """Portal login request — supports password or magic link."""

    login_method: Literal["password", "magic_link"]
    identifier: str = Field(
        ..., min_length=3, max_length=255, description="Email or phone number"
    )
    password: str | None = Field(default=None, min_length=8, max_length=128)
    magic_link_channel: Literal["email", "whatsapp"] | None = None
    tenant_id: str = Field(..., description="Tenant ID for portal login")


class PortalPatientSummary(BaseModel):
    """Minimal patient info returned after login."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None


class PortalLoginResponse(BaseModel):
    """Successful portal login response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    patient: PortalPatientSummary


class MagicLinkResponse(BaseModel):
    """Response after requesting a magic link."""

    status: str = "sent"
    message: str = "Si la cuenta existe, se ha enviado un enlace de acceso."
    expires_in_minutes: int = 15
    channel: str


class MagicLinkVerifyRequest(BaseModel):
    """Verify/redeem a magic link token."""

    token: str = Field(..., min_length=10)
    tenant_id: str


class PortalTokenResponse(BaseModel):
    """Refreshed access token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PortalRegisterRequest(BaseModel):
    """Complete portal registration (set password from invitation)."""

    token: str = Field(..., min_length=10)
    tenant_id: str
    password: str = Field(..., min_length=8, max_length=128)


# ─── Portal Access Schemas (P-11) ────────────────────────────────────────────


class PortalAccessRequest(BaseModel):
    """Grant or revoke portal access for a patient."""

    action: Literal["grant", "revoke"]
    invitation_channel: Literal["email", "whatsapp"] | None = None


class PortalAccessGrantResponse(BaseModel):
    """Response after granting portal access."""

    message: str
    patient_id: str
    portal_access: bool = True
    invitation_sent_via: str | None = None
    invitation_expires_at: datetime | None = None


class PortalAccessRevokeResponse(BaseModel):
    """Response after revoking portal access."""

    message: str
    patient_id: str
    portal_access: bool = False
    tokens_revoked: int = 0


# ─── Cursor Pagination ────────────────────────────────────────────────────────


class CursorPagination(BaseModel):
    """Cursor-based pagination metadata."""

    next_cursor: str | None = None
    has_more: bool = False


# ─── Portal Data Schemas (Read) ──────────────────────────────────────────────


class PortalClinicInfo(BaseModel):
    """Clinic info visible to portal patients."""

    name: str
    slug: str
    logo_url: str | None = None
    phone: str | None = None
    address: str | None = None


class PortalAppointmentResponse(BaseModel):
    """Single appointment in portal view (PP-03)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    scheduled_at: datetime
    duration_minutes: int
    status: str
    appointment_type: str | None = None
    doctor_name: str
    doctor_specialty: str | None = None
    notes_for_patient: str | None = None


class PortalPatientProfile(BaseModel):
    """Patient profile visible in the portal (PP-02)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    birthdate: str | None = None
    gender: str | None = None
    document_type: str
    document_number: str
    insurance_provider: str | None = None
    insurance_policy_number: str | None = None
    clinic: PortalClinicInfo
    outstanding_balance: int = 0
    next_appointment: PortalAppointmentResponse | None = None


class PortalAppointmentListResponse(BaseModel):
    """Paginated list of portal appointments."""

    data: list[PortalAppointmentResponse]
    pagination: CursorPagination


class PortalTreatmentPlanProcedure(BaseModel):
    """Single procedure within a treatment plan."""

    id: str
    name: str
    status: str
    cost: int
    tooth_number: str | None = None


class PortalTreatmentPlanResponse(BaseModel):
    """Single treatment plan in portal view (PP-04)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: str
    procedures: list[PortalTreatmentPlanProcedure]
    total: int
    paid: int
    progress_pct: int
    created_at: datetime


class PortalTreatmentPlanListResponse(BaseModel):
    """Paginated list of treatment plans."""

    data: list[PortalTreatmentPlanResponse]
    pagination: CursorPagination


class PortalInvoiceLineItem(BaseModel):
    """Single line item on an invoice."""

    description: str
    quantity: int
    unit_price: int
    total: int


class PortalInvoiceResponse(BaseModel):
    """Single invoice in portal view (PP-06)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_number: str | None = None
    date: datetime
    total: int
    paid: int
    balance: int
    status: str
    line_items: list[PortalInvoiceLineItem]


class PortalInvoiceListResponse(BaseModel):
    """Paginated list of invoices."""

    data: list[PortalInvoiceResponse]
    pagination: CursorPagination


class PortalDocumentResponse(BaseModel):
    """Single document in portal view (PP-07)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    document_type: str
    name: str
    created_at: datetime
    signed_at: datetime | None = None
    url: str | None = None


class PortalDocumentListResponse(BaseModel):
    """Paginated list of documents."""

    data: list[PortalDocumentResponse]
    pagination: CursorPagination


class PortalMessage(BaseModel):
    """Single message in a thread."""

    id: str
    body: str
    sender_type: Literal["patient", "staff"]
    sender_name: str
    created_at: datetime


class PortalMessageThread(BaseModel):
    """Message thread in portal (PP-10)."""

    id: str
    subject: str | None = None
    last_message_at: datetime
    unread_count: int = 0
    messages: list[PortalMessage] = []


class PortalMessageListResponse(BaseModel):
    """List of message threads."""

    data: list[PortalMessageThread]
    pagination: CursorPagination


class PortalToothCondition(BaseModel):
    """Single condition on a tooth for portal odontogram."""

    condition_code: str
    condition_name: str
    surface: str | None = None
    description: str | None = None


class PortalTooth(BaseModel):
    """Single tooth in portal odontogram view."""

    tooth_number: str
    conditions: list[PortalToothCondition]
    status: str | None = None


class PortalOdontogramResponse(BaseModel):
    """Read-only odontogram for portal (PP-13)."""

    teeth: list[PortalTooth]
    last_updated: datetime | None = None
    legend: dict[str, str] = {}


# ─── Portal Action Schemas (Write) ───────────────────────────────────────────


class PortalBookAppointmentRequest(BaseModel):
    """Request to book an appointment from portal (PP-08)."""

    doctor_id: str
    appointment_type_id: str
    preferred_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    preferred_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    notes: str | None = Field(default=None, max_length=500)


class PortalCancelAppointmentRequest(BaseModel):
    """Request to cancel an appointment from portal (PP-09)."""

    reason: str | None = Field(default=None, max_length=500)


class PortalApprovePlanRequest(BaseModel):
    """Request to approve a treatment plan with signature (PP-05)."""

    signature_data: str = Field(..., description="Base64-encoded PNG signature")
    agreed_terms: bool = Field(..., description="Patient confirmed reading terms")


class PortalSignConsentRequest(BaseModel):
    """Request to sign a consent document (PP-12)."""

    signature_data: str = Field(..., description="Base64-encoded PNG signature")
    acknowledged: bool = Field(..., description="Patient confirmed reading consent")


class PortalSendMessageRequest(BaseModel):
    """Request to send a message from portal (PP-11)."""

    thread_id: str | None = None
    body: str = Field(..., min_length=1, max_length=2000)
    attachment_ids: list[str] | None = None
