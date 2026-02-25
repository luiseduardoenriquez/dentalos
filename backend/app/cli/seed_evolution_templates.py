"""Seed built-in evolution templates for a tenant.

Populates evolution_templates, evolution_template_steps, and
evolution_template_variables in the tenant-schema that is already
set as the session search_path by the caller.

Built-in templates (is_builtin=True) are skipped if a template with the
same name already exists as a builtin, so this script is fully idempotent.

Usage (standalone for development):
    cd backend
    uv run python -m app.cli.seed_evolution_templates

Usage (from tenant provisioning service):
    from app.cli.seed_evolution_templates import seed_evolution_templates
    count = await seed_evolution_templates(db)
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.tenant.evolution_template import (
    EvolutionTemplate,
    EvolutionTemplateStep,
    EvolutionTemplateVariable,
)

logger = logging.getLogger("dentalos.cli.seed_evolution_templates")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class _VariableDef:
    name: str
    variable_type: str          # text | number | select | date
    is_required: bool = True
    options: dict | None = None  # Only for variable_type == 'select'


@dataclass
class _TemplateDef:
    name: str
    procedure_type: str
    cups_code: str
    complexity: str             # simple | moderate | complex
    steps: list[str] = field(default_factory=list)
    variables: list[_VariableDef] = field(default_factory=list)


def _select_opts(*choices: str) -> dict:
    """Build the JSONB options dict for a select variable."""
    return {"choices": list(choices)}


# ---------------------------------------------------------------------------
# Template definitions (10 built-in templates)
# ---------------------------------------------------------------------------

BUILTIN_TEMPLATES: list[_TemplateDef] = [
    # 1 — Resina Compuesta
    _TemplateDef(
        name="Resina Compuesta",
        procedure_type="restorative",
        cups_code="232201",
        complexity="simple",
        steps=[
            "Anestesia y aislamiento del campo operatorio",
            "Remoción de tejido cariado con cureta y fresa",
            "Grabado ácido de esmalte y dentina (15-30 segundos)",
            "Aplicación de adhesivo y fotocurado",
            "Aplicación de resina [color_resina] por capas incrementales en superficie [superficie]",
            "Fotocurado de cada capa (20 segundos)",
            "Ajuste oclusal con papel articular y pulido final",
        ],
        variables=[
            _VariableDef(
                name="superficie",
                variable_type="select",
                options=_select_opts("mesial", "distal", "oclusal", "vestibular", "lingual", "mesio-oclusal", "disto-oclusal"),
            ),
            _VariableDef(
                name="color_resina",
                variable_type="text",
            ),
            _VariableDef(
                name="tipo_anestesia",
                variable_type="select",
                options=_select_opts("infiltrativa", "troncular", "tópica", "sin anestesia"),
            ),
        ],
    ),

    # 2 — Endodoncia Unirradicular
    _TemplateDef(
        name="Endodoncia Unirradicular",
        procedure_type="endodontic",
        cups_code="241201",
        complexity="complex",
        steps=[
            "Radiografía periapical inicial para evaluación y conductometría",
            "Anestesia [tipo_anestesia] e instalación de dique de goma",
            "Apertura cameral con fresa de alta velocidad",
            "Instrumentación del conducto hasta lima [lima_apical] — longitud de trabajo: [longitud_trabajo] mm",
            "Irrigación con hipoclorito de sodio al 5,25% entre limas",
            "Secado del conducto con conos de papel absorbente",
            "Obturación con gutapercha y cemento sellador (técnica [tecnica_obturacion])",
            "Radiografía de control postobturación",
            "Restauración provisional con ionómero de vidrio",
        ],
        variables=[
            _VariableDef(
                name="longitud_trabajo",
                variable_type="number",
            ),
            _VariableDef(
                name="lima_apical",
                variable_type="text",
            ),
            _VariableDef(
                name="tipo_anestesia",
                variable_type="select",
                options=_select_opts("infiltrativa", "troncular"),
            ),
            _VariableDef(
                name="tecnica_obturacion",
                variable_type="select",
                options=_select_opts("condensación lateral", "condensación vertical", "híbrida"),
            ),
        ],
    ),

    # 3 — Exodoncia Simple
    _TemplateDef(
        name="Exodoncia Simple",
        procedure_type="surgical",
        cups_code="243100",
        complexity="simple",
        steps=[
            "Anestesia local [tipo_anestesia]",
            "Sindesmotomía — desprendimiento del ligamento periodontal",
            "Luxación del diente con elevador",
            "Extracción con fórceps [tipo_forceps]",
            "Revisión y curetaje del alveolo",
            "Hemostasia con compresión y gasa",
            "Indicaciones postoperatorias: no escupir, no enjuagarse 24h, dieta blanda, analgesia",
        ],
        variables=[
            _VariableDef(
                name="tipo_anestesia",
                variable_type="select",
                options=_select_opts("infiltrativa", "troncular"),
            ),
            _VariableDef(
                name="tipo_forceps",
                variable_type="text",
            ),
            _VariableDef(
                name="complicaciones",
                variable_type="text",
                is_required=False,
            ),
        ],
    ),

    # 4 — Profilaxis y Detartraje
    _TemplateDef(
        name="Profilaxis y Detartraje",
        procedure_type="preventive",
        cups_code="997120",
        complexity="simple",
        steps=[
            "Revelado de placa bacteriana — índice de placa: [indice_placa]%",
            "Detartraje supragingival con ultrasonido (punta estándar)",
            "Profilaxis con copa de caucho y pasta abrasiva",
            "Aplicación de flúor [tipo_fluor]",
            "Educación en técnica de cepillado y uso de hilo dental",
        ],
        variables=[
            _VariableDef(
                name="indice_placa",
                variable_type="number",
            ),
            _VariableDef(
                name="tipo_fluor",
                variable_type="select",
                options=_select_opts("gel", "barniz", "espuma"),
            ),
        ],
    ),

    # 5 — Corona Completa
    _TemplateDef(
        name="Corona Completa Metal-Porcelana",
        procedure_type="restorative",
        cups_code="234400",
        complexity="complex",
        steps=[
            "Selección de color con guía Vita: [color_porcelana]",
            "Preparación del diente — tallado con reducción oclusal de 1,5-2 mm y reducción axial de 1,5 mm",
            "Retracción gingival con hilo retractor",
            "Toma de impresión definitiva con silicona de adición (cubeta individual)",
            "Colocación de corona provisional acrílica y cementación con eugenol",
            "Envío al laboratorio — material: [material_corona]",
            "Prueba de estructura metálica — verificar ajuste marginal y oclusión",
            "Prueba de porcelana en biscocho — verificar estética y contactos",
            "Cementación definitiva con cemento [tipo_cemento] — ajuste oclusal final",
        ],
        variables=[
            _VariableDef(
                name="color_porcelana",
                variable_type="text",
            ),
            _VariableDef(
                name="material_corona",
                variable_type="select",
                options=_select_opts("metal-porcelana", "porcelana pura", "zirconio", "disilicato de litio"),
            ),
            _VariableDef(
                name="tipo_cemento",
                variable_type="select",
                options=_select_opts("ionómero de vidrio", "resinoso", "fosfato de zinc"),
            ),
        ],
    ),

    # 6 — Blanqueamiento Dental
    _TemplateDef(
        name="Blanqueamiento Dental en Consultorio",
        procedure_type="other",
        cups_code="247100",
        complexity="simple",
        steps=[
            "Profilaxis dental previa para remover placa y cálculo",
            "Fotografía inicial — color de referencia: [color_inicial] (escala Vita)",
            "Aislamiento de tejidos blandos con barrera gingival fotopolimerizable",
            "Aplicación de agente blanqueador (peróxido de hidrógeno [concentracion_peroxido]%)",
            "Activación con lámpara LED — [ciclos_aplicacion] ciclos de 15 minutos",
            "Retiro del agente, lavado y evaluación del resultado",
            "Color final alcanzado: [color_final] (escala Vita)",
            "Indicaciones postoperatorias: dieta blanca 48h, evitar colorantes",
        ],
        variables=[
            _VariableDef(
                name="concentracion_peroxido",
                variable_type="text",
            ),
            _VariableDef(
                name="ciclos_aplicacion",
                variable_type="number",
            ),
            _VariableDef(
                name="color_inicial",
                variable_type="text",
            ),
            _VariableDef(
                name="color_final",
                variable_type="text",
            ),
        ],
    ),

    # 7 — Consulta de Primera Vez
    _TemplateDef(
        name="Consulta de Primera Vez",
        procedure_type="diagnostic",
        cups_code="890201",
        complexity="simple",
        steps=[
            "Anamnesis completa — motivo de consulta: [motivo_consulta]",
            "Examen extraoral: ganglios, ATM, musculatura masticatoria",
            "Examen intraoral: tejidos blandos, encía, mucosa, lengua",
            "Evaluación del estado dental — odontograma diligenciado",
            "Evaluación radiográfica (radiografías según necesidad clínica)",
            "Diagnóstico y elaboración del plan de tratamiento",
            "Hallazgos principales: [hallazgos_principales]",
            "Educación al paciente sobre hallazgos y próximos pasos",
        ],
        variables=[
            _VariableDef(
                name="motivo_consulta",
                variable_type="text",
            ),
            _VariableDef(
                name="hallazgos_principales",
                variable_type="text",
            ),
        ],
    ),

    # 8 — Cirugía de Tercer Molar
    _TemplateDef(
        name="Cirugía de Tercer Molar Incluido",
        procedure_type="surgical",
        cups_code="243400",
        complexity="complex",
        steps=[
            "Evaluación radiográfica panorámica — clasificación Winter: [clasificacion_winter] / Pell y Gregory: [clasificacion_pell_gregory]",
            "Anestesia troncular del nervio dentario inferior y bucal largo",
            "Incisión y desprendimiento de colgajo mucoperióstico",
            "Osteotomía con fresa de carburo si es necesaria",
            "Odontosección con fresa si es necesaria",
            "Luxación y extracción del diente",
            "Limpieza y curetaje del alveolo — irrigación con solución salina",
            "Sutura con [tipo_sutura] — indicar número de puntos",
            "Indicaciones postoperatorias: hielo 20 min/hora x 6h, antibióticos, analgesia, control en 7 días",
        ],
        variables=[
            _VariableDef(
                name="clasificacion_winter",
                variable_type="select",
                options=_select_opts("vertical", "mesioangulado", "distoangulado", "horizontal", "invertido"),
            ),
            _VariableDef(
                name="clasificacion_pell_gregory",
                variable_type="text",
            ),
            _VariableDef(
                name="tipo_sutura",
                variable_type="select",
                options=_select_opts("seda 3-0", "ácido poliglicólico 3-0", "catgut crómico 3-0"),
            ),
        ],
    ),

    # 9 — Raspaje y Alisado Radicular
    _TemplateDef(
        name="Raspaje y Alisado Radicular",
        procedure_type="periodontic",
        cups_code="242100",
        complexity="moderate",
        steps=[
            "Evaluación periodontal — profundidad de sondaje máxima: [profundidad_sondaje_max] mm — sangrado al sondaje: [sangrado_al_sondaje]",
            "Anestesia local del cuadrante [cuadrante]",
            "Raspaje subgingival con curetas Gracey por cuadrante",
            "Alisado radicular hasta superficie lisa y dura",
            "Irrigación subgingival con clorhexidina al 0,12%",
            "Indicaciones: cepillado suave, clorhexidina 2 veces/día x 14 días, control en 3 semanas",
        ],
        variables=[
            _VariableDef(
                name="cuadrante",
                variable_type="select",
                options=_select_opts("1", "2", "3", "4"),
            ),
            _VariableDef(
                name="profundidad_sondaje_max",
                variable_type="number",
            ),
            _VariableDef(
                name="sangrado_al_sondaje",
                variable_type="select",
                options=_select_opts("sí", "no"),
            ),
        ],
    ),

    # 10 — Sellante de Fotocurado
    _TemplateDef(
        name="Sellante de Fotocurado",
        procedure_type="preventive",
        cups_code="997110",
        complexity="simple",
        steps=[
            "Limpieza de la superficie oclusal del diente [diente] con piedra pómez",
            "Aislamiento con rollos de algodón y eyector",
            "Grabado ácido de la superficie oclusal (30 segundos)",
            "Lavado abundante con agua y secado con jeringa de aire",
            "Aplicación del sellante [tipo_sellante] en surcos y fisuras",
            "Fotocurado por 20 segundos",
            "Verificación de oclusión con papel articular — ajuste si hay puntos prematuros",
        ],
        variables=[
            _VariableDef(
                name="diente",
                variable_type="text",
            ),
            _VariableDef(
                name="tipo_sellante",
                variable_type="select",
                options=_select_opts("resinoso", "ionómero de vidrio"),
            ),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------

async def seed_evolution_templates(db: AsyncSession) -> int:
    """Seed built-in evolution templates into the current tenant schema.

    Skips any template whose (name, is_builtin=True) already exists,
    making this function fully idempotent.

    The caller is responsible for setting search_path to the correct
    tenant schema before invoking this function.

    Args:
        db: An open AsyncSession with search_path set to the tenant schema.

    Returns:
        Number of templates inserted (0 if all already existed).
    """
    inserted = 0

    for tdef in BUILTIN_TEMPLATES:
        # Idempotency check — skip if builtin with same name already exists.
        existing = await db.execute(
            select(EvolutionTemplate.id).where(
                EvolutionTemplate.name == tdef.name,
                EvolutionTemplate.is_builtin.is_(True),
            )
        )
        if existing.scalar_one_or_none() is not None:
            logger.debug("Skipping existing builtin template: %r", tdef.name)
            continue

        # Create the template header.
        template = EvolutionTemplate(
            name=tdef.name,
            procedure_type=tdef.procedure_type,
            cups_code=tdef.cups_code,
            complexity=tdef.complexity,
            is_builtin=True,
            is_active=True,
        )
        db.add(template)
        # Flush to get the generated UUID for step/variable FK.
        await db.flush()

        # Create ordered steps.
        for order, content in enumerate(tdef.steps, start=1):
            db.add(
                EvolutionTemplateStep(
                    template_id=template.id,
                    step_order=order,
                    content=content,
                )
            )

        # Create variable definitions.
        for vdef in tdef.variables:
            db.add(
                EvolutionTemplateVariable(
                    template_id=template.id,
                    name=vdef.name,
                    variable_type=vdef.variable_type,
                    is_required=vdef.is_required,
                    options=vdef.options,
                )
            )

        inserted += 1
        logger.info("Inserted builtin template: %r (%s)", tdef.name, tdef.cups_code)

    await db.commit()
    logger.info(
        "Evolution templates: inserted %d / %d builtin templates",
        inserted,
        len(BUILTIN_TEMPLATES),
    )
    return inserted


# ---------------------------------------------------------------------------
# Standalone CLI entry point
# ---------------------------------------------------------------------------

async def _main() -> None:
    """Bootstrap a session pointed at the public default schema for development."""
    from app.core.config import settings

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    print("DentalOS — Evolution Template Seeder")
    print("=" * 45)
    print()

    # For standalone dev use, prompt for the tenant schema to seed into.
    schema = input("Tenant schema name (e.g. tn_abc123, leave blank for 'public'): ").strip()
    if not schema:
        schema = "public"

    from sqlalchemy import text

    async with session_factory() as session:
        await session.execute(text(f"SET search_path TO {schema}, public"))
        count = await seed_evolution_templates(session)

    await engine.dispose()

    print()
    print(f"Templates inserted : {count} / {len(BUILTIN_TEMPLATES)}")
    print("Done. Run again at any time — inserts are idempotent.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        stream=sys.stdout,
    )
    asyncio.run(_main())
