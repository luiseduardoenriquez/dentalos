"""Patient referral program models -- patient-refers-patient.

Distinct from referral.py which handles doctor-to-doctor clinical referrals.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class ReferralCode(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A unique referral code owned by a patient for sharing."""

    __tablename__ = "referral_codes"
    __table_args__ = (
        Index("idx_referral_codes_patient", "patient_id"),
        Index("idx_referral_codes_code", "code"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False,
    )
    code: Mapped[str] = mapped_column(String(8), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    uses_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)

    rewards: Mapped[list["ReferralReward"]] = relationship(
        back_populates="referral_code",
        foreign_keys="ReferralReward.referral_code_id",
    )


class ReferralReward(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A reward (discount or credit) earned through a patient referral."""

    __tablename__ = "referral_rewards"
    __table_args__ = (
        CheckConstraint(
            "reward_type IN ('discount', 'credit')",
            name="chk_referral_rewards_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'applied', 'expired')",
            name="chk_referral_rewards_status",
        ),
        Index("idx_referral_rewards_referrer", "referrer_patient_id"),
        Index("idx_referral_rewards_status", "status"),
    )

    referrer_patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False,
    )
    referred_patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False,
    )
    referral_code_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("referral_codes.id"), nullable=False,
    )
    reward_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="'discount'",
    )
    reward_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="'pending'",
    )
    applied_to_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    referral_code: Mapped["ReferralCode"] = relationship(
        back_populates="rewards",
        foreign_keys=[referral_code_id],
    )
