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
    must_change_password: bool = False
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
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class PortalRegisterRequest(BaseModel):
    """Complete portal registration (set password from invitation)."""

    token: str = Field(..., min_length=10)
    tenant_id: str
    password: str = Field(..., min_length=8, max_length=128)


class PortalChangePasswordRequest(BaseModel):
    """Change portal password (used after first login with temp password)."""

    new_password: str = Field(..., min_length=8, max_length=128)


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
    unread_messages: int = 0
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


# ─── Postop Instruction Schemas ─────────────────────────────────────────────


class PostopInstructionItem(BaseModel):
    """Single post-operative instruction for portal view."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    procedure_type: str
    title: str
    instruction_content: str
    channel: str
    doctor_name: str | None = None
    sent_at: datetime
    is_read: bool = False
    read_at: datetime | None = None


class PostopInstructionListResponse(BaseModel):
    """Paginated list of postop instructions."""

    data: list[PostopInstructionItem]
    pagination: CursorPagination


# ─── Patient Profile Update (V1) ────────────────────────────────────────────


class PatientProfileUpdateRequest(BaseModel):
    """Editable patient profile fields (excludes regulatory fields)."""

    phone: str | None = Field(default=None, pattern=r"^\+?[0-9]{7,15}$")
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    emergency_contact_name: str | None = Field(default=None, max_length=200)
    emergency_contact_phone: str | None = Field(
        default=None, pattern=r"^\+?[0-9]{7,15}$"
    )


# ─── Notification Preferences (V2) ──────────────────────────────────────────


class NotificationPreferencesResponse(BaseModel):
    """Patient notification channel preferences."""

    email_enabled: bool = True
    whatsapp_enabled: bool = True
    sms_enabled: bool = True
    appointment_reminders: bool = True
    treatment_updates: bool = True
    billing_notifications: bool = True
    marketing_messages: bool = False


class NotificationPreferencesUpdate(BaseModel):
    """Update notification preferences."""

    email_enabled: bool | None = None
    whatsapp_enabled: bool | None = None
    sms_enabled: bool | None = None
    appointment_reminders: bool | None = None
    treatment_updates: bool | None = None
    billing_notifications: bool | None = None
    marketing_messages: bool | None = None


# ─── Reschedule (V3) ────────────────────────────────────────────────────────


class RescheduleRequest(BaseModel):
    """Request to reschedule an existing appointment."""

    new_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    new_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")


# ─── Document Upload (V4) ───────────────────────────────────────────────────


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document from portal."""

    id: str
    document_type: str
    file_name: str
    created_at: datetime
    message: str


# ─── Odontogram History (V5) ────────────────────────────────────────────────


class OdontogramSnapshotItem(BaseModel):
    """A single odontogram snapshot in the history timeline."""

    id: str
    snapshot_date: datetime
    tooth_count: int = 0
    condition_count: int = 0
    notes: str | None = None


# ─── Phase 2 Schemas ────────────────────────────────────────────────────────


class PortalSurveyResponse(BaseModel):
    """A patient's NPS/CSAT survey response (F6)."""

    id: str
    nps_score: int | None = None
    csat_score: int | None = None
    comments: str | None = None
    channel_sent: str
    sent_at: datetime
    responded_at: datetime | None = None


class PortalSurveyListResponse(BaseModel):
    """List of survey responses."""

    data: list[PortalSurveyResponse]


class PortalFinancingApplication(BaseModel):
    """A patient's financing application (F7)."""

    id: str
    provider: str
    status: str
    amount_cents: int
    installments: int
    created_at: datetime


class PortalFinancingListResponse(BaseModel):
    """List of financing applications."""

    data: list[PortalFinancingApplication]


class PortalFamilyMember(BaseModel):
    """A member of the patient's family group (F8)."""

    id: str
    first_name: str
    last_name: str
    relationship: str


class PortalFamilyGroup(BaseModel):
    """Patient's family group with members (F8)."""

    id: str
    name: str
    members: list[PortalFamilyMember]
    total_outstanding: int = 0


class PortalFamilyResponse(BaseModel):
    """Family group response — null if patient has no family."""

    family: PortalFamilyGroup | None = None


class PortalLabOrder(BaseModel):
    """A patient's lab order (F9)."""

    id: str
    order_type: str
    status: str
    due_date: str | None = None
    lab_name: str | None = None
    created_at: datetime


class PortalLabOrderListResponse(BaseModel):
    """List of lab orders."""

    data: list[PortalLabOrder]


class PortalToothPhotoItem(BaseModel):
    """A single tooth photo (F10)."""

    id: str
    tooth_number: int
    url: str
    thumbnail_url: str | None = None
    created_at: datetime


class PortalToothPhotoListResponse(BaseModel):
    """List of tooth photos."""

    data: list[PortalToothPhotoItem]


class PortalHealthHistory(BaseModel):
    """Patient's health history data (F11)."""

    allergies: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    surgeries: list[str] = Field(default_factory=list)
    notes: str | None = None


class PortalHealthHistoryUpdate(BaseModel):
    """Update health history from portal (F11)."""

    allergies: list[str] | None = None
    medications: list[str] | None = None
    conditions: list[str] | None = None
    surgeries: list[str] | None = None
    notes: str | None = None


class FinancingSimulationRequest(BaseModel):
    """Request to simulate financing options (F12)."""

    amount_cents: int = Field(..., gt=0)
    provider: str = Field(..., pattern=r"^(addi|sistecredito|mercadopago)$")


class FinancingSimulationOption(BaseModel):
    """A single financing installment option."""

    installments: int
    monthly_payment_cents: int
    total_cents: int
    interest_rate_pct: float


class FinancingSimulationResponse(BaseModel):
    """Financing simulation result (F12)."""

    provider: str
    eligible: bool
    options: list[FinancingSimulationOption] = Field(default_factory=list)
    message: str | None = None


class PortalTimelineEvent(BaseModel):
    """A single event in the treatment timeline (F13)."""

    id: str
    event_type: str  # "procedure" or "photo"
    title: str
    date: datetime
    status: str | None = None
    photo_url: str | None = None
    tooth_number: str | None = None
    treatment_plan_name: str | None = None


class PortalTimelineResponse(BaseModel):
    """Treatment timeline (F13)."""

    events: list[PortalTimelineEvent]
