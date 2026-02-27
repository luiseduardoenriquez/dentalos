import asyncio
import logging
import platform
import time

import aio_pika
import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import generate_latest
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.metrics import REGISTRY, active_tenants, appointments_today, update_db_pool_stats
from app.core.redis import redis_client

logger = logging.getLogger("dentalos.health")

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/health")
async def health_check() -> JSONResponse:
    """System health check. Returns 503 only if the database is unreachable."""
    start = time.time()
    checks: dict[str, dict[str, str]] = {}

    # Database check (critical)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = {"status": "healthy"}
    except Exception:
        logger.error("Health check: database unreachable")
        checks["postgres"] = {"status": "unhealthy"}

    # Redis check (non-critical)
    try:
        await redis_client.ping()  # type: ignore[misc]
        checks["redis"] = {"status": "healthy"}
    except Exception:
        logger.warning("Health check: redis unreachable")
        checks["redis"] = {"status": "degraded"}

    # RabbitMQ check (non-critical)
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url, timeout=3)
        await connection.close()
        checks["rabbitmq"] = {"status": "healthy"}
    except Exception:
        logger.warning("Health check: rabbitmq unreachable")
        checks["rabbitmq"] = {"status": "degraded"}

    # MinIO/S3 check (non-critical) — run in thread to avoid blocking event loop
    try:

        def _check_s3() -> None:
            s3 = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
            )
            s3.head_bucket(Bucket=settings.s3_bucket_name)

        await asyncio.to_thread(_check_s3)
        checks["minio"] = {"status": "healthy"}
    except (ClientError, Exception):
        logger.warning("Health check: minio unreachable")
        checks["minio"] = {"status": "degraded"}

    # Collect DB pool stats for both health response and Prometheus
    pool = engine.pool
    pool_status = pool.status()
    pool_size = pool.size()
    pool_checked_in = pool.checkedin()
    pool_checked_out = pool.checkedout()
    pool_overflow = pool.overflow()
    update_db_pool_stats(pool_checked_in, pool_checked_out, pool_overflow)

    duration_ms = round((time.time() - start) * 1000)
    is_healthy = checks["postgres"]["status"] == "healthy"

    return JSONResponse(
        content={
            "status": "healthy" if is_healthy else "degraded",
            "version": settings.app_version,
            "environment": settings.environment,
            "hostname": platform.node(),
            "uptime_seconds": round(time.time() - _start_time),
            "services": checks,
            "pool": {
                "size": pool_size,
                "checked_in": pool_checked_in,
                "checked_out": pool_checked_out,
                "overflow": pool_overflow,
                "status": pool_status,
            },
            "duration_ms": duration_ms,
        },
        status_code=200 if is_healthy else 503,
    )


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics(
    authorization: str | None = Header(default=None),
) -> PlainTextResponse:
    """Prometheus metrics endpoint for scraping. Requires bearer token when configured."""
    if not settings.prometheus_enabled:
        raise HTTPException(status_code=404, detail="Metrics disabled")

    # When a prometheus_token is configured, require it as a bearer token
    if settings.prometheus_token:
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization required")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or token != settings.prometheus_token:
            raise HTTPException(status_code=403, detail="Invalid metrics token")

    # Update DB pool stats on each scrape
    pool_checked_in = engine.pool.checkedin()
    pool_checked_out = engine.pool.checkedout()
    pool_overflow = engine.pool.overflow()
    update_db_pool_stats(pool_checked_in, pool_checked_out, pool_overflow)

    # Update business metrics from database
    await _update_business_metrics()

    return PlainTextResponse(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


async def _update_business_metrics() -> None:
    """Query the database for business metrics and update Prometheus gauges.

    Runs on every /metrics scrape (~15s). Queries are lightweight COUNT(*)
    on indexed columns. Fails silently to avoid breaking metrics scraping.
    """
    _active_tenants_sql = text(
        "SELECT COUNT(*) FROM public.tenants WHERE status = 'active' AND deleted_at IS NULL"
    )
    _tenant_schemas_sql = text(
        "SELECT schema_name FROM public.tenants WHERE status = 'active' AND deleted_at IS NULL"
    )
    _appointments_today_sql = text(
        "SELECT COUNT(*) FROM appointments"
        " WHERE start_time::date = CURRENT_DATE"
        " AND is_active = true"
    )
    try:
        async with engine.connect() as conn:
            result = await conn.execute(_active_tenants_sql)
            active_tenants.set(result.scalar() or 0)

            schemas_result = await conn.execute(_tenant_schemas_sql)
            schemas = [row[0] for row in schemas_result]

            total_appointments = 0
            for schema in schemas:
                try:
                    await conn.execute(text(f"SET search_path TO {schema}, public"))
                    result = await conn.execute(_appointments_today_sql)
                    total_appointments += result.scalar() or 0
                except Exception:
                    logger.debug("Skipping schema %s for metrics", schema)
                finally:
                    await conn.execute(text("SET search_path TO public"))

            appointments_today.set(total_appointments)
    except Exception:
        logger.debug("Failed to update business metrics", exc_info=True)
