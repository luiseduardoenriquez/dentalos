import logging
import platform
import time

import aio_pika
import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import generate_latest
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.metrics import REGISTRY, update_db_pool_stats
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

    # MinIO/S3 check (non-critical)
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        s3.head_bucket(Bucket=settings.s3_bucket_name)
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
async def prometheus_metrics() -> PlainTextResponse:
    """Prometheus metrics endpoint for scraping. No auth required (internal)."""
    # Update DB pool stats on each scrape
    pool_checked_in = engine.pool.checkedin()
    pool_checked_out = engine.pool.checkedout()
    pool_overflow = engine.pool.overflow()
    update_db_pool_stats(pool_checked_in, pool_checked_out, pool_overflow)

    return PlainTextResponse(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
