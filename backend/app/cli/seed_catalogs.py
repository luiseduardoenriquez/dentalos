"""Seed CIE-10 and CUPS dental catalogs into the public schema.

Both tables live in public schema and are shared across all tenants.
All inserts use ON CONFLICT (code) DO NOTHING so this script is fully
idempotent -- safe to run multiple times.

Usage:
    cd backend
    uv run python -m app.cli.seed_catalogs
"""

import asyncio
import logging
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

logger = logging.getLogger("dentalos.cli.seed_catalogs")

# ---------------------------------------------------------------------------
# CIE-10 dental subset  (K00-K14, ~70 codes)
# Tuple format: (code, description, category)
# ---------------------------------------------------------------------------
CIE10_DENTAL_CODES: list[tuple[str, str, str]] = [
    # K00 — Trastornos del desarrollo y de la erupción de los dientes
    ("K00.0", "Anodoncia", "K00"),
    ("K00.1", "Dientes supernumerarios", "K00"),
    ("K00.2", "Anomalías del tamaño y de la forma del diente", "K00"),
    ("K00.3", "Dientes moteados", "K00"),
    ("K00.4", "Alteraciones en la formación dentaria", "K00"),
    ("K00.5", "Anomalías hereditarias de la estructura dentaria, no clasificadas en otra parte", "K00"),
    ("K00.6", "Alteraciones en la erupción dentaria", "K00"),
    ("K00.7", "Síndrome de la erupción dentaria", "K00"),
    ("K00.8", "Otros trastornos del desarrollo de los dientes", "K00"),
    ("K00.9", "Trastorno del desarrollo de los dientes, no especificado", "K00"),
    # K01 — Dientes incluidos e impactados
    ("K01.0", "Dientes incluidos", "K01"),
    ("K01.1", "Dientes impactados", "K01"),
    # K02 — Caries dental
    ("K02.0", "Caries limitada al esmalte", "K02"),
    ("K02.1", "Caries de la dentina", "K02"),
    ("K02.2", "Caries del cemento", "K02"),
    ("K02.3", "Caries dentaria detenida", "K02"),
    ("K02.4", "Odontoclasia", "K02"),
    ("K02.5", "Caries con exposición pulpar", "K02"),
    ("K02.8", "Otras caries dentales", "K02"),
    ("K02.9", "Caries dental, no especificada", "K02"),
    # K03 — Otras enfermedades de los tejidos duros de los dientes
    ("K03.0", "Atrición excesiva de los dientes", "K03"),
    ("K03.1", "Abrasión de los dientes", "K03"),
    ("K03.2", "Erosión de los dientes", "K03"),
    ("K03.3", "Reabsorción patológica de los dientes", "K03"),
    ("K03.4", "Hipercementosis", "K03"),
    ("K03.5", "Anquilosis dental", "K03"),
    ("K03.6", "Depósitos (acreciones) en los dientes", "K03"),
    ("K03.7", "Cambios posteruptivos del color de los tejidos dentales duros", "K03"),
    ("K03.8", "Otras enfermedades especificadas de los tejidos duros de los dientes", "K03"),
    ("K03.9", "Enfermedad de los tejidos duros de los dientes, no especificada", "K03"),
    # K04 — Enfermedades de la pulpa y de los tejidos periapicales
    ("K04.0", "Pulpitis", "K04"),
    ("K04.1", "Necrosis de la pulpa", "K04"),
    ("K04.2", "Degeneración de la pulpa", "K04"),
    ("K04.3", "Formación anormal de tejido duro en la pulpa", "K04"),
    ("K04.4", "Periodontitis apical aguda originada en la pulpa", "K04"),
    ("K04.5", "Periodontitis apical crónica", "K04"),
    ("K04.6", "Absceso periapical con fístula", "K04"),
    ("K04.7", "Absceso periapical sin fístula", "K04"),
    ("K04.8", "Quiste radicular", "K04"),
    ("K04.9", "Otras enfermedades y las no especificadas de la pulpa y del tejido periapical", "K04"),
    # K05 — Gingivitis y enfermedades periodontales
    ("K05.0", "Gingivitis aguda", "K05"),
    ("K05.1", "Gingivitis crónica", "K05"),
    ("K05.2", "Periodontitis aguda", "K05"),
    ("K05.3", "Periodontitis crónica", "K05"),
    ("K05.4", "Periodontosis", "K05"),
    ("K05.5", "Otras enfermedades periodontales", "K05"),
    ("K05.6", "Enfermedad periodontal, no especificada", "K05"),
    # K06 — Otros trastornos de la encía y de la zona edéntula
    ("K06.0", "Retracción gingival", "K06"),
    ("K06.1", "Hiperplasia gingival", "K06"),
    ("K06.2", "Lesiones de la encía y de la zona edéntula asociadas con traumatismo", "K06"),
    ("K06.8", "Otros trastornos especificados de la encía y de la zona edéntula", "K06"),
    ("K06.9", "Trastorno de la encía y de la zona edéntula, no especificado", "K06"),
    # K07 — Anomalías dentofaciales
    ("K07.0", "Anomalías evidentes del tamaño de los maxilares", "K07"),
    ("K07.1", "Anomalías de la relación maxilobasilar", "K07"),
    ("K07.2", "Anomalías de la relación entre los arcos dentarios", "K07"),
    ("K07.3", "Anomalías de la posición del diente", "K07"),
    ("K07.4", "Maloclusión de tipo no especificado", "K07"),
    ("K07.5", "Anomalías dentofaciales funcionales", "K07"),
    ("K07.6", "Trastornos de la articulación temporomandibular", "K07"),
    # K08 — Otros trastornos de los dientes y de sus estructuras de sostén
    ("K08.0", "Exfoliación de los dientes debida a causas sistémicas", "K08"),
    ("K08.1", "Pérdida de dientes debida a accidente, extracción o enfermedad periodontal local", "K08"),
    ("K08.2", "Atrofia del reborde alveolar desdentado", "K08"),
    ("K08.3", "Raíz dental retenida", "K08"),
    ("K08.8", "Otros trastornos especificados de los dientes y de sus estructuras de sostén", "K08"),
    ("K08.9", "Trastorno de los dientes y de sus estructuras de sostén, no especificado", "K08"),
    # K09-K14 — Condiciones adicionales de la cavidad oral
    ("K09.0", "Quistes originados por el desarrollo de los dientes", "K09"),
    ("K09.1", "Quistes de las fisuras (no odontogénicos)", "K09"),
    ("K09.2", "Otros quistes de los maxilares", "K09"),
    ("K10.0", "Trastornos del desarrollo de los maxilares", "K10"),
    ("K10.2", "Afecciones inflamatorias de los maxilares", "K10"),
    ("K10.3", "Alveolitis del maxilar", "K10"),
    ("K11.0", "Atrofia de glándula salival", "K11"),
    ("K11.2", "Sialoadenitis", "K11"),
    ("K12.0", "Estomatitis aftosa recurrente", "K12"),
    ("K12.1", "Otras formas de estomatitis", "K12"),
    ("K13.0", "Enfermedades de los labios", "K13"),
    ("K13.7", "Otras lesiones y las no especificadas de la mucosa bucal", "K13"),
    ("K14.0", "Glositis", "K14"),
    ("K14.6", "Glosodinia", "K14"),
]

# ---------------------------------------------------------------------------
# CUPS dental subset (~80 codes)
# Tuple format: (code, description, category)
# ---------------------------------------------------------------------------
CUPS_DENTAL_CODES: list[tuple[str, str, str]] = [
    # Diagnóstico
    ("890201", "Consulta de primera vez por odontología general", "diagnostic"),
    ("890202", "Consulta de control o seguimiento por odontología general", "diagnostic"),
    ("890301", "Consulta de primera vez por odontología especializada", "diagnostic"),
    ("890302", "Consulta de control o seguimiento por odontología especializada", "diagnostic"),
    ("871010", "Radiografía periapical", "diagnostic"),
    ("871020", "Radiografía oclusal", "diagnostic"),
    ("871030", "Radiografía panorámica", "diagnostic"),
    ("871040", "Radiografía lateral de cráneo", "diagnostic"),
    # Preventivo
    ("997100", "Aplicación de flúor", "preventive"),
    ("997110", "Aplicación de sellantes de fotocurado", "preventive"),
    ("997120", "Profilaxis dental", "preventive"),
    ("997130", "Detartraje supragingival", "preventive"),
    ("997140", "Detartraje subgingival", "preventive"),
    ("997150", "Control de placa dental", "preventive"),
    ("997160", "Educación en salud oral individual", "preventive"),
    # Restaurador — Amalgama
    ("232101", "Obturación dental con amalgama de una superficie", "restorative"),
    ("232102", "Obturación dental con amalgama de dos superficies", "restorative"),
    ("232103", "Obturación dental con amalgama de tres o más superficies", "restorative"),
    # Restaurador — Resina
    ("232201", "Obturación dental con resina de una superficie", "restorative"),
    ("232202", "Obturación dental con resina de dos superficies", "restorative"),
    ("232203", "Obturación dental con resina de tres o más superficies", "restorative"),
    # Restaurador — Ionómero
    ("232301", "Obturación dental con ionómero de vidrio", "restorative"),
    # Restaurador — Otros
    ("232401", "Recubrimiento pulpar directo", "restorative"),
    ("232402", "Recubrimiento pulpar indirecto", "restorative"),
    ("234100", "Corona temporal acrílica", "restorative"),
    ("234200", "Corona completa en metal", "restorative"),
    ("234300", "Corona completa en porcelana", "restorative"),
    ("234400", "Corona completa metal-porcelana", "restorative"),
    ("234500", "Incrustación (inlay/onlay)", "restorative"),
    ("234600", "Carilla dental en porcelana", "restorative"),
    ("234700", "Carilla dental en resina", "restorative"),
    ("234800", "Perno muñón colado", "restorative"),
    ("234900", "Perno prefabricado", "restorative"),
    # Endodóntico
    ("241101", "Pulpotomía", "endodontic"),
    ("241102", "Pulpectomía", "endodontic"),
    ("241201", "Endodoncia unirradicular (conducto único)", "endodontic"),
    ("241202", "Endodoncia birradicular (dos conductos)", "endodontic"),
    ("241203", "Endodoncia multirradicular (tres o más conductos)", "endodontic"),
    ("241300", "Retratamiento endodóntico", "endodontic"),
    ("241400", "Apicectomía", "endodontic"),
    # Periodontal
    ("242100", "Raspaje y alisado radicular por cuadrante", "periodontic"),
    ("242200", "Cirugía periodontal a colgajo por sextante", "periodontic"),
    ("242300", "Gingivectomía", "periodontic"),
    ("242400", "Gingivoplastia", "periodontic"),
    ("242500", "Alargamiento de corona clínica", "periodontic"),
    ("242600", "Injerto gingival libre", "periodontic"),
    ("242700", "Regeneración tisular guiada", "periodontic"),
    ("242800", "Ferulización dental", "periodontic"),
    # Quirúrgico
    ("243100", "Exodoncia de diente erupcionado", "surgical"),
    ("243200", "Exodoncia de diente incluido", "surgical"),
    ("243300", "Exodoncia de diente retenido", "surgical"),
    ("243400", "Exodoncia de tercer molar incluido", "surgical"),
    ("243500", "Exodoncia de tercer molar retenido", "surgical"),
    ("243600", "Cirugía de dientes supernumerarios", "surgical"),
    ("243700", "Alveoloplastia", "surgical"),
    ("243800", "Frenillectomía labial", "surgical"),
    ("243900", "Frenillectomía lingual", "surgical"),
    ("244000", "Biopsia de tejido blando de cavidad oral", "surgical"),
    ("244100", "Marsupialización de quiste", "surgical"),
    ("244200", "Drenaje de absceso dentoalveolar", "surgical"),
    # Ortodóntico
    ("245100", "Colocación de aparatología ortodóntica fija", "orthodontic"),
    ("245200", "Control de ortodoncia", "orthodontic"),
    ("245300", "Retiro de aparatología ortodóntica fija", "orthodontic"),
    ("245400", "Colocación de retenedor fijo", "orthodontic"),
    ("245500", "Colocación de aparato removible", "orthodontic"),
    # Prostodóntico
    ("246100", "Prótesis parcial removible", "prosthodontic"),
    ("246200", "Prótesis total superior", "prosthodontic"),
    ("246300", "Prótesis total inferior", "prosthodontic"),
    ("246400", "Reparación de prótesis removible", "prosthodontic"),
    ("246500", "Rebase de prótesis removible", "prosthodontic"),
    ("246600", "Prótesis parcial fija (puente) por unidad", "prosthodontic"),
    ("246700", "Implante dental osteointegrado", "prosthodontic"),
    ("246800", "Corona sobre implante", "prosthodontic"),
    # Otros
    ("247100", "Blanqueamiento dental en consultorio", "other"),
    ("247200", "Blanqueamiento dental ambulatorio (kit)", "other"),
    ("247300", "Ajuste oclusal", "other"),
    ("247400", "Placa oclusal (guarda)", "other"),
    ("247500", "Toma de impresiones para estudio", "other"),
    ("247600", "Urgencia odontológica", "other"),
]


async def seed_cie10(db: AsyncSession) -> int:
    """Seed CIE-10 dental codes into public.cie10_catalog.

    Uses ON CONFLICT (code) DO NOTHING so it is fully idempotent.

    Returns:
        Number of rows inserted (0 if all codes already existed).
    """
    if not CIE10_DENTAL_CODES:
        return 0

    values_sql = ", ".join(
        f"(:code_{i}, :description_{i}, :category_{i})"
        for i in range(len(CIE10_DENTAL_CODES))
    )
    params: dict[str, str] = {}
    for i, (code, description, category) in enumerate(CIE10_DENTAL_CODES):
        params[f"code_{i}"] = code
        params[f"description_{i}"] = description
        params[f"category_{i}"] = category

    sql = text(
        f"""
        INSERT INTO public.cie10_catalog (code, description, category)
        VALUES {values_sql}
        ON CONFLICT (code) DO NOTHING
        """
    )
    result = await db.execute(sql, params)
    await db.commit()
    inserted = result.rowcount
    logger.info("CIE-10: inserted %d / %d codes", inserted, len(CIE10_DENTAL_CODES))
    return inserted


async def seed_cups(db: AsyncSession) -> int:
    """Seed CUPS dental procedure codes into public.cups_catalog.

    Uses ON CONFLICT (code) DO NOTHING so it is fully idempotent.

    Returns:
        Number of rows inserted (0 if all codes already existed).
    """
    if not CUPS_DENTAL_CODES:
        return 0

    values_sql = ", ".join(
        f"(:code_{i}, :description_{i}, :category_{i})"
        for i in range(len(CUPS_DENTAL_CODES))
    )
    params: dict[str, str] = {}
    for i, (code, description, category) in enumerate(CUPS_DENTAL_CODES):
        params[f"code_{i}"] = code
        params[f"description_{i}"] = description
        params[f"category_{i}"] = category

    sql = text(
        f"""
        INSERT INTO public.cups_catalog (code, description, category)
        VALUES {values_sql}
        ON CONFLICT (code) DO NOTHING
        """
    )
    result = await db.execute(sql, params)
    await db.commit()
    inserted = result.rowcount
    logger.info("CUPS: inserted %d / %d codes", inserted, len(CUPS_DENTAL_CODES))
    return inserted


async def seed_all_catalogs(db: AsyncSession) -> dict[str, int]:
    """Seed both CIE-10 and CUPS catalogs.

    Intended entry point for both standalone CLI use and programmatic
    invocation during tenant provisioning.

    Args:
        db: An open AsyncSession pointed at the public schema.

    Returns:
        Dict with keys 'cie10' and 'cups' containing insert counts.
    """
    cie10_count = await seed_cie10(db)
    cups_count = await seed_cups(db)
    return {"cie10": cie10_count, "cups": cups_count}


# ---------------------------------------------------------------------------
# Standalone CLI entry point
# ---------------------------------------------------------------------------

async def _main() -> None:
    """Bootstrap a session and run all catalog seeds."""
    from app.core.config import settings

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    print("DentalOS — Catalog Seeder")
    print("=" * 40)

    async with session_factory() as session:
        counts = await seed_all_catalogs(session)

    await engine.dispose()

    print(f"CIE-10 codes inserted : {counts['cie10']} / {len(CIE10_DENTAL_CODES)}")
    print(f"CUPS codes inserted   : {counts['cups']} / {len(CUPS_DENTAL_CODES)}")
    print()
    print("Done. Run again at any time — inserts are idempotent.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        stream=sys.stdout,
    )
    asyncio.run(_main())
