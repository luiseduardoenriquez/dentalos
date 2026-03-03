"""Loyalty points models -- patient point balances and transaction ledger.

LoyaltyPoints tracks each patient's current balance and lifetime totals.
LoyaltyTransaction is an append-only ledger recording every point change.

Security invariants:
  - PHI is NEVER logged (patient names, IDs truncated to 8 chars max).
  - Points balances must never go negative (CHECK constraint).
  - Transactions are append-only -- no updates, no deletes.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class LoyaltyPoints(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Aggregate loyalty point balance for a single patient.

    One row per patient. Updated transactionally alongside every
    LoyaltyTransaction insert via SELECT ... FOR UPDATE.
    """

    __tablename__ = "loyalty_points"
    __table_args__ = (
        CheckConstraint(
            "points_balance >= 0",
            name="chk_loyalty_points_balance_non_negative",
        ),
        UniqueConstraint("patient_id", name="uq_loyalty_points_patient"),
        Index("idx_loyalty_points_patient", "patient_id"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False,
    )
    points_balance: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    lifetime_points_earned: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    lifetime_points_redeemed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )


class LoyaltyTransaction(UUIDPrimaryKeyMixin, TenantBase):
    """Append-only ledger of all loyalty point changes.

    Does NOT use TimestampMixin because transactions are immutable --
    there is no updated_at. The created_at is set once at insert time.
    """

    __tablename__ = "loyalty_transactions"
    __table_args__ = (
        CheckConstraint(
            "type IN ('earned', 'redeemed', 'expired', 'adjusted')",
            name="chk_loyalty_transactions_type",
        ),
        Index("idx_loyalty_transactions_patient", "patient_id"),
        Index("idx_loyalty_transactions_type", "type"),
        Index("idx_loyalty_transactions_created_at", "created_at"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False,
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    reference_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True,
    )
    performed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
