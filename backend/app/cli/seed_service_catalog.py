"""Seed service catalog with default dental procedures and prices.

Populates the service_catalog table in the tenant schema that is already
set as the session search_path by the caller.

All prices are in Colombian Peso **cents** (integer) as required by the
DentalOS convention.  Example: $100,000 COP = 10,000,000 cents.

Inserts are skipped when a row with the same cups_code already exists,
making this script fully idempotent.

Usage (standalone for development):
    cd backend
    uv run python -m app.cli.seed_service_catalog

Usage (from tenant provisioning service):
    from app.cli.seed_service_catalog import seed_service_catalog
    count = await seed_service_catalog(db)
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.tenant.service_catalog import ServiceCatalog

logger = logging.getLogger("dentalos.cli.seed_service_catalog")


# ---------------------------------------------------------------------------
# Service data
# Tuple format: (cups_code, name, default_price_cents, category)
# Prices are in COP cents. Multiply COP value × 100.
# Example: $80,000 COP = 8_000_000 cents
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _ServiceDef:
    cups_code: str
    name: str
    default_price_cents: int
    category: str


SERVICES: list[_ServiceDef] = [
    # ── Diagnóstico ────────────────────────────────────────────────────────
    _ServiceDef("890201", "Consulta de primera vez por odontología general",          8_000_000,  "diagnostic"),
    _ServiceDef("890202", "Consulta de control o seguimiento por odontología general", 5_000_000,  "diagnostic"),
    _ServiceDef("890301", "Consulta de primera vez por odontología especializada",    10_000_000,  "diagnostic"),
    _ServiceDef("890302", "Consulta de control por odontología especializada",         6_000_000,  "diagnostic"),
    _ServiceDef("871010", "Radiografía periapical",                                    2_500_000,  "diagnostic"),
    _ServiceDef("871020", "Radiografía oclusal",                                       3_000_000,  "diagnostic"),
    _ServiceDef("871030", "Radiografía panorámica",                                    8_000_000,  "diagnostic"),
    _ServiceDef("871040", "Radiografía lateral de cráneo",                             8_000_000,  "diagnostic"),

    # ── Preventivo ─────────────────────────────────────────────────────────
    _ServiceDef("997100", "Aplicación de flúor",                                       3_000_000,  "preventive"),
    _ServiceDef("997110", "Sellante de fotocurado por diente",                         4_000_000,  "preventive"),
    _ServiceDef("997120", "Profilaxis dental",                                          5_000_000,  "preventive"),
    _ServiceDef("997130", "Detartraje supragingival",                                   6_000_000,  "preventive"),
    _ServiceDef("997140", "Detartraje subgingival por cuadrante",                       8_000_000,  "preventive"),
    _ServiceDef("997150", "Control de placa dental",                                    2_500_000,  "preventive"),
    _ServiceDef("997160", "Educación en salud oral individual",                         2_500_000,  "preventive"),

    # ── Restaurador — Amalgama ─────────────────────────────────────────────
    _ServiceDef("232101", "Obturación con amalgama de una superficie",                  7_000_000,  "restorative"),
    _ServiceDef("232102", "Obturación con amalgama de dos superficies",                10_000_000,  "restorative"),
    _ServiceDef("232103", "Obturación con amalgama de tres o más superficies",         13_000_000,  "restorative"),

    # ── Restaurador — Resina ───────────────────────────────────────────────
    _ServiceDef("232201", "Resina compuesta de una superficie",                        10_000_000,  "restorative"),
    _ServiceDef("232202", "Resina compuesta de dos superficies",                       13_000_000,  "restorative"),
    _ServiceDef("232203", "Resina compuesta de tres o más superficies",                16_000_000,  "restorative"),

    # ── Restaurador — Ionómero ─────────────────────────────────────────────
    _ServiceDef("232301", "Obturación con ionómero de vidrio",                          8_000_000,  "restorative"),

    # ── Restaurador — Protección pulpar ───────────────────────────────────
    _ServiceDef("232401", "Recubrimiento pulpar directo",                               8_000_000,  "restorative"),
    _ServiceDef("232402", "Recubrimiento pulpar indirecto",                             6_000_000,  "restorative"),

    # ── Restaurador — Coronas e incrustaciones ────────────────────────────
    _ServiceDef("234100", "Corona temporal acrílica",                                  12_000_000,  "restorative"),
    _ServiceDef("234200", "Corona completa en metal",                                  45_000_000,  "restorative"),
    _ServiceDef("234300", "Corona completa en porcelana pura",                         80_000_000,  "restorative"),
    _ServiceDef("234400", "Corona completa metal-porcelana",                           60_000_000,  "restorative"),
    _ServiceDef("234500", "Incrustación (inlay/onlay)",                                40_000_000,  "restorative"),
    _ServiceDef("234600", "Carilla dental en porcelana",                               90_000_000,  "restorative"),
    _ServiceDef("234700", "Carilla dental en resina",                                  25_000_000,  "restorative"),
    _ServiceDef("234800", "Perno muñón colado",                                        25_000_000,  "restorative"),
    _ServiceDef("234900", "Perno prefabricado",                                        15_000_000,  "restorative"),

    # ── Endodóntico ────────────────────────────────────────────────────────
    _ServiceDef("241101", "Pulpotomía",                                                15_000_000,  "endodontic"),
    _ServiceDef("241102", "Pulpectomía",                                               18_000_000,  "endodontic"),
    _ServiceDef("241201", "Endodoncia unirradicular (1 conducto)",                     35_000_000,  "endodontic"),
    _ServiceDef("241202", "Endodoncia birradicular (2 conductos)",                     45_000_000,  "endodontic"),
    _ServiceDef("241203", "Endodoncia multirradicular (3 o más conductos)",            55_000_000,  "endodontic"),
    _ServiceDef("241300", "Retratamiento endodóntico",                                 50_000_000,  "endodontic"),
    _ServiceDef("241400", "Apicectomía",                                               40_000_000,  "endodontic"),

    # ── Periodontal ────────────────────────────────────────────────────────
    _ServiceDef("242100", "Raspaje y alisado radicular por cuadrante",                 15_000_000,  "periodontic"),
    _ServiceDef("242200", "Cirugía periodontal a colgajo por sextante",                60_000_000,  "periodontic"),
    _ServiceDef("242300", "Gingivectomía",                                             35_000_000,  "periodontic"),
    _ServiceDef("242500", "Alargamiento de corona clínica",                            50_000_000,  "periodontic"),
    _ServiceDef("242600", "Injerto gingival libre",                                    80_000_000,  "periodontic"),
    _ServiceDef("242700", "Regeneración tisular guiada",                              100_000_000,  "periodontic"),

    # ── Quirúrgico ─────────────────────────────────────────────────────────
    _ServiceDef("243100", "Exodoncia de diente erupcionado",                           12_000_000,  "surgical"),
    _ServiceDef("243200", "Exodoncia de diente incluido",                              25_000_000,  "surgical"),
    _ServiceDef("243300", "Exodoncia de diente retenido",                              30_000_000,  "surgical"),
    _ServiceDef("243400", "Exodoncia de tercer molar incluido",                        40_000_000,  "surgical"),
    _ServiceDef("243500", "Exodoncia de tercer molar retenido",                        35_000_000,  "surgical"),
    _ServiceDef("243700", "Alveoloplastia",                                            20_000_000,  "surgical"),
    _ServiceDef("243800", "Frenillectomía labial",                                     25_000_000,  "surgical"),
    _ServiceDef("243900", "Frenillectomía lingual",                                    25_000_000,  "surgical"),
    _ServiceDef("244000", "Biopsia de tejido blando de cavidad oral",                  30_000_000,  "surgical"),
    _ServiceDef("244200", "Drenaje de absceso dentoalveolar",                          15_000_000,  "surgical"),

    # ── Ortodóntico ────────────────────────────────────────────────────────
    _ServiceDef("245100", "Colocación de aparatología ortodóntica fija",              350_000_000,  "orthodontic"),
    _ServiceDef("245200", "Control de ortodoncia mensual",                             25_000_000,  "orthodontic"),
    _ServiceDef("245300", "Retiro de aparatología ortodóntica fija",                   30_000_000,  "orthodontic"),
    _ServiceDef("245400", "Colocación de retenedor fijo",                              40_000_000,  "orthodontic"),

    # ── Prostodóntico ──────────────────────────────────────────────────────
    _ServiceDef("246100", "Prótesis parcial removible (por arco)",                    120_000_000,  "prosthodontic"),
    _ServiceDef("246200", "Prótesis total superior",                                  100_000_000,  "prosthodontic"),
    _ServiceDef("246300", "Prótesis total inferior",                                  100_000_000,  "prosthodontic"),
    _ServiceDef("246400", "Reparación de prótesis removible",                          20_000_000,  "prosthodontic"),
    _ServiceDef("246500", "Rebase de prótesis removible",                              35_000_000,  "prosthodontic"),
    _ServiceDef("246600", "Prótesis parcial fija (puente) por unidad",                60_000_000,  "prosthodontic"),
    _ServiceDef("246700", "Implante dental osteointegrado",                           250_000_000,  "prosthodontic"),
    _ServiceDef("246800", "Corona sobre implante",                                     80_000_000,  "prosthodontic"),

    # ── Otros ──────────────────────────────────────────────────────────────
    _ServiceDef("247100", "Blanqueamiento dental en consultorio",                      35_000_000,  "other"),
    _ServiceDef("247200", "Blanqueamiento dental ambulatorio (kit)",                   20_000_000,  "other"),
    _ServiceDef("247300", "Ajuste oclusal",                                            10_000_000,  "other"),
    _ServiceDef("247400", "Placa oclusal (guarda nocturna)",                           45_000_000,  "other"),
    _ServiceDef("247500", "Toma de impresiones para estudio",                           8_000_000,  "other"),
    _ServiceDef("247600", "Urgencia odontológica",                                     12_000_000,  "other"),
]


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------

async def seed_service_catalog(db: AsyncSession) -> int:
    """Seed the default service catalog into the current tenant schema.

    Skips any service whose cups_code already exists in service_catalog,
    making this function fully idempotent.

    The caller is responsible for setting search_path to the correct
    tenant schema before invoking this function.

    Args:
        db: An open AsyncSession with search_path set to the tenant schema.

    Returns:
        Number of services inserted (0 if all already existed).
    """
    inserted = 0

    for sdef in SERVICES:
        # Idempotency check — skip if cups_code already in catalog.
        existing = await db.execute(
            select(ServiceCatalog.id).where(
                ServiceCatalog.cups_code == sdef.cups_code
            )
        )
        if existing.scalar_one_or_none() is not None:
            logger.debug("Skipping existing service: %s — %s", sdef.cups_code, sdef.name)
            continue

        db.add(
            ServiceCatalog(
                cups_code=sdef.cups_code,
                name=sdef.name,
                default_price=sdef.default_price_cents,
                category=sdef.category,
                is_active=True,
            )
        )
        inserted += 1
        logger.info(
            "Inserted service: %s — %s (%s)",
            sdef.cups_code,
            sdef.name,
            sdef.category,
        )

    await db.commit()
    logger.info(
        "Service catalog: inserted %d / %d services",
        inserted,
        len(SERVICES),
    )
    return inserted


# ---------------------------------------------------------------------------
# Standalone CLI entry point
# ---------------------------------------------------------------------------

async def _main() -> None:
    """Bootstrap a session and seed the service catalog for development."""
    from app.core.config import settings
    from sqlalchemy import text

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    print("DentalOS — Service Catalog Seeder")
    print("=" * 40)
    print()

    schema = input("Tenant schema name (e.g. tn_abc123, leave blank for 'public'): ").strip()
    if not schema:
        schema = "public"

    async with session_factory() as session:
        await session.execute(text(f"SET search_path TO {schema}, public"))
        count = await seed_service_catalog(session)

    await engine.dispose()

    total_value = sum(s.default_price_cents for s in SERVICES)
    print()
    print(f"Services inserted    : {count} / {len(SERVICES)}")
    print(f"Price range (COP)    : ${min(s.default_price_cents for s in SERVICES) // 100:,} – ${max(s.default_price_cents for s in SERVICES) // 100:,}")
    print(f"Total catalog value  : ${total_value // 100:,} COP (sum of default prices)")
    print()
    print("Done. Run again at any time — inserts are idempotent.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        stream=sys.stdout,
    )
    asyncio.run(_main())
