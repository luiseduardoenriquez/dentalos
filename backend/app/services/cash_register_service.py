"""Cash register service — open/close sessions and record movements.

Security invariants:
  - PHI is NEVER logged.
  - All monetary values in COP cents.
  - Only one register may be open at a time per tenant.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.error_codes import CashRegisterErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.models.tenant.cash_register import CashMovement, CashRegister

logger = logging.getLogger("dentalos.cash_register")


class CashRegisterService:
    """Stateless cash register service."""

    # ── Open / Close ─────────────────────────────────────────────────────────

    async def open_register(
        self,
        *,
        db: AsyncSession,
        user_id: uuid.UUID,
        name: str,
        location: str | None,
        opening_balance_cents: int,
    ) -> dict[str, Any]:
        """Open a new cash register session.

        Raises ALREADY_OPEN if another register is currently open.
        """
        # Guard: only one open register at a time
        existing = await db.execute(
            select(CashRegister.id).where(CashRegister.status == "open")
        )
        if existing.scalar_one_or_none() is not None:
            raise DentalOSError(
                error=CashRegisterErrors.ALREADY_OPEN,
                message="Ya existe una caja abierta. Ciérrela antes de abrir una nueva.",
                status_code=409,
            )

        register = CashRegister(
            name=name,
            location=location,
            status="open",
            opened_by=user_id,
            opened_at=datetime.now(UTC),
            opening_balance_cents=opening_balance_cents,
        )
        db.add(register)
        await db.flush()
        await db.refresh(register)
        logger.info("Cash register opened: id=%s", str(register.id)[:8])
        return self._register_to_dict(register)

    async def close_register(
        self,
        *,
        db: AsyncSession,
        user_id: uuid.UUID,
        register_id: uuid.UUID,
        closing_balance_cents: int,
    ) -> dict[str, Any]:
        """Close an open cash register session."""
        register = await self._get_open_register(db, register_id)

        register.status = "closed"
        register.closed_by = user_id
        register.closed_at = datetime.now(UTC)
        register.closing_balance_cents = closing_balance_cents

        await db.flush()
        await db.refresh(register)
        logger.info("Cash register closed: id=%s", str(register.id)[:8])
        return self._register_to_dict(register)

    # ── Movements ────────────────────────────────────────────────────────────

    async def record_movement(
        self,
        *,
        db: AsyncSession,
        register_id: uuid.UUID,
        type: str,
        amount_cents: int,
        recorded_by: uuid.UUID,
        payment_method: str | None = None,
        reference_id: uuid.UUID | None = None,
        reference_type: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Record an income, expense, or adjustment movement in the register."""
        movement = CashMovement(
            register_id=register_id,
            type=type,
            amount_cents=amount_cents,
            payment_method=payment_method,
            reference_id=reference_id,
            reference_type=reference_type,
            description=description,
            recorded_by=recorded_by,
        )
        db.add(movement)
        await db.flush()
        await db.refresh(movement)
        logger.info(
            "Cash movement recorded: register=%s type=%s",
            str(register_id)[:8],
            type,
        )
        return self._movement_to_dict(movement)

    # ── Queries ──────────────────────────────────────────────────────────────

    async def get_current(self, *, db: AsyncSession) -> dict[str, Any] | None:
        """Return the currently open register with movements and computed totals, or None."""
        result = await db.execute(
            select(CashRegister)
            .options(selectinload(CashRegister.movements))
            .where(CashRegister.status == "open")
            .limit(1)
        )
        register = result.scalar_one_or_none()
        if register is None:
            return None

        movements = register.movements or []
        total_income = sum(m.amount_cents for m in movements if m.type == "income")
        total_expense = sum(m.amount_cents for m in movements if m.type == "expense")
        net_balance = register.opening_balance_cents + total_income - total_expense

        data = self._register_to_dict(register)
        data["movements"] = [self._movement_to_dict(m) for m in movements]
        data["total_income_cents"] = total_income
        data["total_expense_cents"] = total_expense
        data["net_balance_cents"] = net_balance
        return data

    async def get_history(
        self,
        *,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Return paginated list of closed cash register sessions."""
        offset = (page - 1) * page_size

        total = (
            await db.execute(
                select(func.count(CashRegister.id)).where(CashRegister.status == "closed")
            )
        ).scalar_one()

        result = await db.execute(
            select(CashRegister)
            .where(CashRegister.status == "closed")
            .order_by(CashRegister.closed_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        registers = result.scalars().all()

        return {
            "items": [self._register_to_dict(r) for r in registers],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ── Private Helpers ───────────────────────────────────────────────────────

    async def _get_open_register(
        self, db: AsyncSession, register_id: uuid.UUID,
    ) -> CashRegister:
        result = await db.execute(
            select(CashRegister).where(
                CashRegister.id == register_id,
                CashRegister.status == "open",
            )
        )
        register = result.scalar_one_or_none()
        if register is None:
            raise ResourceNotFoundError(
                error=CashRegisterErrors.NOT_FOUND,
                resource_name="CashRegister",
            )
        return register

    def _register_to_dict(self, register: CashRegister) -> dict[str, Any]:
        return {
            "id": str(register.id),
            "name": register.name,
            "location": register.location,
            "status": register.status,
            "opened_by": str(register.opened_by) if register.opened_by else None,
            "opened_at": register.opened_at,
            "opening_balance_cents": register.opening_balance_cents,
            "closing_balance_cents": register.closing_balance_cents,
            "closed_by": str(register.closed_by) if register.closed_by else None,
            "closed_at": register.closed_at,
            "created_at": register.created_at,
            "updated_at": register.updated_at,
        }

    def _movement_to_dict(self, movement: CashMovement) -> dict[str, Any]:
        return {
            "id": str(movement.id),
            "register_id": str(movement.register_id),
            "type": movement.type,
            "amount_cents": movement.amount_cents,
            "payment_method": movement.payment_method,
            "reference_id": str(movement.reference_id) if movement.reference_id else None,
            "reference_type": movement.reference_type,
            "description": movement.description,
            "recorded_by": str(movement.recorded_by),
            "created_at": movement.created_at,
        }


cash_register_service = CashRegisterService()
