"""Run tenant migrations across all active tenant schemas.

Usage:
    python -m app.cli.migrate_all_tenants
"""
import asyncio
import logging
import os
import subprocess
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

logger = logging.getLogger("dentalos.cli.migrate")

CONCURRENCY = 5
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def get_tenant_schemas() -> list[str]:
    """Query public.tenants for all active/suspended schema names."""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "SELECT schema_name FROM public.tenants "
                "WHERE status IN ('active', 'suspended') "
                "ORDER BY created_at"
            )
        )
        schemas = [row[0] for row in result]
    await engine.dispose()
    return schemas


def run_migration_sync(schema: str) -> tuple[str, bool, str]:
    """Run Alembic upgrade for a single tenant schema."""
    result = subprocess.run(  # noqa: S603
        [
            sys.executable, "-m", "alembic",
            "-c", "alembic_tenant/alembic.ini",
            "upgrade", "head",
            "-x", f"schema={schema}",
        ],
        capture_output=True,
        text=True,
        cwd=BACKEND_DIR,
    )
    success = result.returncode == 0
    output = result.stdout if success else result.stderr
    return schema, success, output


async def migrate_schema(semaphore: asyncio.Semaphore, schema: str) -> tuple[str, bool, str]:
    """Run migration with bounded concurrency."""
    async with semaphore:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, run_migration_sync, schema)


async def main() -> None:
    """Migrate all tenant schemas."""
    schemas = await get_tenant_schemas()

    if not schemas:
        logger.info("No active tenants found. Nothing to migrate.")
        return

    logger.info("Migrating %d tenant schemas (concurrency=%d)...", len(schemas), CONCURRENCY)

    semaphore = asyncio.Semaphore(CONCURRENCY)
    tasks = [migrate_schema(semaphore, schema) for schema in schemas]
    results = await asyncio.gather(*tasks)

    success_count = 0
    fail_count = 0
    for schema, success, output in results:
        if success:
            success_count += 1
            logger.info("OK: %s", schema)
        else:
            fail_count += 1
            logger.error("FAIL: %s — %s", schema, output.strip())

    logger.info(
        "Migration complete: %d succeeded, %d failed out of %d total",
        success_count, fail_count, len(schemas),
    )

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    asyncio.run(main())
