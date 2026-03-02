"""Cash register and movement models."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class CashRegister(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Represents a single cash register session (open → closed)."""

    __tablename__ = "cash_registers"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'closed')", name="chk_cash_registers_status"),
        Index("idx_cash_registers_status", "status"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="closed")
    opened_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opening_balance_cents: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    closing_balance_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    movements: Mapped[list["CashMovement"]] = relationship(back_populates="register")


class CashMovement(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A single cash movement (income, expense, or adjustment) within a register session."""

    __tablename__ = "cash_movements"
    __table_args__ = (
        CheckConstraint(
            "type IN ('income', 'expense', 'adjustment')",
            name="chk_cash_movements_type",
        ),
        Index("idx_cash_movements_register", "register_id"),
        Index("idx_cash_movements_type", "type"),
    )

    register_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cash_registers.id"), nullable=False,
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )

    register: Mapped["CashRegister"] = relationship(back_populates="movements")
