import logging
import time

import aio_pika
import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.redis import redis_client

logger = logging.getLogger("dentalos.health")

router = APIRouter(tags=["health"])


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

    duration_ms = round((time.time() - start) * 1000)
    is_healthy = checks["postgres"]["status"] == "healthy"

    return JSONResponse(
        content={
            "status": "healthy" if is_healthy else "degraded",
            "version": settings.app_version,
            "services": checks,
            "duration_ms": duration_ms,
        },
        status_code=200 if is_healthy else 503,
    )
