"""Service catalog service — list, fetch, and update the per-tenant CUPS price list.

Security invariants:
  - cups_code is IMMUTABLE after creation. update_service explicitly refuses
    to accept a cups_code argument, and the method never writes that column.
    This is a service-layer invariant; the DB constraint is a UNIQUE index
    rather than an immutability check, so enforcement must live here.
  - All monetary values are stored in COP cents (integer). The service layer
    does not perform currency conversion — that is the caller's responsibility.
  - Soft-delete is not implemented for service catalog entries because they
    carry no PHI and are not subject to Resolución 1888. Inactive entries
    (is_active=False) are retained for historical billing references.
  - PHI is not present in this domain — no special logging restrictions
    beyond the standard practice of not logging user-supplied strings verbatim.
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.models.tenant.service_catalog import ServiceCatalog

logger = logging.getLogger("dentalos.service_catalog")


# ─── Serialization helper ─────────────────────────────────────────────────────


def _service_to_dict(service: ServiceCatalog) -> dict[str, Any]:
    """Serialize a ServiceCatalog ORM instance to a plain dict."""
    return {
        "id": str(service.id),
        "cups_code": service.cups_code,
        "name": service.name,
        "default_price": service.default_price,
        "category": service.category,
        "is_active": service.is_active,
        "created_at": service.created_at,
        "updated_at": service.updated_at,
    }


# ─── Service Catalog Service ──────────────────────────────────────────────────


class ServiceCatalogService:
    """Stateless service catalog service.

    All methods accept primitive arguments and an AsyncSession so they can
    be called from API routes, workers, CLI scripts, and tests without
    coupling to HTTP concerns.

    The search_path for each method is already set by get_tenant_db().
    Methods do NOT call SET search_path themselves — the session is already
    scoped to the correct tenant schema by the time it arrives here.

    Pagination uses cursor-based pagination (keyed on cups_code ASC) rather
    than offset-based pagination because service catalogs can grow to
    thousands of entries and offset scans degrade linearly at depth.
    """

    async def list_services(
        self,
        *,
        db: AsyncSession,
        cursor: str | None = None,
        limit: int = 20,
        category: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """Return a cursor-paginated list of services.

        The cursor is the last seen cups_code value. Items with cups_code
        strictly greater than the cursor are returned, allowing efficient
        keyset pagination over large catalogs.

        Filters:
          - category: Restrict to entries in this service category.
          - search: Case-insensitive ILIKE match against name or cups_code.

        Args:
            cursor: Last cups_code from the previous page. None = first page.
            limit: Maximum number of results per page (default 20).
            category: Optional category filter (one of the CHECK constraint values).
            search: Optional free-text ILIKE filter on name / cups_code.

        Returns:
            dict with keys: items, next_cursor (str | None), has_more (bool).
        """
        stmt = select(ServiceCatalog).order_by(ServiceCatalog.cups_code.asc())

        if cursor is not None:
            stmt = stmt.where(ServiceCatalog.cups_code > cursor)

        if category is not None:
            stmt = stmt.where(ServiceCatalog.category == category)

        if search is not None:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                ServiceCatalog.name.ilike(pattern)
                | ServiceCatalog.cups_code.ilike(pattern)
            )

        # Fetch one extra row to determine whether there is a next page
        stmt = stmt.limit(limit + 1)

        result = await db.execute(stmt)
        services = list(result.scalars().all())

        has_more = len(services) > limit
        if has_more:
            services = services[:limit]

        next_cursor: str | None = services[-1].cups_code if has_more else None

        return {
            "items": [_service_to_dict(s) for s in services],
            "next_cursor": next_cursor,
            "has_more": has_more,
        }

    async def get_service(
        self,
        *,
        db: AsyncSession,
        service_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single service catalog entry by ID.

        Returns None when the service does not exist or is inactive.
        The caller is responsible for converting None to a 404 response.
        """
        result = await db.execute(
            select(ServiceCatalog).where(
                ServiceCatalog.id == uuid.UUID(service_id),
                ServiceCatalog.is_active.is_(True),
            )
        )
        service = result.scalar_one_or_none()

        if service is None:
            return None

        return _service_to_dict(service)

    async def update_service(
        self,
        *,
        db: AsyncSession,
        service_id: str,
        name: str | None = None,
        default_price: int | None = None,
        category: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        """Apply partial updates to an existing service catalog entry.

        Only non-None arguments are applied. cups_code is intentionally NOT
        a parameter — it is immutable after creation. Passing it would be a
        caller error and is rejected at the schema (Pydantic) layer upstream.

        Raises:
            ResourceNotFoundError (404) — service not found or inactive
                                          (active-only fetch guards the update).
        """
        result = await db.execute(
            select(ServiceCatalog).where(
                ServiceCatalog.id == uuid.UUID(service_id),
                ServiceCatalog.is_active.is_(True),
            )
        )
        service = result.scalar_one_or_none()

        if service is None:
            raise ResourceNotFoundError(
                error="CLINICAL_service_not_found",
                resource_name="ServiceCatalog",
            )

        # Apply non-None updates (cups_code is NEVER updated — immutable)
        if name is not None:
            service.name = name
        if default_price is not None:
            service.default_price = default_price
        if category is not None:
            service.category = category
        if is_active is not None:
            service.is_active = is_active

        await db.flush()

        logger.info(
            "ServiceCatalog updated: id=%s cups_code=%s",
            str(service.id)[:8],
            service.cups_code,
        )

        return _service_to_dict(service)


# Module-level singleton for dependency injection
service_catalog_service = ServiceCatalogService()
