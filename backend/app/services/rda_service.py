"""RDA compliance service with Redis caching."""

import json
import logging
from datetime import date, datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.colombia.rda import compute_rda_status
from app.core.cache import get_cached, set_cached
from app.schemas.compliance import RDAStatusResponse

logger = logging.getLogger("dentalos.compliance.rda")

_CACHE_TTL = 3600  # 1 hour


async def get_rda_status(
    db: AsyncSession,
    tenant_id: str,
    refresh: bool = False,
    since_date: date | None = None,
) -> RDAStatusResponse:
    """Get RDA compliance status, with Redis caching.

    Args:
        db: Tenant-scoped database session.
        tenant_id: Tenant ID for cache key scoping.
        refresh: If True, bypass cache and recompute.
        since_date: Optional date filter for records.

    Returns:
        RDAStatusResponse with compliance metrics.
    """
    cache_key = f"dentalos:{tenant_id}:compliance:rda:status"

    # Try cache (unless refresh requested)
    if not refresh:
        try:
            cached = await get_cached(cache_key)
            if cached:
                response = RDAStatusResponse(**cached)
                response.cached = True
                return response
        except Exception:
            logger.debug("Redis cache miss for RDA status: %s", cache_key)

    # Compute fresh status
    status = await compute_rda_status(db, since_date=since_date)
    status.last_computed_at = datetime.now(UTC)

    # Cache result
    try:
        await set_cached(cache_key, json.loads(status.model_dump_json()), _CACHE_TTL)
    except Exception:
        logger.debug("Failed to cache RDA status: %s", cache_key)

    return status
