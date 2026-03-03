"""Pydantic schemas for the email marketing campaign domain (VP-17)."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


# ── Segment Filters ─────────────────────────────────────────────────────────


class SegmentFilters(BaseModel):
    """Criteria used to select campaign recipients from the patient table.

    All fields are optional; omitted fields are not used as filter conditions.
    Multiple fields are combined with AND logic.
    """

    last_visit_before: date | None = Field(
        default=None,
        description="Include patients whose most recent appointment was before this date.",
    )
    last_visit_after: date | None = Field(
        default=None,
        description="Include patients whose most recent appointment was after this date.",
    )
    age_min: int | None = Field(
        default=None,
        ge=0,
        le=150,
        description="Minimum patient age (inclusive).",
    )
    age_max: int | None = Field(
        default=None,
        ge=0,
        le=150,
        description="Maximum patient age (inclusive).",
    )
    insurance_type: str | None = Field(
        default=None,
        max_length=100,
        description="Filter by patients.insurance_provider value (exact match, case-insensitive).",
    )
    has_balance_due: bool | None = Field(
        default=None,
        description="True: include only patients with at least one unpaid invoice.",
    )

    @model_validator(mode="after")
    def _validate_age_range(self) -> "SegmentFilters":
        if (
            self.age_min is not None
            and self.age_max is not None
            and self.age_min > self.age_max
        ):
            raise ValueError("age_min must not be greater than age_max.")
        return self

    @model_validator(mode="after")
    def _validate_visit_range(self) -> "SegmentFilters":
        if (
            self.last_visit_after is not None
            and self.last_visit_before is not None
            and self.last_visit_after > self.last_visit_before
        ):
            raise ValueError(
                "last_visit_after must not be later than last_visit_before."
            )
        return self


# ── Campaign Create / Update ─────────────────────────────────────────────────


class EmailCampaignCreate(BaseModel):
    """Payload for creating a new email marketing campaign (draft status)."""

    name: str = Field(min_length=1, max_length=200)
    subject: str = Field(min_length=1, max_length=500)
    template_id: str | None = Field(default=None, max_length=100)
    template_html: str | None = Field(default=None)
    segment_filters: SegmentFilters | None = Field(default=None)

    @model_validator(mode="after")
    def _require_content(self) -> "EmailCampaignCreate":
        """Either template_id or template_html must be provided."""
        if not self.template_id and not self.template_html:
            raise ValueError(
                "Se requiere template_id o template_html para crear la campaña."
            )
        return self


class EmailCampaignUpdate(BaseModel):
    """Payload for updating a draft campaign. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    subject: str | None = Field(default=None, min_length=1, max_length=500)
    template_html: str | None = Field(default=None)
    segment_filters: SegmentFilters | None = Field(default=None)


# ── Response Schemas ─────────────────────────────────────────────────────────


class EmailCampaignResponse(BaseModel):
    """Summary of an email campaign returned by list and detail endpoints."""

    id: uuid.UUID
    name: str
    subject: str
    template_id: str | None = None
    status: str
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    sent_count: int
    open_count: int
    click_count: int
    bounce_count: int
    unsubscribe_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignListResponse(BaseModel):
    """Paginated list of email campaigns."""

    items: list[EmailCampaignResponse]
    total: int
    page: int
    page_size: int


class CampaignStatsResponse(BaseModel):
    """Engagement statistics for a sent campaign."""

    sent_count: int
    open_count: int
    click_count: int
    bounce_count: int
    unsubscribe_count: int
    open_rate: float = Field(description="Percentage of sent emails that were opened.")
    click_rate: float = Field(description="Percentage of sent emails that were clicked.")


class CampaignRecipientResponse(BaseModel):
    """A single recipient record within a campaign."""

    id: uuid.UUID
    patient_id: uuid.UUID
    email: str
    status: str
    sent_at: datetime | None = None
    opened_at: datetime | None = None
    clicked_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CampaignRecipientListResponse(BaseModel):
    """Paginated list of campaign recipients."""

    items: list[CampaignRecipientResponse]
    total: int
    page: int
    page_size: int


# ── Action Schemas ───────────────────────────────────────────────────────────


class ScheduleRequest(BaseModel):
    """Request to schedule a draft campaign for future sending."""

    scheduled_at: datetime = Field(
        description="UTC datetime when the campaign should be dispatched."
    )

    @model_validator(mode="after")
    def _must_be_future(self) -> "ScheduleRequest":
        from datetime import UTC

        if self.scheduled_at <= datetime.now(UTC):
            raise ValueError("scheduled_at debe ser una fecha y hora en el futuro.")
        return self


# ── Template Schemas ─────────────────────────────────────────────────────────


class EmailTemplateResponse(BaseModel):
    """A built-in Spanish marketing email template."""

    template_id: str
    name: str
    subject_template: str
    description: str
