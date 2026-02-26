"""Compliance configuration service with Redis caching."""

import json
import logging

from app.compliance.colombia.config import (
    CODE_SYSTEMS,
    DOCUMENT_TYPES,
    FEATURE_FLAGS,
    REGULATORY_REFERENCES,
    RETENTION_RULES,
)
from app.core.cache import redis_client
from app.schemas.compliance import CountryConfigResponse

logger = logging.getLogger("dentalos.compliance.config")

_CACHE_TTL = 3600  # 1 hour
_CACHE_KEY_PREFIX = "dentalos:global:compliance_config"


async def get_country_config(
    country_code: str,
    lang: str = "es",
) -> CountryConfigResponse:
    """Return the compliance configuration for a country.

    Uses Redis cache with 1-hour TTL. Falls through to static config
    if Redis is unavailable.
    """
    cache_key = f"{_CACHE_KEY_PREFIX}:{country_code}:{lang}"

    # Try cache first
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            data = json.loads(cached)
            return CountryConfigResponse(**data)
    except Exception:
        logger.debug("Redis cache miss or unavailable for %s", cache_key)

    # Build response from static config
    if country_code == "CO":
        config = CountryConfigResponse(
            country_code="CO",
            country_name="Colombia",
            procedure_code_system="CUPS",
            document_types=DOCUMENT_TYPES,
            code_systems=CODE_SYSTEMS,
            retention_rules=RETENTION_RULES,
            regulatory_references=REGULATORY_REFERENCES,
            feature_flags=FEATURE_FLAGS,
        )
    else:
        config = CountryConfigResponse(
            country_code=country_code,
            country_name=country_code,
            procedure_code_system="unknown",
            document_types=[],
            code_systems={},
            retention_rules={},
            regulatory_references=[],
            feature_flags={},
        )

    # Cache the result
    try:
        await redis_client.setex(cache_key, _CACHE_TTL, config.model_dump_json())
    except Exception:
        logger.debug("Failed to cache compliance config for %s", cache_key)

    return config
