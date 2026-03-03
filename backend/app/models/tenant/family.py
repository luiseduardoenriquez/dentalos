"""Family group models — live in each tenant schema.

Two tables:
  - FamilyGroup: a named group of related patients with a designated primary contact.
  - FamilyMember: a patient's membership in a family group with a relationship type.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class FamilyGroup(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A named group of related patients within a clinic.

    The primary_contact_patient_id designates which family member is the
    primary administrative contact (billing, scheduling, etc.).

    Clinical data is NEVER hard-deleted (regulatory requirement).
    Use is_active=False + deleted_at for soft delete.
    """

    __tablename__ = "family_groups"
    __table_args__ = (
        Index("idx_family_groups_primary_contact", "primary_contact_patient_id"),
        Index("idx_family_groups_is_active", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    primary_contact_patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<FamilyGroup name={self.name!r} id={str(self.id)[:8]}>"


class FamilyMember(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A patient's membership in a family group.

    Each patient may belong to at most one family group at a time
    (enforced by the UNIQUE constraint on patient_id).
    """

    __tablename__ = "family_members"
    __table_args__ = (
        UniqueConstraint("patient_id", name="uq_family_members_patient"),
        CheckConstraint(
            "relationship IN ('parent', 'child', 'spouse', 'sibling', 'other')",
            name="chk_family_members_relationship",
        ),
        Index("idx_family_members_family_group", "family_group_id"),
        Index("idx_family_members_patient", "patient_id"),
        Index("idx_family_members_is_active", "is_active"),
    )

    family_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("family_groups.id"),
        nullable=False,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    relationship: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return (
            f"<FamilyMember patient={str(self.patient_id)[:8]}"
            f" family={str(self.family_group_id)[:8]}"
            f" relationship={self.relationship!r}>"
        )
