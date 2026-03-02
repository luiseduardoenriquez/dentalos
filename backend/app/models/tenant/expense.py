"""Expense category and expense models."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class ExpenseCategory(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """User-defined category for grouping expenses (e.g. Materiales, Servicios)."""

    __tablename__ = "expense_categories"
    __table_args__ = (
        Index("idx_expense_categories_active", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class Expense(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A single clinic expense record — always in COP cents."""

    __tablename__ = "expenses"
    __table_args__ = (
        Index("idx_expenses_category", "category_id"),
        Index("idx_expenses_date", "expense_date"),
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("expense_categories.id"), nullable=False,
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
