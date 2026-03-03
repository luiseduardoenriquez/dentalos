"""Default intake template seeder — VP-10.

Seeds the default Colombian medical intake form template on tenant creation.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("dentalos.intake_template")

# Default Colombian medical intake form fields
DEFAULT_INTAKE_TEMPLATE: dict[str, Any] = {
    "name": "Formulario de ingreso estándar",
    "description": "Formulario médico estándar para pacientes en Colombia",
    "version": "1.0",
    "sections": [
        {
            "title": "Información personal",
            "fields": [
                {"key": "occupation", "label": "Ocupación", "type": "text"},
                {
                    "key": "marital_status",
                    "label": "Estado civil",
                    "type": "select",
                    "options": [
                        "Soltero/a",
                        "Casado/a",
                        "Unión libre",
                        "Divorciado/a",
                        "Viudo/a",
                    ],
                },
                {
                    "key": "emergency_contact_name",
                    "label": "Contacto de emergencia",
                    "type": "text",
                },
                {
                    "key": "emergency_contact_phone",
                    "label": "Teléfono de emergencia",
                    "type": "phone",
                },
            ],
        },
        {
            "title": "Antecedentes médicos",
            "fields": [
                {
                    "key": "current_medications",
                    "label": "Medicamentos actuales",
                    "type": "textarea",
                },
                {
                    "key": "allergies",
                    "label": "Alergias conocidas",
                    "type": "textarea",
                },
                {
                    "key": "chronic_conditions",
                    "label": "Enfermedades crónicas",
                    "type": "multi_select",
                    "options": [
                        "Diabetes",
                        "Hipertensión",
                        "Asma",
                        "Cardiopatía",
                        "VIH/SIDA",
                        "Hepatitis",
                        "Epilepsia",
                        "Artritis",
                        "Ninguna",
                    ],
                },
                {
                    "key": "previous_surgeries",
                    "label": "Cirugías previas",
                    "type": "textarea",
                },
                {
                    "key": "is_pregnant",
                    "label": "¿Está en embarazo?",
                    "type": "boolean",
                },
                {
                    "key": "blood_type",
                    "label": "Tipo de sangre",
                    "type": "select",
                    "options": [
                        "A+",
                        "A-",
                        "B+",
                        "B-",
                        "AB+",
                        "AB-",
                        "O+",
                        "O-",
                        "No sé",
                    ],
                },
            ],
        },
        {
            "title": "Historial dental",
            "fields": [
                {
                    "key": "last_dental_visit",
                    "label": "Última visita al dentista",
                    "type": "date",
                },
                {
                    "key": "dental_complaints",
                    "label": "Motivo de consulta",
                    "type": "textarea",
                },
                {
                    "key": "dental_anxiety_level",
                    "label": "Nivel de ansiedad dental",
                    "type": "select",
                    "options": ["Ninguna", "Leve", "Moderada", "Alta"],
                },
                {
                    "key": "brushing_frequency",
                    "label": "Frecuencia de cepillado",
                    "type": "select",
                    "options": [
                        "1 vez al día",
                        "2 veces al día",
                        "3+ veces al día",
                        "Irregular",
                    ],
                },
                {
                    "key": "uses_floss",
                    "label": "¿Usa hilo dental?",
                    "type": "boolean",
                },
                {
                    "key": "teeth_grinding",
                    "label": "¿Aprieta o rechina los dientes?",
                    "type": "boolean",
                },
            ],
        },
        {
            "title": "Consentimiento",
            "fields": [
                {
                    "key": "consent_data_processing",
                    "label": (
                        "Autorizo el tratamiento de mis datos personales"
                        " según la Ley 1581 de 2012"
                    ),
                    "type": "boolean",
                    "required": True,
                },
                {
                    "key": "consent_treatment",
                    "label": (
                        "Autorizo la realización de examen clínico y tratamientos necesarios"
                    ),
                    "type": "boolean",
                    "required": True,
                },
            ],
        },
    ],
}


async def seed_default_intake_template(
    tenant_id: str,
) -> dict[str, Any]:
    """Seed the default intake template for a new tenant.

    Called during tenant provisioning. Stores the template in the
    tenant's clinic_settings JSONB under the ``intake_template`` key.

    Returns:
        The seeded template dict.
    """
    try:
        import json

        from sqlalchemy import text

        from app.core.database import get_tenant_session

        async with get_tenant_session(tenant_id) as db:
            template_json = json.dumps(DEFAULT_INTAKE_TEMPLATE)
            await db.execute(
                text(
                    "UPDATE clinic_settings SET settings = jsonb_set("
                    "COALESCE(settings, '{}'), '{intake_template}', :template::jsonb"
                    ") WHERE id = (SELECT id FROM clinic_settings LIMIT 1)"
                ),
                {"template": template_json},
            )
            await db.commit()

        logger.info("Default intake template seeded: tenant=%s", tenant_id)
        return DEFAULT_INTAKE_TEMPLATE

    except Exception:
        logger.exception("Failed to seed intake template: tenant=%s", tenant_id)
        return DEFAULT_INTAKE_TEMPLATE
