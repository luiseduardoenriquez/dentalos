"""Seed built-in consent templates into the public schema.

Populates public.consent_templates with 7 system-provided templates that
cover the most common consent categories used by dental clinics.

Built-in templates (builtin=True) are skipped if a template with the same
name already exists as a builtin, so this script is fully idempotent.

Usage (standalone for development):
    cd backend
    uv run python -m app.cli.seed_consent_templates

Usage (from tenant provisioning or admin tooling):
    from app.cli.seed_consent_templates import seed_consent_templates
    count = await seed_consent_templates(db)
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.public.consent_template import PublicConsentTemplate

logger = logging.getLogger("dentalos.cli.seed_consent_templates")

# ---------------------------------------------------------------------------
# Shared signature positions used across all templates
# ---------------------------------------------------------------------------

_DEFAULT_SIGNATURE_POSITIONS = [
    {"role": "patient", "label": "Paciente", "required": True},
    {"role": "doctor", "label": "Doctor", "required": True},
]


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------


@dataclass
class _ConsentTemplateDef:
    name: str
    category: str
    description: str
    content: str
    signature_positions: list[dict] = field(
        default_factory=lambda: list(_DEFAULT_SIGNATURE_POSITIONS)
    )
    version: int = 1
    builtin: bool = True
    is_active: bool = True


# ---------------------------------------------------------------------------
# Template definitions (7 built-in templates)
# ---------------------------------------------------------------------------

BUILTIN_CONSENT_TEMPLATES: list[_ConsentTemplateDef] = [
    # 1 — General (applies to any dental procedure)
    _ConsentTemplateDef(
        name="Consentimiento Informado General",
        category="general",
        description=(
            "Consentimiento general para tratamiento odontológico. "
            "Cubre diagnóstico, procedimientos preventivos y restauradores de rutina."
        ),
        content="""\
<h2>CONSENTIMIENTO INFORMADO PARA TRATAMIENTO ODONTOLÓGICO</h2>

<p>Yo, <strong>{{patient_name}}</strong>, identificado(a) con el documento de identidad
registrado en el sistema, de manera libre, voluntaria y consciente, autorizo al(la)
<strong>Dr(a). {{doctor_name}}</strong> de la clínica <strong>{{clinic_name}}</strong>
para realizar los procedimientos odontológicos que estime necesarios según su criterio
clínico y el diagnóstico realizado.</p>

<h3>Declaro haber sido informado(a) sobre:</h3>
<ul>
  <li>La naturaleza y el propósito de los procedimientos propuestos.</li>
  <li>Los beneficios esperados del tratamiento.</li>
  <li>Los posibles riesgos, molestias e incomodidades que pueden presentarse.</li>
  <li>Los tratamientos alternativos disponibles y sus respectivos riesgos y beneficios.</li>
  <li>Las consecuencias de no recibir tratamiento.</li>
</ul>

<h3>Comprendo que:</h3>
<ul>
  <li>Puedo retirar mi consentimiento en cualquier momento sin perjuicio de la atención que requiero.</li>
  <li>Debo informar al profesional sobre cualquier cambio en mi estado de salud, alergias
      o medicamentos que esté tomando.</li>
  <li>El éxito del tratamiento depende en parte de mi colaboración y del seguimiento
      de las indicaciones médicas.</li>
</ul>

<p>Fecha: <strong>{{date}}</strong></p>
""",
    ),

    # 2 — Surgery (exodoncias, cirugías menores)
    _ConsentTemplateDef(
        name="Consentimiento para Cirugía Oral",
        category="surgery",
        description=(
            "Consentimiento para procedimientos quirúrgicos orales: exodoncias simples, "
            "cirugías de terceros molares, biopsias y otros procedimientos quirúrgicos menores."
        ),
        content="""\
<h2>CONSENTIMIENTO INFORMADO PARA CIRUGÍA ORAL</h2>

<p>Yo, <strong>{{patient_name}}</strong>, autorizo al(la)
<strong>Dr(a). {{doctor_name}}</strong> de <strong>{{clinic_name}}</strong>
para realizar el procedimiento quirúrgico oral indicado en mi historia clínica.</p>

<h3>He sido informado(a) de los posibles riesgos y complicaciones quirúrgicas, incluyendo:</h3>
<ul>
  <li>Sangrado intraoperatorio y postoperatorio.</li>
  <li>Infección del sitio quirúrgico.</li>
  <li>Inflamación, equimosis y dolor postoperatorio.</li>
  <li>Daño temporal o permanente a nervios adyacentes (parestesia o disestesia).</li>
  <li>Comunicación oroantral (en dientes superiores posteriores).</li>
  <li>Fractura de instrumentos o tejido óseo.</li>
  <li>Necesidad de procedimientos adicionales no previstos.</li>
  <li>Reacción a medicamentos o anestesia local.</li>
</ul>

<h3>Instrucciones postoperatorias que acepto seguir:</h3>
<ul>
  <li>No escupir, no enjuagarse ni succionar durante las primeras 24 horas.</li>
  <li>Aplicar hielo local en la zona operada las primeras 6 horas.</li>
  <li>Dieta blanda y fría las primeras 48 horas.</li>
  <li>Tomar los medicamentos prescritos según indicación.</li>
  <li>Asistir a controles postoperatorios programados.</li>
  <li>Consultar de urgencias ante sangrado abundante, fiebre mayor de 38°C o dolor intenso.</li>
</ul>

<p>Fecha: <strong>{{date}}</strong></p>
""",
    ),

    # 3 — Sedation
    _ConsentTemplateDef(
        name="Consentimiento para Sedación Consciente",
        category="sedation",
        description=(
            "Consentimiento para el uso de sedación consciente (óxido nitroso o "
            "sedación oral/intravenosa) durante el tratamiento odontológico."
        ),
        content="""\
<h2>CONSENTIMIENTO INFORMADO PARA SEDACIÓN CONSCIENTE</h2>

<p>Yo, <strong>{{patient_name}}</strong>, autorizo al(la)
<strong>Dr(a). {{doctor_name}}</strong> de <strong>{{clinic_name}}</strong>
para administrarme sedación consciente durante el procedimiento odontológico
programado en la fecha <strong>{{date}}</strong>.</p>

<h3>Declaro haber sido informado(a) sobre:</h3>
<ul>
  <li>El tipo de sedación que se utilizará y su mecanismo de acción.</li>
  <li>Que mantendré la conciencia y la capacidad de responder a estímulos verbales.</li>
  <li>Los posibles efectos secundarios: náuseas, mareo, cefalea, alteraciones de memoria
      a corto plazo.</li>
  <li>La necesidad de acompañante adulto responsable para el retorno a casa.</li>
  <li>Que no podré conducir vehículos ni operar maquinaria durante las 24 horas siguientes.</li>
</ul>

<h3>Confirmo que:</h3>
<ul>
  <li>He seguido las instrucciones de ayuno indicadas (mínimo 2 horas para sólidos y líquidos).</li>
  <li>He informado al profesional sobre todos mis antecedentes médicos, medicamentos
      y alergias.</li>
  <li>Cuento con acompañante adulto responsable para el retorno a casa.</li>
</ul>

<p>Fecha: <strong>{{date}}</strong></p>
""",
    ),

    # 4 — Orthodontics
    _ConsentTemplateDef(
        name="Consentimiento para Tratamiento Ortodóntico",
        category="orthodontics",
        description=(
            "Consentimiento para tratamiento de ortodoncia con aparatología fija "
            "(brackets metálicos, cerámicos o de zafiro) o removible (alineadores)."
        ),
        content="""\
<h2>CONSENTIMIENTO INFORMADO PARA TRATAMIENTO ORTODÓNTICO</h2>

<p>Yo, <strong>{{patient_name}}</strong>, autorizo al(la)
<strong>Dr(a). {{doctor_name}}</strong> de <strong>{{clinic_name}}</strong>
para iniciar y llevar a cabo mi tratamiento ortodóntico.</p>

<h3>He sido informado(a) sobre las condiciones del tratamiento:</h3>
<ul>
  <li>La duración estimada del tratamiento y la necesidad de controles periódicos.</li>
  <li>Que los resultados finales pueden variar según mi colaboración y respuesta biológica.</li>
  <li>La obligatoriedad de uso de los retenedores al finalizar el tratamiento activo.</li>
</ul>

<h3>Posibles riesgos y limitaciones que acepto:</h3>
<ul>
  <li>Desmineralización del esmalte (manchas blancas) si la higiene oral es deficiente.</li>
  <li>Reabsorción radicular leve (acortamiento de raíces) como respuesta biológica normal.</li>
  <li>Molestias dentales en los primeros días tras cada ajuste.</li>
  <li>Recidiva o recaída si no se usan los retenedores según indicación.</li>
  <li>Posible necesidad de extracciones dentales para lograr espacio.</li>
  <li>Lesiones en mucosa por la aparatología (úlceras, irritaciones).</li>
</ul>

<h3>Mis responsabilidades como paciente:</h3>
<ul>
  <li>Mantener una higiene oral estricta y usar los implementos indicados (cepillos
      interdentales, hilo dental, cepillo ortodóntico).</li>
  <li>Asistir a todos los controles programados.</li>
  <li>Evitar alimentos duros, pegajosos o muy azucarados.</li>
  <li>Informar inmediatamente sobre cualquier aparato roto o despegado.</li>
</ul>

<p>Fecha: <strong>{{date}}</strong></p>
""",
    ),

    # 5 — Implants
    _ConsentTemplateDef(
        name="Consentimiento para Implante Dental",
        category="implants",
        description=(
            "Consentimiento para cirugía de colocación de implante oseointegrado "
            "y rehabilitación protésica sobre implante."
        ),
        content="""\
<h2>CONSENTIMIENTO INFORMADO PARA IMPLANTE DENTAL</h2>

<p>Yo, <strong>{{patient_name}}</strong>, autorizo al(la)
<strong>Dr(a). {{doctor_name}}</strong> de <strong>{{clinic_name}}</strong>
para realizar la cirugía de colocación de implante(s) dental(es) y el tratamiento
protésico correspondiente.</p>

<h3>He sido informado(a) que el éxito del implante depende de:</h3>
<ul>
  <li>Calidad y cantidad de hueso disponible en la zona a implantar.</li>
  <li>Estado de salud general y sistémico (diabetes, osteoporosis, tabaquismo reducen
      la tasa de éxito).</li>
  <li>Higiene oral y controles periódicos de mantenimiento.</li>
  <li>Carga oclusal adecuada — no rechinar los dientes ni morder objetos duros.</li>
</ul>

<h3>Posibles riesgos y complicaciones:</h3>
<ul>
  <li>Fracaso de la oseointegración (pérdida del implante).</li>
  <li>Infección periimplantaria (periimplantitis).</li>
  <li>Daño a estructuras adyacentes: dientes vecinos, nervio dentario inferior, seno maxilar.</li>
  <li>Sangrado, inflamación y dolor postoperatorio.</li>
  <li>Necesidad de injertos óseos o membranosos adicionales.</li>
  <li>Fractura del implante o de la prótesis.</li>
</ul>

<h3>Compromisos que adquiero como paciente:</h3>
<ul>
  <li>Mantener una higiene oral meticulosa con los implementos recomendados.</li>
  <li>Asistir a controles de mantenimiento periimplantario mínimo 2 veces por año.</li>
  <li>No fumar durante el período de cicatrización (mínimo 3 meses).</li>
  <li>Informar sobre cambios en mi estado de salud o medicamentos.</li>
</ul>

<p>Fecha: <strong>{{date}}</strong></p>
""",
    ),

    # 6 — Endodontics
    _ConsentTemplateDef(
        name="Consentimiento para Tratamiento Endodóntico",
        category="endodontics",
        description=(
            "Consentimiento para tratamiento de conductos radiculares (endodoncia) "
            "en dientes temporales o permanentes."
        ),
        content="""\
<h2>CONSENTIMIENTO INFORMADO PARA TRATAMIENTO ENDODÓNTICO</h2>

<p>Yo, <strong>{{patient_name}}</strong>, autorizo al(la)
<strong>Dr(a). {{doctor_name}}</strong> de <strong>{{clinic_name}}</strong>
para realizar el tratamiento endodóntico (tratamiento de conductos) en el/los
diente(s) indicado(s) en mi historia clínica.</p>

<h3>He sido informado(a) sobre el procedimiento:</h3>
<ul>
  <li>Consiste en la eliminación del tejido pulpar infectado o necrótico del interior
      del diente.</li>
  <li>Se realizará bajo anestesia local para minimizar el dolor durante el procedimiento.</li>
  <li>Puede requerir una o más sesiones según la complejidad del caso.</li>
  <li>El diente tratado requerirá restauración definitiva (corona o resina) al finalizar.</li>
</ul>

<h3>Posibles riesgos y limitaciones que acepto:</h3>
<ul>
  <li>Fractura de instrumentos dentro del conducto radicular (infrecuente pero posible).</li>
  <li>Perforación radicular o de la cámara pulpar.</li>
  <li>Sobre o sub-obturación del material de relleno.</li>
  <li>Fractura del diente durante o después del tratamiento (dientes muy destruidos).</li>
  <li>Persistencia de la infección que requiera retratamiento o cirugía periapical.</li>
  <li>Molestias postoperatorias que ceden en 48-72 horas en la mayoría de los casos.</li>
</ul>

<h3>Comprendo que:</h3>
<ul>
  <li>El tratamiento endodóntico no garantiza la conservación indefinida del diente.</li>
  <li>La tasa de éxito es alta (>90%) cuando se realiza correctamente y se restaura
      adecuadamente el diente.</li>
  <li>Debo acudir a control radiográfico al año y a los 2 años del tratamiento.</li>
</ul>

<p>Fecha: <strong>{{date}}</strong></p>
""",
    ),

    # 7 — Pediatric
    _ConsentTemplateDef(
        name="Consentimiento para Tratamiento Odontológico Pediátrico",
        category="pediatric",
        description=(
            "Consentimiento para procedimientos odontológicos en pacientes menores de edad. "
            "Requiere firma del padre, madre o representante legal."
        ),
        content="""\
<h2>CONSENTIMIENTO INFORMADO PARA TRATAMIENTO ODONTOLÓGICO PEDIÁTRICO</h2>

<p>Yo, representante legal / padre / madre del menor <strong>{{patient_name}}</strong>,
autorizo al(la) <strong>Dr(a). {{doctor_name}}</strong> de <strong>{{clinic_name}}</strong>
para realizar los procedimientos odontológicos recomendados para el menor a mi cargo.</p>

<h3>Declaro que:</h3>
<ul>
  <li>Soy el padre/madre/representante legal del menor y estoy legalmente facultado(a)
      para autorizar el tratamiento.</li>
  <li>He sido informado(a) sobre los procedimientos propuestos, sus beneficios, riesgos
      y alternativas de tratamiento.</li>
  <li>He informado al profesional sobre el estado de salud del menor, sus alergias conocidas
      y los medicamentos que toma.</li>
</ul>

<h3>Autorizo específicamente:</h3>
<ul>
  <li>El uso de anestesia local cuando sea necesario para el bienestar del menor.</li>
  <li>El uso de técnicas de manejo de conducta apropiadas para la edad del paciente.</li>
  <li>La toma de radiografías diagnósticas cuando el profesional lo considere necesario.</li>
  <li>La realización de los procedimientos preventivos, restauradores y/o quirúrgicos
      indicados en la historia clínica.</li>
</ul>

<h3>Me comprometo a:</h3>
<ul>
  <li>Acompañar al menor a todas las citas programadas.</li>
  <li>Reforzar los hábitos de higiene oral en casa según las indicaciones recibidas.</li>
  <li>Informar al profesional sobre cualquier cambio en el estado de salud del menor.</li>
  <li>Asistir a los controles periódicos recomendados.</li>
</ul>

<p>Fecha: <strong>{{date}}</strong></p>
""",
        signature_positions=[
            {"role": "guardian", "label": "Padre/Madre/Representante Legal", "required": True},
            {"role": "doctor", "label": "Doctor", "required": True},
        ],
    ),
]


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------


async def seed_consent_templates(db: AsyncSession) -> int:
    """Seed built-in consent templates into the public schema.

    Inserts each template only if a builtin template with the same name
    does not already exist, making this function fully idempotent.

    The caller is responsible for ensuring the session targets the public
    schema (the default for public.consent_templates).

    Args:
        db: An open AsyncSession connected to the database.

    Returns:
        Number of templates inserted (0 if all already existed).
    """
    inserted = 0

    for tdef in BUILTIN_CONSENT_TEMPLATES:
        # Idempotency check — skip if a builtin with the same name exists.
        existing = await db.execute(
            select(PublicConsentTemplate.id).where(
                PublicConsentTemplate.name == tdef.name,
                PublicConsentTemplate.builtin.is_(True),
            )
        )
        if existing.scalar_one_or_none() is not None:
            logger.debug("Skipping existing builtin consent template: %r", tdef.name)
            continue

        template = PublicConsentTemplate(
            name=tdef.name,
            category=tdef.category,
            description=tdef.description,
            content=tdef.content,
            signature_positions=tdef.signature_positions,
            version=tdef.version,
            builtin=tdef.builtin,
            is_active=tdef.is_active,
        )
        db.add(template)
        inserted += 1
        logger.info(
            "Inserting builtin consent template: %r (category=%s)",
            tdef.name,
            tdef.category,
        )

    await db.commit()
    logger.info(
        "Consent templates: inserted %d / %d builtin templates",
        inserted,
        len(BUILTIN_CONSENT_TEMPLATES),
    )
    return inserted


# ---------------------------------------------------------------------------
# Standalone CLI entry point
# ---------------------------------------------------------------------------


async def _main() -> None:
    """Bootstrap a session against the public schema for development use."""
    from app.core.config import settings

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    print("DentalOS — Consent Template Seeder")
    print("=" * 45)
    print()
    print(f"Will insert up to {len(BUILTIN_CONSENT_TEMPLATES)} builtin consent templates")
    print("into the public.consent_templates table.")
    print()

    async with session_factory() as session:
        count = await seed_consent_templates(session)

    await engine.dispose()

    print()
    print(f"Templates inserted : {count} / {len(BUILTIN_CONSENT_TEMPLATES)}")
    print("Done. Run again at any time — inserts are idempotent.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        stream=sys.stdout,
    )
    asyncio.run(_main())
