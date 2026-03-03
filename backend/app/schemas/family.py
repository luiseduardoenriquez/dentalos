"""Family group schemas — request/response models for the families domain."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class FamilyGroupCreate(BaseModel):
    """Create a new family group."""

    name: str = Field(min_length=1, max_length=200)
    primary_contact_patient_id: str


class MemberAdd(BaseModel):
    """Add a patient to an existing family group."""

    patient_id: str
    relationship: str = Field(pattern=r"^(parent|child|spouse|sibling|other)$")


class MemberResponse(BaseModel):
    """A single member within a family group response."""

    patient_id: uuid.UUID
    patient_name: str
    relationship: str
    is_active: bool


class FamilyResponse(BaseModel):
    """Full family group details including member list."""

    id: uuid.UUID
    name: str
    primary_contact_patient_id: uuid.UUID
    members: list[MemberResponse]
    is_active: bool
    created_at: datetime


class FamilyBillingSummary(BaseModel):
    """Consolidated billing view across all members of a family group."""

    family_id: uuid.UUID
    family_name: str
    members: list[dict]
    total_billed: int
    total_paid: int
    total_balance: int
