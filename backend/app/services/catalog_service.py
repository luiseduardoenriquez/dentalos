"""Catalog service — full-text search over CIE-10 and CUPS shared catalogs.

Security invariants:
  - Catalog tables live in the public schema (shared across all tenants).
  - Results are cached in Redis with a 1-hour TTL to avoid hammering
    PostgreSQL for high-frequency type-ahead searches.
  - Cache keys use an MD5 hash of the query so PHI-adjacent terms (e.g.
    a patient's diagnosis keyword) are never stored verbatim in Redis.
  - Raw SQL (text()) is used exclusively for the FTS queries because
    websearch_to_tsquery / ts_rank cannot be expressed via the ORM.
    All parameters are bound — no string interpolation.
  - If Redis is unavailable, the fallthrough to PostgreSQL is transparent
    and silent (contextlib.suppress on all cache operations).
"""

import contextlib
import hashlib
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cached, set_cached

logger = logging.getLogger("dentalos.catalog")

# ─── Constants ────────────────────────────────────────────────────────────────

_CIE10_CACHE_TTL = 3600   # 1 hour — catalog changes are infrequent
_CUPS_CACHE_TTL = 3600    # 1 hour


# ─── Cache helpers ────────────────────────────────────────────────────────────


def _cie10_cache_key(q: str) -> str:
    """Stable, PHI-safe cache key for a CIE-10 FTS query.

    Uses the first 12 hex characters of the MD5 of the normalised query
    string. This matches the pattern used in patient_service for consistency.
    """
    q_hash = hashlib.md5(q.encode()).hexdigest()[:12]  # noqa: S324
    return f"dentalos:shared:catalog:cie10:search:{q_hash}"


def _cups_cache_key(q: str) -> str:
    """Stable, PHI-safe cache key for a CUPS FTS query."""
    q_hash = hashlib.md5(q.encode()).hexdigest()[:12]  # noqa: S324
    return f"dentalos:shared:catalog:cups:search:{q_hash}"


# ─── Catalog Service ──────────────────────────────────────────────────────────


class CatalogService:
    """Stateless catalog service for shared CIE-10 and CUPS code lookups.

    Both search methods follow the same flow:
      1. Normalize query.
      2. Check Redis cache — return immediately on hit.
      3. Run FTS query against the public schema table.
         Primary: websearch_to_tsquery on the Spanish description.
         ILIKE fallback: code prefix match so numeric-only queries work.
      4. Cache and return result.

    The db session already has search_path set to the tenant schema + public
    by the time it arrives here. Because cie10_catalog and cups_catalog live
    in public, they are always reachable via the unqualified table name.
    """

    async def search_cie10(
        self,
        *,
        db: AsyncSession,
        q: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Full-text search over the shared CIE-10 diagnosis code catalog.

        Returns ranked results from PostgreSQL FTS on the Spanish description,
        with a code ILIKE fallback so that queries like "K02" return exact
        code-prefix matches even when the FTS tokenizer ranks them lower.

        Results are cached for 1 hour because the catalog is static data.

        Args:
            q: Free-text query (e.g. "caries", "K02.1", "periodont").
            limit: Maximum number of results to return (default 20).

        Returns:
            dict with keys: items (list of code/description/category dicts),
            total (number of items returned), query (normalised query string).
        """
        q_normalized = q.strip().lower()
        cache_key = _cie10_cache_key(q_normalized)

        # 1. Cache hit
        cached = await get_cached(cache_key)
        if cached is not None:
            return cached

        # 2. FTS + code-prefix search (raw SQL — FTS functions require text())
        query = text("""
            SELECT code, description, category
            FROM public.cie10_catalog
            WHERE to_tsvector('spanish', description) @@ websearch_to_tsquery('spanish', :q)
               OR code ILIKE :prefix
            ORDER BY ts_rank(
                to_tsvector('spanish', description),
                websearch_to_tsquery('spanish', :q)
            ) DESC
            LIMIT :limit
        """)

        result = await db.execute(
            query,
            {"q": q_normalized, "prefix": q_normalized + "%", "limit": limit},
        )
        rows = result.mappings().all()

        items = [
            {
                "code": row["code"],
                "description": row["description"],
                "category": row["category"],
            }
            for row in rows
        ]

        response: dict[str, Any] = {
            "items": items,
            "total": len(items),
            "query": q_normalized,
        }

        # 3. Cache result — suppress errors so Redis downtime does not break search
        with contextlib.suppress(Exception):
            await set_cached(cache_key, response, ttl_seconds=_CIE10_CACHE_TTL)

        return response

    async def search_cups(
        self,
        *,
        db: AsyncSession,
        q: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Full-text search over the shared CUPS procedure code catalog.

        Mirrors search_cie10 but targets public.cups_catalog. CUPS codes are
        6-digit numeric strings (e.g. "890202"), so the ILIKE fallback is
        particularly useful for clinicians who remember the numeric prefix.

        Results are cached for 1 hour because the catalog is static data.

        Args:
            q: Free-text query (e.g. "extraccion", "890202", "resina").
            limit: Maximum number of results to return (default 20).

        Returns:
            dict with keys: items (list of code/description/category dicts),
            total (number of items returned), query (normalised query string).
        """
        q_normalized = q.strip().lower()
        cache_key = _cups_cache_key(q_normalized)

        # 1. Cache hit
        cached = await get_cached(cache_key)
        if cached is not None:
            return cached

        # 2. FTS + code-prefix search (raw SQL — FTS functions require text())
        query = text("""
            SELECT code, description, category
            FROM public.cups_catalog
            WHERE to_tsvector('spanish', description) @@ websearch_to_tsquery('spanish', :q)
               OR code ILIKE :prefix
            ORDER BY ts_rank(
                to_tsvector('spanish', description),
                websearch_to_tsquery('spanish', :q)
            ) DESC
            LIMIT :limit
        """)

        result = await db.execute(
            query,
            {"q": q_normalized, "prefix": q_normalized + "%", "limit": limit},
        )
        rows = result.mappings().all()

        items = [
            {
                "code": row["code"],
                "description": row["description"],
                "category": row["category"],
            }
            for row in rows
        ]

        response: dict[str, Any] = {
            "items": items,
            "total": len(items),
            "query": q_normalized,
        }

        # 3. Cache result
        with contextlib.suppress(Exception):
            await set_cached(cache_key, response, ttl_seconds=_CUPS_CACHE_TTL)

        return response


# Module-level singleton for dependency injection
catalog_service = CatalogService()
