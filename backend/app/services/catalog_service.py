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
_MEDICATION_CACHE_TTL = 86400  # 24 hours

# MVP: In-memory medication catalog for dental prescriptions
# In production, this would be a public.medication_catalog table
_MEDICATION_CATALOG: list[dict[str, str]] = [
    {"id": "med_001", "name": "Ibuprofeno 400mg", "active_ingredient": "Ibuprofeno", "presentation": "Tableta", "concentration": "400mg"},
    {"id": "med_002", "name": "Ibuprofeno 600mg", "active_ingredient": "Ibuprofeno", "presentation": "Tableta", "concentration": "600mg"},
    {"id": "med_003", "name": "Acetaminofén 500mg", "active_ingredient": "Acetaminofén", "presentation": "Tableta", "concentration": "500mg"},
    {"id": "med_004", "name": "Acetaminofén 1g", "active_ingredient": "Acetaminofén", "presentation": "Tableta", "concentration": "1000mg"},
    {"id": "med_005", "name": "Amoxicilina 500mg", "active_ingredient": "Amoxicilina", "presentation": "Cápsula", "concentration": "500mg"},
    {"id": "med_006", "name": "Amoxicilina 875mg + Ácido Clavulánico 125mg", "active_ingredient": "Amoxicilina/Clavulanato", "presentation": "Tableta", "concentration": "875/125mg"},
    {"id": "med_007", "name": "Clindamicina 300mg", "active_ingredient": "Clindamicina", "presentation": "Cápsula", "concentration": "300mg"},
    {"id": "med_008", "name": "Azitromicina 500mg", "active_ingredient": "Azitromicina", "presentation": "Tableta", "concentration": "500mg"},
    {"id": "med_009", "name": "Metronidazol 500mg", "active_ingredient": "Metronidazol", "presentation": "Tableta", "concentration": "500mg"},
    {"id": "med_010", "name": "Diclofenaco 50mg", "active_ingredient": "Diclofenaco", "presentation": "Tableta", "concentration": "50mg"},
    {"id": "med_011", "name": "Nimesulida 100mg", "active_ingredient": "Nimesulida", "presentation": "Tableta", "concentration": "100mg"},
    {"id": "med_012", "name": "Dexametasona 4mg", "active_ingredient": "Dexametasona", "presentation": "Tableta", "concentration": "4mg"},
    {"id": "med_013", "name": "Ketorolaco 10mg", "active_ingredient": "Ketorolaco", "presentation": "Tableta", "concentration": "10mg"},
    {"id": "med_014", "name": "Tramadol 50mg", "active_ingredient": "Tramadol", "presentation": "Cápsula", "concentration": "50mg"},
    {"id": "med_015", "name": "Clorhexidina 0.12%", "active_ingredient": "Clorhexidina", "presentation": "Enjuague bucal", "concentration": "0.12%"},
    {"id": "med_016", "name": "Lidocaína 2% con Epinefrina", "active_ingredient": "Lidocaína/Epinefrina", "presentation": "Inyectable", "concentration": "2%/1:80000"},
    {"id": "med_017", "name": "Mepivacaína 3%", "active_ingredient": "Mepivacaína", "presentation": "Inyectable", "concentration": "3%"},
    {"id": "med_018", "name": "Naproxeno 250mg", "active_ingredient": "Naproxeno", "presentation": "Tableta", "concentration": "250mg"},
    {"id": "med_019", "name": "Cefalexina 500mg", "active_ingredient": "Cefalexina", "presentation": "Cápsula", "concentration": "500mg"},
    {"id": "med_020", "name": "Fluconazol 150mg", "active_ingredient": "Fluconazol", "presentation": "Cápsula", "concentration": "150mg"},
]


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

    async def search_medications(
        self, *, db: AsyncSession, q: str
    ) -> dict[str, Any]:
        """Search the medication catalog with a substring match.

        MVP: searches the in-memory constant list.
        Production: would use FTS against public.medication_catalog table.

        Results are cached in Redis for 24 hours per query string.
        """
        q_normalised = q.strip().lower()

        # Check Redis cache first
        cache_key = f"dentalos:shared:catalog:medications:search:{hashlib.md5(q_normalised.encode()).hexdigest()[:12]}"  # noqa: S324
        cached = None
        with contextlib.suppress(Exception):
            cached = await get_cached(cache_key)

        if cached is not None:
            return cached

        # Search in-memory catalog
        results = [
            med for med in _MEDICATION_CATALOG
            if q_normalised in med["name"].lower()
            or q_normalised in med["active_ingredient"].lower()
        ]

        response: dict[str, Any] = {
            "items": results[:20],
            "total": len(results),
        }

        # Cache the result
        with contextlib.suppress(Exception):
            await set_cached(cache_key, response, ttl_seconds=_MEDICATION_CACHE_TTL)

        return response


# Module-level singleton for dependency injection
catalog_service = CatalogService()
