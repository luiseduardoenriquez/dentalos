"""Inventory service — items, quantity history, sterilization, implant placements.

Business invariants enforced here:
  - Only category='instrument' items may appear in sterilization loads.
  - Only category='implant' items may be linked via implant placements.
  - Implant placement decrements quantity atomically with a consumed history row.
  - SHA-256 verification of signature_data when both fields are provided.
  - Sterilization (autoclave_id, load_number, date) uniqueness checked before insert.
  - Quantity never goes below 0 on implant placement.
  - Soft delete for inventory items (is_active + deleted_at).
  - Quantity history, sterilization records, and implant placements are immutable.
"""

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessValidationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.models.tenant.inventory import (
    ImplantPlacement,
    InventoryItem,
    InventoryQuantityHistory,
    SterilizationRecord,
    SterilizationRecordInstrument,
)

logger = logging.getLogger("dentalos.inventory")


def _item_to_dict(item: InventoryItem) -> dict[str, Any]:
    """Serialize an InventoryItem ORM instance to a plain dict."""
    return {
        "id": str(item.id),
        "name": item.name,
        "category": item.category,
        "quantity": item.quantity,
        "unit": item.unit,
        "lot_number": item.lot_number,
        "expiry_date": item.expiry_date,
        "expiry_status": item.expiry_status,
        "manufacturer": item.manufacturer,
        "supplier": item.supplier,
        "cost_per_unit": item.cost_per_unit,
        "minimum_stock": item.minimum_stock,
        "location": item.location,
        "created_by": str(item.created_by),
        "is_active": item.is_active,
        "deleted_at": item.deleted_at,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _history_to_dict(h: InventoryQuantityHistory) -> dict[str, Any]:
    """Serialize an InventoryQuantityHistory ORM instance to a plain dict."""
    return {
        "id": str(h.id),
        "item_id": str(h.item_id),
        "quantity_change": h.quantity_change,
        "reason": h.reason,
        "previous_quantity": h.previous_quantity,
        "new_quantity": h.new_quantity,
        "notes": h.notes,
        "created_by": str(h.created_by),
        "created_at": h.created_at,
    }


def _sterilization_to_dict(record: SterilizationRecord) -> dict[str, Any]:
    """Serialize a SterilizationRecord ORM instance to a plain dict."""
    instrument_ids = [
        str(j.inventory_item_id) for j in (record.instruments or [])
    ]
    return {
        "id": str(record.id),
        "autoclave_id": record.autoclave_id,
        "load_number": record.load_number,
        "date": record.date,
        "temperature_celsius": record.temperature_celsius,
        "duration_minutes": record.duration_minutes,
        "biological_indicator": record.biological_indicator,
        "chemical_indicator": record.chemical_indicator,
        "responsible_user_id": str(record.responsible_user_id),
        "is_compliant": record.is_compliant,
        "instrument_ids": instrument_ids,
        "signature_data": record.signature_data,
        "signature_sha256_hash": record.signature_sha256_hash,
        "notes": record.notes,
        "created_by": str(record.created_by),
        "created_at": record.created_at,
    }


def _placement_to_dict(p: ImplantPlacement) -> dict[str, Any]:
    """Serialize an ImplantPlacement ORM instance to a plain dict."""
    return {
        "id": str(p.id),
        "item_id": str(p.item_id),
        "patient_id": str(p.patient_id),
        "procedure_id": str(p.procedure_id) if p.procedure_id else None,
        "tooth_number": p.tooth_number,
        "placement_date": p.placement_date,
        "serial_number": p.serial_number,
        "lot_number": p.lot_number,
        "manufacturer": p.manufacturer,
        "notes": p.notes,
        "created_by": str(p.created_by),
        "created_at": p.created_at,
    }


class InventoryService:
    """Stateless inventory service.

    All methods accept an AsyncSession already scoped to the correct tenant
    schema by get_tenant_db(). Methods do NOT call SET search_path themselves.
    """

    # ─── Inventory Items ─────────────────────────────────────────────────

    async def create_item(
        self,
        *,
        db: AsyncSession,
        created_by_id: str,
        name: str,
        category: str,
        quantity: Decimal,
        unit: str,
        lot_number: str | None = None,
        expiry_date: Any | None = None,
        manufacturer: str | None = None,
        supplier: str | None = None,
        cost_per_unit: int | None = None,
        minimum_stock: Decimal | None = None,
        location: str | None = None,
    ) -> dict[str, Any]:
        """Create a new inventory item.

        Returns the persisted item dict including server-computed expiry_status.
        session.refresh() is called after flush to load the generated column.
        """
        item = InventoryItem(
            name=name.strip(),
            category=category,
            quantity=quantity,
            unit=unit,
            lot_number=lot_number,
            expiry_date=expiry_date,
            manufacturer=manufacturer,
            supplier=supplier,
            cost_per_unit=cost_per_unit,
            minimum_stock=minimum_stock if minimum_stock is not None else Decimal(0),
            location=location,
            created_by=uuid.UUID(created_by_id),
            is_active=True,
        )
        db.add(item)
        await db.flush()
        # Refresh to pick up persisted computed column (expiry_status)
        await db.refresh(item)

        logger.info("Inventory item created id=%s category=%s", str(item.id)[:8], category)
        return _item_to_dict(item)

    async def list_items(
        self,
        *,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        expiry_status: str | None = None,
        low_stock: bool | None = None,
    ) -> dict[str, Any]:
        """Return a paginated list of active inventory items with optional filters."""
        stmt = select(InventoryItem).where(InventoryItem.is_active.is_(True))

        if category is not None:
            stmt = stmt.where(InventoryItem.category == category)

        if expiry_status is not None:
            stmt = stmt.where(InventoryItem.expiry_status == expiry_status)

        if low_stock:
            # Items where quantity is at or below minimum_stock (and minimum_stock > 0)
            stmt = stmt.where(
                and_(
                    InventoryItem.quantity <= InventoryItem.minimum_stock,
                    InventoryItem.minimum_stock > 0,
                )
            )

        # Total count before pagination
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # Apply ordering and pagination
        stmt = (
            stmt.order_by(InventoryItem.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await db.execute(stmt)
        items = result.scalars().all()

        return {
            "items": [_item_to_dict(i) for i in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_item(
        self,
        *,
        db: AsyncSession,
        item_id: str,
        created_by_id: str,
        name: str | None = None,
        quantity_change: Decimal | None = None,
        change_reason: str | None = None,
        change_notes: str | None = None,
        lot_number: str | None = None,
        expiry_date: Any | None = None,
        manufacturer: str | None = None,
        supplier: str | None = None,
        cost_per_unit: int | None = None,
        minimum_stock: Decimal | None = None,
        location: str | None = None,
    ) -> dict[str, Any]:
        """Apply partial updates to an active inventory item.

        If quantity_change is provided, change_reason must also be provided.
        A QuantityHistory row is created atomically with the quantity update.

        Raises:
            ResourceNotFoundError (404) — item not found or inactive.
            BusinessValidationError (422) — quantity_change without reason, or
                                            resulting quantity would be negative.
        """
        result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.id == uuid.UUID(item_id),
                InventoryItem.is_active.is_(True),
            )
        )
        item = result.scalar_one_or_none()

        if item is None:
            raise ResourceNotFoundError(
                error="INVENTORY_item_not_found",
                resource_name="InventoryItem",
            )

        # Validate quantity change prerequisites
        if quantity_change is not None and change_reason is None:
            raise BusinessValidationError(
                "change_reason is required when quantity_change is provided.",
                field_errors={"change_reason": ["Este campo es obligatorio cuando se cambia la cantidad."]},
            )

        # Apply scalar field updates (non-None only)
        if name is not None:
            item.name = name.strip()
        if lot_number is not None:
            item.lot_number = lot_number
        if expiry_date is not None:
            item.expiry_date = expiry_date
        if manufacturer is not None:
            item.manufacturer = manufacturer
        if supplier is not None:
            item.supplier = supplier
        if cost_per_unit is not None:
            item.cost_per_unit = cost_per_unit
        if minimum_stock is not None:
            item.minimum_stock = minimum_stock
        if location is not None:
            item.location = location

        # Quantity change with history row
        if quantity_change is not None:
            previous_qty = Decimal(str(item.quantity))
            new_qty = previous_qty + quantity_change

            if new_qty < 0:
                raise BusinessValidationError(
                    "La cantidad resultante no puede ser negativa.",
                    field_errors={"quantity_change": [
                        f"La cantidad actual es {previous_qty}. "
                        f"El cambio de {quantity_change} resultaría en {new_qty}."
                    ]},
                )

            item.quantity = new_qty

            history = InventoryQuantityHistory(
                item_id=item.id,
                quantity_change=quantity_change,
                reason=change_reason,
                previous_quantity=previous_qty,
                new_quantity=new_qty,
                notes=change_notes,
                created_by=uuid.UUID(created_by_id),
            )
            db.add(history)

        await db.flush()
        # Refresh to pick up updated computed column (expiry_status may change)
        await db.refresh(item)

        logger.info("Inventory item updated id=%s", item_id[:8])
        return _item_to_dict(item)

    async def get_alerts(self, *, db: AsyncSession) -> dict[str, Any]:
        """Return grouped alert lists: expired, critical expiry, and low stock.

        Three separate queries — each returns only active items.
        """
        # Expired items
        expired_result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.is_active.is_(True),
                InventoryItem.expiry_status == "expired",
            ).order_by(InventoryItem.expiry_date.asc())
        )
        expired = expired_result.scalars().all()

        # Critical expiry items (1-30 days)
        critical_result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.is_active.is_(True),
                InventoryItem.expiry_status == "critical",
            ).order_by(InventoryItem.expiry_date.asc())
        )
        critical = critical_result.scalars().all()

        # Low stock items (quantity <= minimum_stock AND minimum_stock > 0)
        low_stock_result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.is_active.is_(True),
                InventoryItem.quantity <= InventoryItem.minimum_stock,
                InventoryItem.minimum_stock > 0,
            ).order_by(InventoryItem.quantity.asc())
        )
        low_stock = low_stock_result.scalars().all()

        def _alert_dict(item: InventoryItem) -> dict[str, Any]:
            return {
                "id": str(item.id),
                "name": item.name,
                "category": item.category,
                "quantity": item.quantity,
                "expiry_status": item.expiry_status,
                "expiry_date": item.expiry_date,
                "minimum_stock": item.minimum_stock,
            }

        return {
            "expired": [_alert_dict(i) for i in expired],
            "critical": [_alert_dict(i) for i in critical],
            "low_stock": [_alert_dict(i) for i in low_stock],
        }

    # ─── Sterilization Records ───────────────────────────────────────────

    async def create_sterilization(
        self,
        *,
        db: AsyncSession,
        created_by_id: str,
        autoclave_id: str,
        load_number: str,
        date: Any,
        responsible_user_id: str,
        instrument_ids: list[str],
        temperature_celsius: Any | None = None,
        duration_minutes: int | None = None,
        biological_indicator: str | None = None,
        chemical_indicator: str | None = None,
        signature_data: str | None = None,
        signature_sha256_hash: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Create a sterilization record for an autoclave load.

        Validates:
          - All instrument_ids exist and are category='instrument'.
          - SHA-256 hash matches signature_data when both are provided.
          - (autoclave_id, load_number, date) is unique.

        Raises:
            BusinessValidationError (422) — validation failures.
            ResourceConflictError (409) — duplicate load.
        """
        # Validate all instrument IDs exist and are category='instrument'
        if not instrument_ids:
            raise BusinessValidationError(
                "Se requiere al menos un instrumento por carga.",
                field_errors={"instrument_ids": ["Debe incluir al menos un instrumento."]},
            )

        instrument_uuids = [uuid.UUID(iid) for iid in instrument_ids]
        items_result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.id.in_(instrument_uuids),
                InventoryItem.is_active.is_(True),
            )
        )
        found_items = items_result.scalars().all()
        found_ids = {i.id for i in found_items}

        missing = [str(iid) for iid in instrument_uuids if iid not in found_ids]
        if missing:
            raise BusinessValidationError(
                "Algunos instrumentos no fueron encontrados.",
                field_errors={"instrument_ids": [f"No encontrados: {', '.join(missing)}"]},
            )

        non_instruments = [
            str(i.id) for i in found_items if i.category != "instrument"
        ]
        if non_instruments:
            raise BusinessValidationError(
                "Solo se permiten instrumentos en los registros de esterilización.",
                field_errors={"instrument_ids": [
                    f"Los siguientes ítems no son instrumentos: {', '.join(non_instruments)}"
                ]},
            )

        # Verify SHA-256 when both signature fields are provided
        if signature_data is not None and signature_sha256_hash is not None:
            computed_hash = hashlib.sha256(signature_data.encode()).hexdigest()
            if computed_hash != signature_sha256_hash:
                raise BusinessValidationError(
                    "La firma digital no coincide con el hash SHA-256 proporcionado.",
                    field_errors={"signature_sha256_hash": ["Hash SHA-256 inválido."]},
                )

        # Check uniqueness (autoclave_id, load_number, date)
        existing_check = await db.execute(
            select(SterilizationRecord.id).where(
                SterilizationRecord.autoclave_id == autoclave_id,
                SterilizationRecord.load_number == load_number,
                SterilizationRecord.date == date,
            )
        )
        if existing_check.scalar_one_or_none() is not None:
            raise ResourceConflictError(
                error="INVENTORY_sterilization_duplicate_load",
                message=(
                    f"Ya existe un registro de esterilización para el autoclave "
                    f"'{autoclave_id}', carga '{load_number}', fecha '{date}'."
                ),
            )

        # Create the sterilization record
        record = SterilizationRecord(
            autoclave_id=autoclave_id,
            load_number=load_number,
            date=date,
            temperature_celsius=temperature_celsius,
            duration_minutes=duration_minutes,
            biological_indicator=biological_indicator,
            chemical_indicator=chemical_indicator,
            responsible_user_id=uuid.UUID(responsible_user_id),
            signature_data=signature_data,
            signature_sha256_hash=signature_sha256_hash,
            notes=notes,
            created_by=uuid.UUID(created_by_id),
        )
        db.add(record)
        await db.flush()  # Get record.id for junction rows

        # Insert junction rows for each instrument
        for item_uuid in instrument_uuids:
            junction = SterilizationRecordInstrument(
                sterilization_record_id=record.id,
                inventory_item_id=item_uuid,
            )
            db.add(junction)

        await db.flush()
        await db.refresh(record)

        logger.info(
            "Sterilization record created id=%s autoclave=%s load=%s",
            str(record.id)[:8],
            autoclave_id,
            load_number,
        )
        return _sterilization_to_dict(record)

    async def list_sterilization(
        self,
        *,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        date_from: Any | None = None,
        date_to: Any | None = None,
        autoclave_id: str | None = None,
        compliant_only: bool | None = None,
    ) -> dict[str, Any]:
        """Return a paginated list of sterilization records with optional filters."""
        from sqlalchemy import func

        stmt = select(SterilizationRecord)

        if date_from is not None:
            stmt = stmt.where(SterilizationRecord.date >= date_from)
        if date_to is not None:
            stmt = stmt.where(SterilizationRecord.date <= date_to)
        if autoclave_id is not None:
            stmt = stmt.where(SterilizationRecord.autoclave_id == autoclave_id)
        if compliant_only:
            stmt = stmt.where(SterilizationRecord.is_compliant.is_(True))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            stmt.order_by(SterilizationRecord.date.desc(), SterilizationRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await db.execute(stmt)
        records = result.scalars().all()

        return {
            "items": [_sterilization_to_dict(r) for r in records],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ─── Implant Placements ──────────────────────────────────────────────

    async def link_implant(
        self,
        *,
        db: AsyncSession,
        created_by_id: str,
        item_id: str,
        patient_id: str,
        placement_date: Any,
        procedure_id: str | None = None,
        tooth_number: int | None = None,
        serial_number: str | None = None,
        lot_number: str | None = None,
        manufacturer: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Atomically link an implant to a patient and decrement inventory.

        Steps (single flush):
          1. Load and validate the item (must be category='implant', quantity > 0).
          2. Decrement item.quantity by 1.
          3. Create QuantityHistory row (reason='consumed').
          4. Create ImplantPlacement record.

        Raises:
            ResourceNotFoundError (404) — item not found or inactive.
            BusinessValidationError (422) — not an implant, or zero stock.
        """
        result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.id == uuid.UUID(item_id),
                InventoryItem.is_active.is_(True),
            )
        )
        item = result.scalar_one_or_none()

        if item is None:
            raise ResourceNotFoundError(
                error="INVENTORY_item_not_found",
                resource_name="InventoryItem",
            )

        if item.category != "implant":
            raise BusinessValidationError(
                "Solo los ítems de categoría 'implant' pueden ser vinculados como implante.",
                field_errors={"item_id": ["El ítem seleccionado no es un implante."]},
            )

        previous_qty = Decimal(str(item.quantity))
        if previous_qty <= 0:
            raise BusinessValidationError(
                "No hay existencias disponibles de este implante.",
                field_errors={"item_id": ["La cantidad en inventario es 0."]},
            )

        new_qty = previous_qty - Decimal("1")
        item.quantity = new_qty

        # Quantity history row (reason='consumed')
        history = InventoryQuantityHistory(
            item_id=item.id,
            quantity_change=Decimal("-1"),
            reason="consumed",
            previous_quantity=previous_qty,
            new_quantity=new_qty,
            notes=f"Implante colocado — paciente {patient_id[:8]}",
            created_by=uuid.UUID(created_by_id),
        )
        db.add(history)

        # Implant placement record
        placement = ImplantPlacement(
            item_id=item.id,
            patient_id=uuid.UUID(patient_id),
            procedure_id=uuid.UUID(procedure_id) if procedure_id else None,
            tooth_number=tooth_number,
            placement_date=placement_date,
            serial_number=serial_number,
            lot_number=lot_number,
            manufacturer=manufacturer,
            notes=notes,
            created_by=uuid.UUID(created_by_id),
        )
        db.add(placement)

        # Single flush for atomicity — all three changes committed together
        await db.flush()
        await db.refresh(item)
        await db.refresh(placement)

        logger.info(
            "Implant placed item=%s patient=%s",
            item_id[:8],
            patient_id[:8],
        )
        return _placement_to_dict(placement)

    async def search_implants(
        self,
        *,
        db: AsyncSession,
        lot_number: str | None = None,
        patient_id: str | None = None,
    ) -> dict[str, Any]:
        """Search implant placement records.

        Supports:
          - lot_number: ILIKE search for implant recall scenarios.
          - patient_id: exact match to retrieve all implants for a patient.

        At least one filter must be provided.

        Raises:
            BusinessValidationError (422) — neither filter provided.
        """
        if lot_number is None and patient_id is None:
            raise BusinessValidationError(
                "Se requiere al menos un filtro: lot_number o patient_id.",
                field_errors={
                    "lot_number": ["Provea lot_number o patient_id."],
                    "patient_id": ["Provea lot_number o patient_id."],
                },
            )

        stmt = select(ImplantPlacement)

        if lot_number is not None:
            stmt = stmt.where(ImplantPlacement.lot_number.ilike(f"%{lot_number}%"))

        if patient_id is not None:
            stmt = stmt.where(ImplantPlacement.patient_id == uuid.UUID(patient_id))

        stmt = stmt.order_by(ImplantPlacement.placement_date.desc())

        result = await db.execute(stmt)
        placements = result.scalars().all()

        return {
            "placements": [_placement_to_dict(p) for p in placements],
            "total": len(placements),
        }


# Module-level singleton for dependency injection
inventory_service = InventoryService()
